"""Payment provider webhooks (no JWT auth — verified by signature)."""

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.razorpay_webhook_service import RazorpayWebhookService

router = APIRouter()


@router.post(
    "/razorpay",
    summary="Razorpay webhook (signature verified, event-id deduplicated)",
)
async def razorpay_webhook(
    request: Request,
    signature: str | None = Header(None, alias="X-Razorpay-Signature"),
    event_id: str | None = Header(None, alias="X-Razorpay-Event-Id"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    return RazorpayWebhookService(db).handle(
        raw_body,
        signature or "",
        event_id,
    )
