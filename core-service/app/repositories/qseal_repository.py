"""Repository for QSeal module"""

import uuid
from uuid import UUID

from sqlalchemy import Date, case, cast, func
from sqlalchemy.orm import Session

from app.models.qr_product import QRProduct
from app.models.qr_scan_event import QRScanEvent
from app.models.qseal import QSealTrack
from app.services.qseal_suspicion_service import risk_level


class QSealRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Node CRUD ─────────────────────────────────────────────────────────────

    def create_node(self, data: dict) -> QSealTrack:
        node = QSealTrack(**data)
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_by_id(self, node_id: UUID, organization_id: UUID) -> QSealTrack | None:
        return (
            self.db.query(QSealTrack)
            .filter(
                QSealTrack.id == node_id,
                QSealTrack.organization_id == organization_id,
            )
            .first()
        )

    def get_by_serial(
        self, serial_number: str, organization_id: UUID
    ) -> QSealTrack | None:
        return (
            self.db.query(QSealTrack)
            .filter(
                QSealTrack.serial_number == serial_number,
                QSealTrack.organization_id == organization_id,
            )
            .first()
        )

    def list_roots(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        qseal_type: str | None = None,
    ) -> tuple[list[QSealTrack], int]:
        """List top-level (parent_id IS NULL) nodes."""
        q = self.db.query(QSealTrack).filter(
            QSealTrack.organization_id == organization_id,
            QSealTrack.parent_id.is_(None),
        )
        if qseal_type:
            q = q.filter(QSealTrack.qseal_type == qseal_type)
        total = q.count()
        items = (
            q.order_by(QSealTrack.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def list_children(
        self,
        parent_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[QSealTrack], int]:
        q = self.db.query(QSealTrack).filter(
            QSealTrack.parent_id == parent_id,
            QSealTrack.organization_id == organization_id,
        )
        total = q.count()
        items = (
            q.order_by(QSealTrack.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def count_children(self, parent_id: UUID) -> int:
        return (
            self.db.query(func.count(QSealTrack.id))
            .filter(QSealTrack.parent_id == parent_id)
            .scalar()
        ) or 0

    def map_children(
        self, parent_id: UUID, child_ids: list[UUID], organization_id: UUID
    ) -> int:
        """Attach child nodes (QSealTrack or QSealParameters) to a parent.

        Handles both:
        - QSealTrack children (other cascade nodes): updates parent_id
        - QSealParameters children (ProductItem units): updates parent_id

        Allows re-assigning already-mapped children to a new parent.
        Returns count of successfully mapped children.
        """
        import logging

        logger = logging.getLogger(__name__)

        from app.models.qseal import QSealParameters

        mapped = 0
        for child_id in child_ids:
            # Try QSealTrack first
            child = self.get_by_id(child_id, organization_id)
            if child:
                if child.parent_id and child.parent_id != parent_id:
                    logger.info(
                        "[QSEAL] map_children re-assigning track id=%s from parent=%s to parent=%s",
                        child_id,
                        child.parent_id,
                        parent_id,
                    )
                child.parent_id = parent_id
                mapped += 1
                continue

            # Try QSealParameters (individual units from ProductItems)
            child_param = (
                self.db.query(QSealParameters)
                .filter(
                    QSealParameters.id == child_id,
                    QSealParameters.organization_id == organization_id,
                )
                .first()
            )
            if child_param:
                old_parent = child_param.parent_id
                if old_parent and old_parent != parent_id:
                    logger.info(
                        "[QSEAL] map_children re-assigning param id=%s serial=%s from parent=%s to parent=%s",
                        child_id,
                        child_param.serial_number,
                        old_parent,
                        parent_id,
                    )
                child_param.parent_id = parent_id
                mapped += 1
                continue

            logger.warning(
                "[QSEAL] map_children child not found id=%s org=%s",
                child_id,
                organization_id,
            )

        self.db.commit()
        logger.info(
            "[QSEAL] map_children parent=%s total_requested=%d mapped=%d",
            parent_id,
            len(child_ids),
            mapped,
        )
        return mapped

    def generate_serial(self, prefix: str = "QSL") -> str:
        """Generate a short unique serial for a QSeal node (max 10 chars)."""
        return f"{prefix}{str(uuid.uuid4()).replace('-', '')[:7].upper()}"

    # ── Scan History ──────────────────────────────────────────────────────────

    def record_scan(self, data: dict) -> QRScanEvent:
        event = QRScanEvent(**data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_suspicious_scans(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
        review_status: str | None = None,
        limit_score: int | None = None,
        **filters,
    ) -> tuple[list[dict], int]:
        """List flagged QSeal events with product names and tenant filtering."""
        query = self._qseal_scan_query(organization_id, **filters).filter(
            QRScanEvent.is_suspicious.is_(True)
        )
        if review_status:
            query = query.filter(QRScanEvent.review_status == review_status)
        if limit_score is not None:
            query = query.filter(QRScanEvent.risk_score >= limit_score)

        total = query.count()
        rows = (
            query.outerjoin(QRProduct, QRProduct.id == QRScanEvent.product_id)
            .with_entities(QRScanEvent, QRProduct.name.label("product_name"))
            .order_by(QRScanEvent.scan_timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items = []
        for event, product_name in rows:
            items.append(
                {
                    "id": event.id,
                    "organization_id": event.organization_id,
                    "serial_number": event.serial_number,
                    "product_id": event.product_id,
                    "product_name": product_name or "Unknown product",
                    "block_id": event.block_id,
                    "batch": event.batch,
                    "scan_timestamp": event.scan_timestamp,
                    "verification_status": event.verification_status,
                    "is_suspicious": event.is_suspicious,
                    "risk_score": event.risk_score or 0,
                    "risk_level": risk_level(event.risk_score or 0),
                    "suspicious_reasons": event.suspicious_reasons or [],
                    "review_status": event.review_status or "not_flagged",
                    "device_type": event.device_type,
                    "city": event.city,
                    "state": event.state,
                    "country": event.country,
                }
            )
        return items, total

    def update_suspicious_review(
        self, event_id: UUID, organization_id: UUID, review_status: str
    ) -> QRScanEvent | None:
        event = (
            self.db.query(QRScanEvent)
            .filter(
                QRScanEvent.id == event_id,
                QRScanEvent.organization_id == organization_id,
                QRScanEvent.qseal_type.is_not(None),
                QRScanEvent.is_suspicious.is_(True),
            )
            .first()
        )
        if not event:
            return None
        event.review_status = review_status
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_scan_history(
        self,
        organization_id: UUID,
        serial_number: str | None = None,
        page: int = 1,
        page_size: int = 50,
        date_from=None,
        date_to=None,
        product_id: UUID | None = None,
        block_id: UUID | None = None,
        batch: str | None = None,
        qseal_type: str | None = None,
        risk_filter: str | None = None,
    ) -> tuple[list[QRScanEvent], int]:
        q = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id,
            # QSeal events are explicitly marked by the QSeal service. This
            # prevents the QSeal history/dashboard from mixing in WMS or
            # generic QR scan events stored in the shared table.
            QRScanEvent.qseal_type.is_not(None),
        )
        if serial_number:
            q = q.filter(QRScanEvent.serial_number.ilike(f"%{serial_number}%"))
        if date_from:
            q = q.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            q = q.filter(QRScanEvent.scan_timestamp <= date_to)
        if product_id:
            q = q.filter(QRScanEvent.product_id == product_id)
        if block_id:
            q = q.filter(QRScanEvent.block_id == block_id)
        if batch:
            q = q.filter(QRScanEvent.batch == batch)
        if qseal_type:
            q = q.filter(QRScanEvent.qseal_type == qseal_type)
        q = self._apply_risk_filter(q, risk_filter)
        total = q.count()
        items = (
            q.order_by(QRScanEvent.scan_timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    # ── Client-facing analytics ──────────────────────────────────────────────

    def _qseal_scan_query(
        self,
        organization_id: UUID,
        date_from=None,
        date_to=None,
        product_id: UUID | None = None,
        block_id: UUID | None = None,
        batch: str | None = None,
        qseal_type: str | None = None,
        serial_number: str | None = None,
        risk_filter: str | None = None,
    ):
        """Return a tenant-scoped QSeal event query with shared filters."""
        query = self.db.query(QRScanEvent).filter(
            QRScanEvent.organization_id == organization_id,
            QRScanEvent.qseal_type.is_not(None),
        )
        if date_from:
            query = query.filter(QRScanEvent.scan_timestamp >= date_from)
        if date_to:
            query = query.filter(QRScanEvent.scan_timestamp <= date_to)
        if product_id:
            query = query.filter(QRScanEvent.product_id == product_id)
        if block_id:
            query = query.filter(QRScanEvent.block_id == block_id)
        if batch:
            query = query.filter(QRScanEvent.batch == batch)
        if qseal_type:
            query = query.filter(QRScanEvent.qseal_type == qseal_type)
        if serial_number:
            query = query.filter(QRScanEvent.serial_number == serial_number)
        query = self._apply_risk_filter(query, risk_filter)
        return query

    @staticmethod
    def _apply_risk_filter(query, risk_filter: str | None):
        if risk_filter == "suspicious":
            return query.filter(QRScanEvent.is_suspicious.is_(True))
        if risk_filter == "high_risk":
            return query.filter(QRScanEvent.risk_score >= 60)
        if risk_filter == "unreviewed":
            return query.filter(
                QRScanEvent.is_suspicious.is_(True),
                QRScanEvent.review_status == "new",
            )
        return query

    @staticmethod
    def _valid_scan_filter(query):
        return query.filter(QRScanEvent.verification_status == "valid")

    def get_scan_summary(self, organization_id: UUID, **filters) -> dict:
        query = self._qseal_scan_query(organization_id, **filters)
        total_scans = query.count()
        valid_query = self._valid_scan_filter(query)
        valid_scans = valid_query.count()
        invalid_scans = query.filter(QRScanEvent.verification_status != "valid").count()
        unique_serials = (
            valid_query.with_entities(
                func.count(func.distinct(QRScanEvent.serial_number))
            ).scalar()
            or 0
        )
        repeat_scans = max(valid_scans - unique_serials, 0)
        suspicious_scans = query.filter(QRScanEvent.is_suspicious.is_(True)).count()
        high_risk_scans = query.filter(QRScanEvent.risk_score >= 60).count()
        unreviewed_suspicious_scans = query.filter(
            QRScanEvent.is_suspicious.is_(True),
            QRScanEvent.review_status == "new",
        ).count()
        return {
            "total_scans": total_scans,
            "valid_scans": valid_scans,
            "invalid_scans": invalid_scans,
            "unique_serials": unique_serials,
            "repeat_scans": repeat_scans,
            "repeat_scan_rate": round((repeat_scans / valid_scans) * 100, 1)
            if valid_scans
            else 0.0,
            "suspicious_scans": suspicious_scans,
            "suspicious_rate": round(
                (suspicious_scans / total_scans) * 100,
                1,
            )
            if total_scans
            else 0.0,
            "high_risk_scans": high_risk_scans,
            "unreviewed_suspicious_scans": unreviewed_suspicious_scans,
        }

    def get_scan_trends(self, organization_id: UUID, **filters) -> dict:
        query = self._qseal_scan_query(organization_id, **filters)
        rows = (
            query.with_entities(
                cast(QRScanEvent.scan_timestamp, Date).label("date"),
                QRScanEvent.verification_status,
                func.count().label("count"),
                func.sum(case((QRScanEvent.is_suspicious.is_(True), 1), else_=0)).label(
                    "suspicious_count"
                ),
            )
            .group_by(
                cast(QRScanEvent.scan_timestamp, Date),
                QRScanEvent.verification_status,
            )
            .order_by(cast(QRScanEvent.scan_timestamp, Date))
            .all()
        )
        trend: dict[str, dict] = {}
        for row in rows:
            date_key = str(row.date)
            item = trend.setdefault(
                date_key,
                {
                    "date": date_key,
                    "total_scans": 0,
                    "valid_scans": 0,
                    "invalid_scans": 0,
                    "suspicious_scans": 0,
                },
            )
            item["total_scans"] += row.count
            item["suspicious_scans"] += int(getattr(row, "suspicious_count", 0) or 0)
            if row.verification_status == "valid":
                item["valid_scans"] += row.count
            else:
                item["invalid_scans"] += row.count
        return {"items": list(trend.values())}

    def get_product_analytics(
        self, organization_id: UUID, limit: int = 20, **filters
    ) -> dict:
        query = (
            self.db.query(
                QRScanEvent.product_id,
                QRProduct.name.label("product_name"),
                QRScanEvent.batch,
                func.count(QRScanEvent.id).label("total_scans"),
                func.sum(
                    case((QRScanEvent.verification_status == "valid", 1), else_=0)
                ).label("valid_scans"),
                func.count(
                    func.distinct(
                        case(
                            (QRScanEvent.verification_status == "valid", QRScanEvent.serial_number),
                            else_=None,
                        )
                    )
                ).label("unique_serials"),
                func.max(QRScanEvent.scan_timestamp).label("last_scan"),
            )
            .outerjoin(QRProduct, QRProduct.id == QRScanEvent.product_id)
            .filter(
                QRScanEvent.organization_id == organization_id,
                QRScanEvent.qseal_type.is_not(None),
            )
        )
        query = self._apply_scan_filters(query, filters)
        rows = (
            query.group_by(QRScanEvent.product_id, QRProduct.name, QRScanEvent.batch)
            .order_by(func.count(QRScanEvent.id).desc())
            .limit(limit)
            .all()
        )
        items = []
        for row in rows:
            total = int(row.total_scans or 0)
            valid = int(row.valid_scans or 0)
            items.append(
                {
                    "product_id": row.product_id,
                    "product_name": row.product_name or "Unknown product",
                    "batch": row.batch,
                    "total_scans": total,
                    "valid_scans": valid,
                    "invalid_scans": total - valid,
                    "unique_serials": int(row.unique_serials or 0),
                    "last_scan": row.last_scan,
                }
            )
        return {"items": items}

    def get_geography_analytics(
        self, organization_id: UUID, limit: int = 500, **filters
    ) -> dict:
        query = self._qseal_scan_query(organization_id, **filters)
        rows = (
            query.with_entities(
                QRScanEvent.country,
                QRScanEvent.state,
                QRScanEvent.city,
                QRScanEvent.latitude,
                QRScanEvent.longitude,
                func.count().label("total_scans"),
                func.sum(
                    case((QRScanEvent.verification_status == "valid", 1), else_=0)
                ).label("valid_scans"),
            )
            .group_by(
                QRScanEvent.country,
                QRScanEvent.state,
                QRScanEvent.city,
                QRScanEvent.latitude,
                QRScanEvent.longitude,
            )
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )
        return {
            "items": [
                {
                    "country": row.country,
                    "state": row.state,
                    "city": row.city,
                    "latitude": float(row.latitude) if row.latitude is not None else None,
                    "longitude": float(row.longitude) if row.longitude is not None else None,
                    "total_scans": int(row.total_scans or 0),
                    "valid_scans": int(row.valid_scans or 0),
                    "invalid_scans": int((row.total_scans or 0) - (row.valid_scans or 0)),
                }
                for row in rows
            ]
        }

    def get_device_analytics(
        self, organization_id: UUID, limit: int = 20, **filters
    ) -> dict:
        query = self._qseal_scan_query(organization_id, **filters)
        rows = (
            query.with_entities(
                QRScanEvent.device_type,
                func.count().label("total_scans"),
                func.sum(
                    case((QRScanEvent.verification_status == "valid", 1), else_=0)
                ).label("valid_scans"),
            )
            .group_by(QRScanEvent.device_type)
            .order_by(func.count().desc())
            .limit(limit)
            .all()
        )
        return {
            "items": [
                {
                    "device_type": row.device_type or "unknown",
                    "total_scans": int(row.total_scans or 0),
                    "valid_scans": int(row.valid_scans or 0),
                    "invalid_scans": int((row.total_scans or 0) - (row.valid_scans or 0)),
                }
                for row in rows
            ]
        }

    def _apply_scan_filters(self, query, filters: dict):
        """Apply shared filters to aggregate queries that already include joins."""
        for field, column in (
            ("date_from", QRScanEvent.scan_timestamp),
            ("date_to", QRScanEvent.scan_timestamp),
            ("product_id", QRScanEvent.product_id),
            ("block_id", QRScanEvent.block_id),
            ("batch", QRScanEvent.batch),
            ("qseal_type", QRScanEvent.qseal_type),
            ("serial_number", QRScanEvent.serial_number),
        ):
            value = filters.get(field)
            if value:
                if field == "date_from":
                    query = query.filter(column >= value)
                elif field == "date_to":
                    query = query.filter(column <= value)
                else:
                    query = query.filter(column == value)
        query = self._apply_risk_filter(query, filters.get("risk_filter"))
        return query
