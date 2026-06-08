"""Validation layer for ASN ingestion pipeline.

Cross-checks extracted data against master data in core-service:
- Supplier fuzzy matching
- SKU resolution
- Business rules (quantity > 0, dates in future, etc.)
"""

import logging
from typing import Any, Optional
from uuid import UUID

from app.clients.core_service import core_client

logger = logging.getLogger(__name__)


_REQUIRED_ASN_FIELDS = [
    "supplier_name",
    "expected_delivery_date",
    "line_items",
]


class IngestionValidator:
    """Validate extracted ASN data before creating a draft."""

    def __init__(self):
        self.min_confidence_threshold = 0.90

    async def validate(
        self,
        extracted: dict[str, Any],
        organization_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Run validation and return enriched result.

        Returns a dict:
        {
            "is_valid": bool,
            "confidence_score": float,
            "auto_create": bool,
            "errors": [str],
            "warnings": [str],
            "matched_supplier_id": UUID | None,
            "matched_supplier_name": str | None,
            "matched_po_id": UUID | None,
            "is_duplicate": bool,
            "line_item_results": [
                {"sku": str, "matched_item_id": UUID|None, "warnings": [str]}
            ],
        }
        """
        errors: list[str] = []
        warnings: list[str] = []
        line_item_results: list[dict] = []
        matched_supplier_id: Optional[UUID] = None
        matched_supplier_name: Optional[str] = None
        matched_po_id: Optional[UUID] = None
        is_duplicate: bool = False

        confidence = extracted.get("confidence_score", 0.0)
        low_confidence_fields = extracted.get("low_confidence_fields", []) or []

        # ── Field completeness gate ──
        for field in _REQUIRED_ASN_FIELDS:
            if not extracted.get(field):
                errors.append(f"Missing required ASN field: {field}")

        # ── Basic structural validation ──
        if not extracted.get("line_items"):
            errors.append("No line_items found in extracted data")

        if not extracted.get("supplier_name"):
            errors.append("supplier_name is missing")

        for idx, item in enumerate(extracted.get("line_items", [])):
            item_warnings: list[str] = []
            if not item.get("sku"):
                errors.append(f"Line item {idx + 1}: sku is missing")
            if item.get("quantity", 0) <= 0:
                errors.append(f"Line item {idx + 1}: quantity must be > 0")
            if not item.get("item_name"):
                item_warnings.append("item_name is missing")
            line_item_results.append({
                "sku": item.get("sku", ""),
                "matched_item_id": None,
                "warnings": item_warnings,
            })

        # ── Supplier fuzzy match (best-effort via core-service) ──
        supplier_name = extracted.get("supplier_name")
        if supplier_name and not extracted.get("supplier_id"):
            try:
                matched_supplier = await self._match_supplier(supplier_name, organization_id)
                if matched_supplier:
                    matched_supplier_id = matched_supplier.get("id")
                    matched_supplier_name = matched_supplier.get("name")
                    logger.info("Fuzzy-matched supplier '%s' -> %s", supplier_name, matched_supplier_id)
                else:
                    warnings.append(f"Could not resolve supplier: '{supplier_name}'")
            except Exception as e:
                logger.warning("Supplier matching failed: %s", e)
                warnings.append(f"Supplier matching unavailable: {e}")

        # ── PO matching (must reference an open purchase order) ──
        po_reference = (
            extracted.get("po_reference")
            or extracted.get("purchase_order_number")
            or extracted.get("po_number")
        )
        if not po_reference:
            errors.append("No purchase order reference found — cannot verify order exists")
        else:
            try:
                po = await core_client.find_purchase_order(
                    po_number=po_reference,
                    supplier_id=extracted.get("supplier_id"),
                    organization_id=organization_id,
                )
                if not po:
                    errors.append(
                        f"Purchase order {po_reference} not found — possible quotation or cancelled order"
                    )
                elif po.get("status") != "open":
                    errors.append(
                        f"Purchase order {po_reference} status is '{po.get('status')}' — not eligible for ASN"
                    )
                else:
                    matched_po_id = po.get("id")
                    logger.info("Matched PO %s for ASN ingestion", matched_po_id)
                    # Cross-check line items against PO lines
                    po_lines = po.get("lines", [])
                    for idx, item in enumerate(extracted.get("line_items", [])):
                        sku = item.get("sku")
                        qty = item.get("quantity", 0)
                        matched_po_line = self._find_po_line(po_lines, sku, qty)
                        if not matched_po_line:
                            warnings.append(
                                f"SKU {sku} / qty {qty} not found on PO {po_reference}"
                            )
            except Exception as e:
                logger.warning("PO matching failed: %s", e)
                warnings.append(f"PO matching unavailable: {e}")

        # ── Duplicate ASN detection ──
        asn_number = extracted.get("asn_order_number") or extracted.get("asn_number")
        if asn_number:
            try:
                existing = await core_client.find_asn_by_number(
                    asn_number=asn_number,
                    supplier_id=extracted.get("supplier_id"),
                    organization_id=organization_id,
                )
                if existing:
                    is_duplicate = True
                    errors.append(
                        f"ASN {asn_number} already exists (ID: {existing.get('id')})"
                    )
            except Exception as e:
                logger.warning("Duplicate ASN check failed: %s", e)

        # ── Supplier fuzzy match (best-effort via core-service) ──
        supplier_name = extracted.get("supplier_name")
        if supplier_name and not extracted.get("supplier_id"):
            try:
                matched_supplier = await self._match_supplier(supplier_name, organization_id)
                if matched_supplier:
                    matched_supplier_id = matched_supplier.get("id")
                    matched_supplier_name = matched_supplier.get("name")
                    logger.info("Fuzzy-matched supplier '%s' -> %s", supplier_name, matched_supplier_id)
                else:
                    warnings.append(f"Could not resolve supplier: '{supplier_name}'")
            except Exception as e:
                logger.warning("Supplier matching failed: %s", e)
                warnings.append(f"Supplier matching unavailable: {e}")

        # ── SKU resolution (best-effort) ──
        for idx, item in enumerate(extracted.get("line_items", [])):
            sku = item.get("sku")
            if sku:
                try:
                    item_id = await self._resolve_sku(sku, organization_id)
                    if item_id:
                        line_item_results[idx]["matched_item_id"] = item_id
                    else:
                        line_item_results[idx]["warnings"].append(f"SKU '{sku}' not found in item master")
                except Exception as e:
                    logger.warning("SKU resolution failed for %s: %s", sku, e)

        # ── Auto-create decision ──
        auto_create = (
            not is_duplicate
            and confidence >= self.min_confidence_threshold
            and len(errors) == 0
            and len(low_confidence_fields) == 0
            and matched_supplier_id is not None
            and all(r["matched_item_id"] for r in line_item_results)
        )

        if confidence < self.min_confidence_threshold:
            warnings.append(f"Confidence {confidence:.2f} below threshold {self.min_confidence_threshold}")

        if low_confidence_fields:
            warnings.append(f"Low confidence fields: {', '.join(low_confidence_fields)}")

        return {
            "is_valid": len(errors) == 0 and not is_duplicate,
            "confidence_score": confidence,
            "auto_create": auto_create,
            "errors": errors,
            "warnings": warnings,
            "matched_supplier_id": matched_supplier_id,
            "matched_supplier_name": matched_supplier_name,
            "matched_po_id": matched_po_id,
            "is_duplicate": is_duplicate,
            "line_item_results": line_item_results,
        }

    @staticmethod
    def _find_po_line(po_lines: list[dict], sku: str, qty: int) -> dict | None:
        """Find a PO line that matches the given SKU and quantity (within tolerance)."""
        for line in po_lines:
            line_sku = line.get("sku", line.get("item_sku", ""))
            line_qty = line.get("quantity", line.get("qty", 0))
            if line_sku and line_sku.lower() == sku.lower():
                # Allow 10% quantity variance
                if line_qty and abs(qty - line_qty) / max(line_qty, 1) <= 0.10:
                    return line
        return None

    async def _match_supplier(self, supplier_name: str, organization_id: Optional[UUID]) -> Optional[dict]:
        """Fuzzy-match supplier name against core-service supplier list.

        Returns the best match dict with keys 'id', 'name' or None.
        """
        try:
            # Try to fetch suppliers from core-service
            # This uses a generic search; adjust endpoint as needed
            suppliers = await core_client.search_suppliers(name=supplier_name, organization_id=organization_id)
            if not suppliers:
                return None
            # Simple exact / contains match first
            supplier_name_lower = supplier_name.lower()
            for s in suppliers:
                if s.get("name", "").lower() == supplier_name_lower:
                    return s
            for s in suppliers:
                if supplier_name_lower in s.get("name", "").lower():
                    return s
            # Fallback: return first result if list is short
            return suppliers[0] if len(suppliers) <= 3 else None
        except Exception:
            # If core-service doesn't have a supplier endpoint yet, skip gracefully
            return None

    async def _resolve_sku(self, sku: str, organization_id: Optional[UUID]) -> Optional[UUID]:
        """Resolve a SKU to an item ID via core-service."""
        try:
            items = await core_client.search_items(sku=sku, organization_id=organization_id)
            if items:
                for it in items:
                    if it.get("sku", "").lower() == sku.lower():
                        return it.get("id")
                return items[0].get("id")
        except Exception:
            return None
        return None


def get_validator() -> IngestionValidator:
    """Factory: return an IngestionValidator instance."""
    return IngestionValidator()
