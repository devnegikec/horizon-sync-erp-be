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
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.put_away_list import PutAwayListItem
from app.models.warehouse_location import WarehouseLocation
from app.services.capacity_math import (
    CC_PER_M3,
    G_PER_KG,
    compute_bin_occupancy,
    effective_bin_volume_limit_cc,
    effective_bin_weight_limit_g,
)


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
        reserved_bin_ids: set[UUID] | None = None,
    ) -> None:
        """Assign the best available bin to each put-away list item in place.

        For each item, the method:
        1. Fetches the associated packaging unit (if any).
        2. Calculates the required volume in cc (mm³ → cc).
        3. Calculates the required weight in grams.
        4. Queries for the best bin using the volumetric allocation SQL.
        5. Mutates ``item.bin_location_id`` with the result (or None).

        Volume already claimed **within this call** is tracked, so the same SKU
        consolidates into as few bins as physically fit instead of being sprayed
        one-per-bin, and two items can never oversubscribe the same bin. Bins in
        ``reserved_bin_ids`` (worker-held reservations) are skipped.

        If no suitable bin is found for an item, ``bin_location_id`` is left
        as None and processing continues with the next item — this method
        never raises due to a missing bin (Req 7.7).

        Args:
            put_away_list_items: List of PutAwayListItem rows to assign.
            warehouse_id: The warehouse to search bins within.
            org_id: Organization ID for tenant isolation.
            db: SQLAlchemy session shared with the caller's transaction.
            reserved_bin_ids: Optional bins reserved by workers to skip.
        """
        base_unit_cache: dict = {}
        # bin id -> [claimed_cc, claimed_g] for items placed in THIS call.
        claimed: dict[UUID, list[Decimal]] = {}
        reserved = set(reserved_bin_ids or set())

        for item in put_away_list_items:
            packaging_unit = self._get_packaging_unit(item, db)
            base_unit = self._get_base_unit(item.item_id, db, base_unit_cache)
            required_volume_cc = self._calc_volume(
                item.quantity, packaging_unit, base_unit
            )
            required_weight_g = self._calc_weight(
                item.quantity, packaging_unit, base_unit
            )

            excluded = set(reserved)
            chosen: WarehouseLocation | None = None
            while True:
                candidate = self._find_best_bin(
                    item_id=item.item_id,
                    batch_number=item.batch_number,
                    warehouse_id=warehouse_id,
                    org_id=org_id,
                    required_volume_cc=required_volume_cc,
                    required_weight_g=required_weight_g,
                    db=db,
                    exclude_bin_ids=excluded,
                )
                if candidate is None:
                    break
                if self._fits(
                    candidate,
                    required_volume_cc,
                    required_weight_g,
                    claimed.get(candidate.id),
                    db,
                ):
                    chosen = candidate
                    break
                # The tightest bin is already filled by an earlier item in this
                # run — try the next-best candidate.
                excluded.add(candidate.id)

            # bin_loc may be None — that is acceptable (Req 7.7)
            item.bin_location_id = chosen.id if chosen else None
            if chosen is not None:
                bucket = claimed.setdefault(chosen.id, [Decimal("0"), Decimal("0")])
                bucket[0] += required_volume_cc or Decimal("0")
                bucket[1] += required_weight_g or Decimal("0")

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _fits(
        self,
        bin_loc: WarehouseLocation,
        required_volume_cc: Decimal | None,
        required_weight_g: Decimal | None,
        claimed: list[Decimal] | None,
        db: Session,
    ) -> bool:
        """Whether the bin still has room for the item, given in-run claims.

        Only dimensions the bin actually limits are checked; ``None`` on either
        side means unconstrained. Returns True immediately when the item carries
        no measurable requirement, so the common unconstrained path never
        touches the database.
        """
        if required_volume_cc is None and required_weight_g is None:
            return True

        max_cc = effective_bin_volume_limit_cc(bin_loc)
        max_g = effective_bin_weight_limit_g(bin_loc)
        need_cc = (
            required_volume_cc if (max_cc is not None and required_volume_cc) else None
        )
        need_g = (
            required_weight_g if (max_g is not None and required_weight_g) else None
        )
        if need_cc is None and need_g is None:
            return True

        occupied_cc, occupied_g = self._bin_occupied_cc_g(bin_loc.id, db)
        used_cc, used_g = claimed if claimed else (Decimal("0"), Decimal("0"))

        if need_cc is not None and (max_cc - occupied_cc - used_cc) < need_cc:
            return False
        if need_g is not None and (max_g - occupied_g - used_g) < need_g:
            return False
        return True

    @staticmethod
    def _bin_occupied_cc_g(bin_id: UUID, db: Session) -> tuple[Decimal, Decimal]:
        """Current occupied volume (cc) and weight (g) of a bin."""
        occupied_m3, occupied_kg = compute_bin_occupancy(db, bin_id)
        return occupied_m3 * CC_PER_M3, occupied_kg * G_PER_KG

    @staticmethod
    def _d(value) -> Decimal | None:
        """Coerce a numeric value (Decimal/int/float/str) to Decimal, else None.

        Mock objects (MagicMock) and other non-numeric values are treated as
        missing so the pure-logic tests remain green.
        """
        if value is None:
            return None
        if isinstance(value, (Decimal, int, float, str)):
            try:
                return Decimal(str(value))
            except Exception:
                return None
        return None

    @classmethod
    def _factor(cls, pu) -> Decimal:
        """Return the packaging unit's conversion factor (Eaches per pack).

        Non-numeric or missing factors fall back to 1 (base unit).
        """
        if pu is None:
            return Decimal("1")
        c = cls._d(getattr(pu, "conversion_factor", None))
        if c is None or c < 1:
            return Decimal("1")
        return c

    @classmethod
    def _unit_volume_cc(cls, pu) -> Decimal | None:
        """Volume of one packaging unit in cc (mm³ → cc)."""
        if pu is None:
            return None
        l = cls._d(getattr(pu, "length_mm", None))
        w = cls._d(getattr(pu, "width_mm", None))
        h = cls._d(getattr(pu, "height_mm", None))
        if l is None or w is None or h is None:
            return None
        return l * w * h / Decimal("1000")

    @classmethod
    def _unit_weight_g(cls, pu) -> Decimal | None:
        """Weight of one packaging unit in grams."""
        if pu is None:
            return None
        return cls._d(getattr(pu, "weight_grams", None))

    def _get_base_unit(
        self,
        item_id,
        db: Session,
        cache: dict | None = None,
    ) -> ItemPackagingUnit | None:
        """Return the item's base-unit packaging row, with a per-call cache."""
        if item_id is None:
            return None
        if cache is not None and item_id in cache:
            return cache[item_id]
        base = (
            db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.item_id == item_id,
                ItemPackagingUnit.is_base_unit.is_(True),
            )
            .first()
        )
        if cache is not None:
            cache[item_id] = base
        return base

    def _get_packaging_unit(
        self,
        item: PutAwayListItem,
        db: Session,
    ) -> ItemPackagingUnit | None:
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
        pu: ItemPackagingUnit | None,
        base_pu: ItemPackagingUnit | None = None,
    ) -> Decimal | None:
        """Calculate the required volume in cubic centimetres (cc), MC-aware.

        Intact master cartons occupy ``floor(qty / c)`` full cartons; the loose
        remainder occupies base-unit (IC) volume. Returns None (unconstrained)
        when neither the packaging unit nor the base unit carries dimensions.
        """
        qty = Decimal(str(quantity))
        c = self._factor(pu)
        n_full = qty // c
        n_loose = qty - n_full * c

        pu_vol = self._unit_volume_cc(pu)
        base_vol = self._unit_volume_cc(base_pu)
        full_vol = pu_vol if pu_vol is not None else base_vol
        if full_vol is None and base_vol is None:
            return None
        return n_full * (full_vol or Decimal("0")) + n_loose * (
            base_vol or Decimal("0")
        )

    def _calc_weight(
        self,
        quantity: Decimal,
        pu: ItemPackagingUnit | None,
        base_pu: ItemPackagingUnit | None = None,
    ) -> Decimal | None:
        """Calculate the required weight in grams, MC-aware.

        Returns None (unconstrained) when neither the packaging unit nor the
        base unit carries a weight.
        """
        qty = Decimal(str(quantity))
        c = self._factor(pu)
        n_full = qty // c
        n_loose = qty - n_full * c

        pu_w = self._unit_weight_g(pu)
        base_w = self._unit_weight_g(base_pu)
        full_w = pu_w if pu_w is not None else base_w
        if full_w is None and base_w is None:
            return None
        return n_full * (full_w or Decimal("0")) + n_loose * (base_w or Decimal("0"))

    def _find_best_bin(
        self,
        item_id: UUID,
        batch_number: str | None,
        warehouse_id: UUID,
        org_id: UUID,
        required_volume_cc: Decimal | None,
        required_weight_g: Decimal | None,
        db: Session,
        exclude_bin_ids: set[UUID] | None = None,
    ) -> WarehouseLocation | None:
        """Find the best available bin for the given item using volumetric SQL.

        The query uses four CTEs:
        - ``bin_usage``: computes currently occupied volume and weight per bin
          from bin_stock_levels joined to item_packaging_units.
        - ``limits``: resolves each bin's **effective** physical limit —
          ``max_volume_cc`` / ``max_weight_grams``, or a legacy ``capacity``
          whose ``capacity_uom`` is ``volume`` (m³) / ``weight`` (kg). This is
          what keeps a new-layout bin holding ``capacity = 1.2`` m³ from being
          read as a 1.2-item limit.
        - ``consolidation``: flags bins already holding the same
          (item_id, batch_number) combination.
        - ``alloc_rank``: the item group's allocation priority per bin.

        Ordering:
        1. Allocation rank (exclusive → preferred → unallocated).
        2. Consolidation bins first (COALESCE(has_same_item, FALSE) DESC).
        3. Tightest fit (smallest remaining volume) ASC.

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
            exclude_bin_ids: Bins to skip (worker reservations, or bins already
                filled by an earlier item in the same run).

        Returns:
            The best WarehouseLocation (bin), or None if no suitable bin exists.
        """
        item_group_id = None
        item = db.get(Item, item_id)
        if item is not None:
            item_group_id = item.item_group_id

        exclude_ids = [str(b) for b in (exclude_bin_ids or set())]
        exclude_clause = "AND wl.id NOT IN :exclude_bin_ids" if exclude_ids else ""

        sql = text(
            f"""
            WITH bin_usage AS (
                SELECT
                    bsl.bin_location_id,
                    COALESCE(SUM(
                        FLOOR(bsl.quantity_on_hand / NULLIF(GREATEST(COALESCE(ipu.conversion_factor, 1), 1), 0))
                        * (COALESCE(ipu.length_mm, base.length_mm, 0)
                           * COALESCE(ipu.width_mm, base.width_mm, 0)
                           * COALESCE(ipu.height_mm, base.height_mm, 0))
                        + MOD(bsl.quantity_on_hand, NULLIF(GREATEST(COALESCE(ipu.conversion_factor, 1), 1), 0))
                        * (COALESCE(base.length_mm, 0) * COALESCE(base.width_mm, 0) * COALESCE(base.height_mm, 0))
                    ) / 1000.0, 0) AS occupied_volume_cc,
                    COALESCE(SUM(
                        FLOOR(bsl.quantity_on_hand / NULLIF(GREATEST(COALESCE(ipu.conversion_factor, 1), 1), 0))
                        * COALESCE(ipu.weight_grams, base.weight_grams, 0)
                        + MOD(bsl.quantity_on_hand, NULLIF(GREATEST(COALESCE(ipu.conversion_factor, 1), 1), 0))
                        * COALESCE(base.weight_grams, 0)
                    ), 0) AS occupied_weight_g
                FROM bin_stock_levels bsl
                LEFT JOIN item_packaging_units ipu ON ipu.id = bsl.packaging_unit_id
                LEFT JOIN item_packaging_units base
                       ON base.item_id = bsl.item_id AND base.is_base_unit = TRUE
                WHERE bsl.organization_id = :org_id
                GROUP BY bsl.bin_location_id
            ),
            limits AS (
                SELECT
                    wl.id AS bin_id,
                    CASE
                        WHEN wl.max_volume_cc IS NOT NULL THEN wl.max_volume_cc
                        WHEN LOWER(COALESCE(wl.capacity_uom, '')) = 'volume' AND wl.capacity > 0
                            THEN wl.capacity * 1000000
                        ELSE NULL
                    END AS max_cc,
                    CASE
                        WHEN wl.max_weight_grams IS NOT NULL THEN wl.max_weight_grams
                        WHEN LOWER(COALESCE(wl.capacity_uom, '')) = 'weight' AND wl.capacity > 0
                            THEN wl.capacity * 1000
                        ELSE NULL
                    END AS max_g
                FROM warehouse_locations wl
                WHERE wl.organization_id = :org_id
                  AND wl.warehouse_id    = :warehouse_id
                  AND wl.location_type   = 'bin'
                  AND wl.is_active       = TRUE
                  AND wl.is_pickable     = TRUE
            ),
            consolidation AS (
                SELECT bin_location_id, TRUE AS has_same_item
                FROM bin_stock_levels
                WHERE item_id = :item_id
                  AND batch_number IS NOT DISTINCT FROM :batch_number
                  AND organization_id = :org_id
                  AND quantity_on_hand > 0
            ),
            alloc_rank AS (
                SELECT la.location_id,
                       MIN(CASE la.allocation_type
                           WHEN 'exclusive' THEN 0
                           WHEN 'preferred' THEN 1
                           ELSE 2 END) AS rank
                FROM location_allocations la
                WHERE la.organization_id = :org_id
                  AND la.is_active = TRUE
                  AND la.item_group_id = :item_group_id
                GROUP BY la.location_id
            )
            SELECT wl.id
            FROM warehouse_locations wl
            LEFT JOIN bin_usage bu ON bu.bin_location_id = wl.id
            LEFT JOIN limits l ON l.bin_id = wl.id
            LEFT JOIN consolidation c ON c.bin_location_id = wl.id
            LEFT JOIN alloc_rank ar ON ar.location_id = wl.id
            WHERE wl.organization_id = :org_id
              AND wl.warehouse_id    = :warehouse_id
              AND wl.location_type   = 'bin'
              AND wl.is_active       = TRUE
              AND wl.is_pickable     = TRUE
              AND (
                  l.max_cc IS NULL
                  OR :required_volume_cc IS NULL
                  OR (l.max_cc - COALESCE(bu.occupied_volume_cc, 0)) >= :required_volume_cc
              )
              AND (
                  l.max_g IS NULL
                  OR :required_weight_g IS NULL
                  OR (l.max_g - COALESCE(bu.occupied_weight_g, 0)) >= :required_weight_g
              )
              {exclude_clause}
            ORDER BY
                COALESCE(ar.rank, 2) ASC,
                COALESCE(c.has_same_item, FALSE) DESC,
                (l.max_cc - COALESCE(bu.occupied_volume_cc, 0)) ASC,
                wl.id ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        )

        params = {
            "org_id": str(org_id),
            "warehouse_id": str(warehouse_id),
            "item_id": str(item_id),
            "batch_number": batch_number,
            "item_group_id": str(item_group_id) if item_group_id else None,
            "required_volume_cc": (
                float(required_volume_cc) if required_volume_cc is not None else None
            ),
            "required_weight_g": (
                float(required_weight_g) if required_weight_g is not None else None
            ),
        }

        statement = sql
        if exclude_ids:
            statement = sql.bindparams(bindparam("exclude_bin_ids", expanding=True))
            params["exclude_bin_ids"] = exclude_ids

        result = db.execute(statement, params).fetchone()
        if result is None:
            return None

        bin_id = result[0]
        return db.get(WarehouseLocation, bin_id)
