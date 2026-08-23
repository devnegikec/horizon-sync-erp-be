"""Vehicle arrival service for inbound receiving."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.asn_order import AsnOrder
from app.models.vehicle import Vehicle, VehicleArrival, vehicle_arrival_asns


class VehicleArrivalService:
    def __init__(self, db: Session):
        self.db = db

    def _get_or_create_vehicle(self, data: dict, organization_id: UUID) -> Vehicle:
        """Return an existing vehicle for the org or create a new one."""
        vehicle = (
            self.db.query(Vehicle)
            .filter(
                Vehicle.organization_id == organization_id,
                Vehicle.vehicle_no == data["vehicle_no"].strip(),
            )
            .first()
        )
        if vehicle:
            return vehicle

        vehicle = Vehicle(
            organization_id=organization_id,
            vehicle_no=data["vehicle_no"].strip(),
            driver_name=data.get("driver_name"),
            driver_contact=data.get("driver_contact"),
            transporter=data.get("transporter"),
        )
        self.db.add(vehicle)
        self.db.flush()
        return vehicle

    def _validate_asns(
        self, asn_order_ids: list[UUID], organization_id: UUID
    ) -> list[AsnOrder]:
        """Validate ASN ids belong to the organization and return the rows."""
        if not asn_order_ids:
            return []
        asns = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.organization_id == organization_id,
                AsnOrder.id.in_(asn_order_ids),
            )
            .all()
        )
        found_ids = {a.id for a in asns}
        missing = set(asn_order_ids) - found_ids
        if missing:
            raise ResourceNotFoundException(
                f"ASN order(s) not found: {', '.join(str(m) for m in missing)}"
            )
        return asns

    def create(
        self, data: dict, organization_id: UUID, user_id: UUID
    ) -> VehicleArrival:
        asn_order_ids = [UUID(str(x)) for x in (data.pop("asn_order_ids", []) or [])]
        asns = self._validate_asns(asn_order_ids, organization_id)

        vehicle = self._get_or_create_vehicle(data, organization_id)

        arrival = VehicleArrival(
            organization_id=organization_id,
            vehicle_id=vehicle.id,
            warehouse_id=data.get("warehouse_id"),
            dock=data.get("dock"),
            notes=data.get("notes"),
            status="arrived",
            created_by=user_id,
        )
        arrival.asn_orders = asns
        self.db.add(arrival)
        self.db.commit()
        self.db.refresh(arrival)
        return arrival

    def get(self, arrival_id: UUID, organization_id: UUID) -> VehicleArrival:
        arrival = (
            self.db.query(VehicleArrival)
            .filter(
                VehicleArrival.id == arrival_id,
                VehicleArrival.organization_id == organization_id,
            )
            .first()
        )
        if not arrival:
            raise ResourceNotFoundException(f"Vehicle arrival {arrival_id} not found")
        return arrival

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        warehouse_id: UUID | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[VehicleArrival], dict]:
        q = self.db.query(VehicleArrival).filter(
            VehicleArrival.organization_id == organization_id
        )
        if warehouse_id is not None:
            q = q.filter(VehicleArrival.warehouse_id == warehouse_id)
        if status is not None:
            q = q.filter(VehicleArrival.status == status)
        if search:
            q = q.join(Vehicle, Vehicle.id == VehicleArrival.vehicle_id).filter(
                Vehicle.vehicle_no.ilike(f"%{search}%")
            )

        total = q.count()
        items = (
            q.order_by(VehicleArrival.arrived_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return items, pagination

    def link_asns(
        self, arrival_id: UUID, asn_order_ids: list[UUID], organization_id: UUID
    ) -> VehicleArrival:
        arrival = self.get(arrival_id, organization_id)
        asns = self._validate_asns(asn_order_ids, organization_id)
        existing_ids = {a.id for a in arrival.asn_orders}
        for asn in asns:
            if asn.id not in existing_ids:
                arrival.asn_orders.append(asn)
        self.db.commit()
        self.db.refresh(arrival)
        return arrival

    def unlink_asn(
        self, arrival_id: UUID, asn_order_id: UUID, organization_id: UUID
    ) -> VehicleArrival:
        arrival = self.get(arrival_id, organization_id)
        arrival.asn_orders = [a for a in arrival.asn_orders if a.id != asn_order_id]
        self.db.commit()
        self.db.refresh(arrival)
        return arrival
