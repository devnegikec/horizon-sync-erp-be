"""Purchase receipt repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.purchase_receipt import PurchaseReceipt, PurchaseReceiptItem


class PurchaseReceiptRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, items: list[dict]) -> PurchaseReceipt:
        pr = PurchaseReceipt(**data)
        self.db.add(pr)
        self.db.flush()
        for it in items:
            it["purchase_receipt_id"] = pr.id
            it["organization_id"] = pr.organization_id
            self.db.add(PurchaseReceiptItem(**it))
        self.db.commit()
        self.db.refresh(pr)
        return pr

    def get_by_id(
        self, purchase_receipt_id: UUID, organization_id: UUID, load_items: bool = True
    ) -> PurchaseReceipt | None:
        q = self.db.query(PurchaseReceipt).filter(
            PurchaseReceipt.id == purchase_receipt_id,
            PurchaseReceipt.organization_id == organization_id,
        )
        pr = q.first()
        if pr and load_items:
            _ = pr.items
        return pr

    def get_by_no(
        self, purchase_receipt_no: str, organization_id: UUID
    ) -> PurchaseReceipt | None:
        return (
            self.db.query(PurchaseReceipt)
            .filter(
                PurchaseReceipt.purchase_receipt_no == purchase_receipt_no,
                PurchaseReceipt.organization_id == organization_id,
            )
            .first()
        )

    def list_purchase_receipts(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        supplier_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "receipt_date",
        sort_order: str = "desc",
    ) -> tuple[list[PurchaseReceipt], int]:
        q = self.db.query(PurchaseReceipt).filter(
            PurchaseReceipt.organization_id == organization_id
        )
        if supplier_id is not None:
            q = q.filter(PurchaseReceipt.supplier_id == supplier_id)
        if status is not None:
            q = q.filter(PurchaseReceipt.status == status)
        total = q.count()
        col = getattr(PurchaseReceipt, sort_by, PurchaseReceipt.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, pr: PurchaseReceipt, data: dict) -> PurchaseReceipt:
        for k, v in data.items():
            if hasattr(pr, k):
                setattr(pr, k, v)
        self.db.commit()
        self.db.refresh(pr)
        return pr

    def delete(self, pr: PurchaseReceipt) -> None:
        self.db.delete(pr)
        self.db.commit()
