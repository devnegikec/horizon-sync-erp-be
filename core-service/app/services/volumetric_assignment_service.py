"""VolumetricAssignmentService — assigns bin locations to put-away list items
based on available volume and weight capacity.

Called from PutAwayService.generate_from_slip() within the same DB transaction.
All DB operations share the caller's session — no new transaction is opened here.

Key design decisions (from design doc):
- Null capacity = unconstrained: if max_volume_cc or max_weight_grams is null on
  a bin, that dimension is not checked.
- Consolidation preference: bins already holding the same (item_id, batch_number)
  are ranked first.
- SELECT ... FOR UPDATE SKIP LOCKED prevents concurrent double-assignment.
- If no bin is found, bin_location_id is left as None without aborting.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.put_away_list import PutAwayListItem
from app.models.warehouse_location import WarehouseLocation


class VolumetricAssignmentService:
    """Assigns optimal bin locations to put-away list items using volumetric
    capacity constraints and consolidation preference.

    This service is stateless and shares the caller's DB session.  It must
    never open a new transaction or call db.commit().
    """

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def assign_bins(
        self,
        put_away_list_items: list[PutAwayListItem],
        warehouse_id: UUID,
        org_id: UUID,
        db: Session,
    ) -> None:
        """Assign the best available bin to each put-away list item in place.

        For each item, the method:
        1. Fetches the associated packaging unit (if any).
        2. Calculates the required volume in cc (mm³ → cc).
        3. Calculates the required weight in grams.
        4. Queries for the best bin using the volumetric allocation SQL.
        5. Mutates ``item.bin_location_id`` with the result (or None).

        If no suitable bin is found for an item, ``bin_location_id`` is left
        as None and processing continues with the next item — this method
        never raises due to a missing bin (Req 7.7).

        Args:
            put_away_list_items: List of PutAwayListItem rows to assign.
            warehouse_id: The warehouse to search bins within.
            org_id: Organization ID for tenant isolation.
            db: SQLAlchemy session shared with the caller's transaction.
        """
        for item in put_away_list_items:
            packaging_unit = self._get_packaging_unit(item, db)
            required_volume_cc = self._calc_volume(item.quantity, packaging_unit)
            required_weight_g = self._calc_weight(item.quantity, packaging_unit)

            bin_loc = self._find_best_bin(
                item_id=item.item_id,
                batch_number=item.batch_number,
                warehouse_id=warehouse_id,
                org_id=org_id,
                required_volume_cc=required_volume_cc,
                required_weight_g=required_weight_g,
                db=db,
            )
            # bin_loc may be None — that is acceptable (Req 7.7)
            item.bin_location_id = bin_loc.id if bin_loc else None

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _get_packaging_unit(
        self,
        item: PutAwayListItem,
        db: Session,
    ) -> Optional[ItemPackagingUnit]:
        """Fetch the ItemPackagingUnit for a put-away item, if present.

        Args:
            item: The put-away list item to look up.
            db: SQLAlchemy session.

        Returns:
            The ItemPackagingUnit row, or None if the item has no
            packaging_unit_id or the row is not found.
        """
        packaging_unit_id = getattr(item, "packaging_unit_id", None)
        if packaging_unit_id is None:
            return None
        return db.get(ItemPackagingUnit, packaging_unit_id)

    def _calc_volume(
        self,
        quantity: Decimal,
        pu: Optional[ItemPackagingUnit],
    ) -> Optional[Decimal]:
        """Calculate the required volume in cubic centimetres (cc).

        Converts mm³ to cc by dividing by 1000.  Returns None (unconstrained)
        when any of the three dimensions is null or when no packaging unit is
        provided (Req 7.3, 4.4).

        Args:
            quantity: Number of units being put away.
            pu: The packaging unit with physical dimensions, or None.

        Returns:
            ``quantity * L * W * H / 1000`` as a Decimal, or None.
        """
        if pu and pu.length_mm and pu.width_mm and pu.height_mm:
            return (
                Decimal(str(quantity))
                * Decimal(str(pu.length_mm))
                * Decimal(str(pu.width_mm))
                * Decimal(str(pu.height_mm))
                / Decimal("1000")
            )
        return None

    def _calc_weight(
        self,
        quantity: Decimal,
        pu: Optional[ItemPackagingUnit],
    ) -> Optional[Decimal]:
        """Calculate the required weight in grams.

        Returns None (unconstrained) when weight_grams is null or when no
        packaging unit is provided (Req 7.4, 4.4).

        Args:
            quantity: Number of units being put away.
            pu: The packaging unit with weight data, or None.

        Returns:
            ``quantity * weight_grams`` as a Decimal, or None.
        """
        if pu and pu.weight_grams:
            return Decimal(str(quantity)) * Decimal(str(pu.weight_grams))
        return None

    def _find_best_bin(
        self,
        item_id: UUID,
        batch_number: Optional[str],
        warehouse_id: UUID,
        org_id: UUID,
        required_volume_cc: Optional[Decimal],
        required_weight_g: Optional[Decimal],
        db: Session,
    ) -> Optional[WarehouseLocation]:
        """Find the best available bin for the given item using volumetric SQL.

        The query uses two CTEs:
        - ``bin_usage``: computes currently occupied volume and weight per bin
          from bin_stock_levels joined to item_packaging_units.
        - ``consolidation``: flags bins already holding the same
          (item_id, batch_number) combination.

        Ordering:
        1. Consolidation bins first (COALESCE(has_same_item, FALSE) DESC).
        2. Tightest fit (smallest remaining volume) ASC.

        ``FOR UPDATE SKIP LOCKED`` prevents concurrent put-away list
        generations from assigning the same bin to conflicting items.

        Volume and weight checks are only applied when BOTH the bin has a
        limit AND the item has a calculated dimension — null on either side
        means unconstrained (Req 4.4, 7.5).

        Args:
            item_id: The item being put away.
            batch_number: The batch number (may be None).
            warehouse_id: The warehouse to search within.
            org_id: Organization ID for tenant isolation.
            required_volume_cc: Required volume in cc, or None if unconstrained.
            required_weight_g: Required weight in grams, or None if unconstrained.
            db: SQLAlchemy session shared with the caller's transaction.

        Returns:
            The best WarehouseLocation (bin), or None if no suitable bin exists.
        """
        sql = text(
            """
            WITH bin_usage AS (
                SELECT
                    bsl.bin_location_id,
                    COALESCE(SUM(
                        bsl.quantity_on_hand
                        * ipu.length_mm * ipu.width_mm * ipu.height_mm / 1000.0
                    ), 0) AS occupied_volume_cc,
                    COALESCE(SUM(
                        bsl.quantity_on_hand * ipu.weight_grams
                    ), 0) AS occupied_weight_g
                FROM bin_stock_levels bsl
                LEFT JOIN item_packaging_units ipu ON ipu.id = bsl.packaging_unit_id
                WHERE bsl.organization_id = :org_id
                GROUP BY bsl.bin_location_id
            ),
            consolidation AS (
                SELECT bin_location_id, TRUE AS has_same_item
                FROM bin_stock_levels
                WHERE item_id = :item_id
                  AND batch_number IS NOT DISTINCT FROM :batch_number
                  AND organization_id = :org_id
                  AND quantity_on_hand > 0
            )
            SELECT wl.id
            FROM warehouse_locations wl
            LEFT JOIN bin_usage bu ON bu.bin_location_id = wl.id
            LEFT JOIN consolidation c ON c.bin_location_id = wl.id
            WHERE wl.organization_id = :org_id
              AND wl.warehouse_id    = :warehouse_id
              AND wl.location_type   = 'bin'
              AND wl.is_active       = TRUE
              AND (
                  wl.max_volume_cc IS NULL
                  OR :required_volume_cc IS NULL
                  OR (wl.max_volume_cc - COALESCE(bu.occupied_volume_cc, 0)) >= :required_volume_cc
              )
              AND (
                  wl.max_weight_grams IS NULL
                  OR :required_weight_g IS NULL
                  OR (wl.max_weight_grams - COALESCE(bu.occupied_weight_g, 0)) >= :required_weight_g
              )
            ORDER BY
                COALESCE(c.has_same_item, FALSE) DESC,
                (wl.max_volume_cc - COALESCE(bu.occupied_volume_cc, 0)) ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        )

        params = {
            "org_id": str(org_id),
            "warehouse_id": str(warehouse_id),
            "item_id": str(item_id),
            "batch_number": batch_number,
            "required_volume_cc": (
                float(required_volume_cc) if required_volume_cc is not None else None
            ),
            "required_weight_g": (
                float(required_weight_g) if required_weight_g is not None else None
            ),
        }

        result = db.execute(sql, params).fetchone()
        if result is None:
            return None

        bin_id = result[0]
        return db.get(WarehouseLocation, bin_id)
