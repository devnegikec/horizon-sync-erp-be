-- ============================================================
-- Clone warehouse_locations from Main Warehouse to Warehouse Ecity
-- Source: cbf290a6-91cb-4c93-b9a6-db408bb3c274 (Main Warehouse)
-- Target: 504e646f-16be-4bba-b903-6a28e2730db2 (Warehouse Ecity)
-- Usage: docker exec -i horizon_postgres psql -U horizon_user -d core_db -f - < scripts/clone_warehouse_locations.sql
-- ============================================================

BEGIN;

-- Temp table: maps old source ID → new target ID (cumulative across all levels)
CREATE TEMP TABLE _id_map (
    old_id UUID PRIMARY KEY,
    new_id UUID NOT NULL
);

-- Helper: insert one level and populate _id_map
CREATE OR REPLACE FUNCTION pg_temp.clone_level(
    p_location_type TEXT,
    p_source_wh UUID,
    p_target_wh UUID,
    p_org_id UUID,
    p_now TIMESTAMPTZ
) RETURNS INT AS $$
DECLARE
    v_count INT;
BEGIN
    -- Insert new locations, using _id_map to resolve parent IDs
    INSERT INTO warehouse_locations (
        id, organization_id, warehouse_id, parent_location_id,
        location_type, code, full_path, name,
        capacity, total_capacity, available_capacity, capacity_uom,
        position_x, position_y, is_active, version,
        created_at, updated_at
    )
    SELECT
        gen_random_uuid(), p_org_id, p_target_wh,
        CASE WHEN src.parent_location_id IS NULL THEN NULL
             ELSE m.new_id END,
        src.location_type, src.code, src.full_path, src.name,
        src.capacity, src.total_capacity, src.available_capacity, src.capacity_uom,
        src.position_x, src.position_y, src.is_active, src.version,
        p_now, p_now
    FROM warehouse_locations src
    LEFT JOIN _id_map m ON m.old_id = src.parent_location_id
    WHERE src.warehouse_id = p_source_wh
      AND src.location_type = p_location_type
      AND src.is_active = TRUE
      AND (src.parent_location_id IS NULL OR m.new_id IS NOT NULL);

    GET DIAGNOSTICS v_count = ROW_COUNT;

    -- Populate _id_map: match by (warehouse_id, location_type, parent, code)
    INSERT INTO _id_map (old_id, new_id)
    SELECT src.id, tgt.id
    FROM warehouse_locations src
    JOIN warehouse_locations tgt
        ON tgt.warehouse_id = p_target_wh
        AND tgt.location_type = src.location_type
        AND tgt.code = src.code
        AND (
            (tgt.parent_location_id IS NULL AND src.parent_location_id IS NULL)
            OR tgt.parent_location_id = (
                SELECT m2.new_id FROM _id_map m2 WHERE m2.old_id = src.parent_location_id
            )
        )
    WHERE src.warehouse_id = p_source_wh
      AND src.location_type = p_location_type
      AND src.id NOT IN (SELECT old_id FROM _id_map);

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Clone each level in dependency order
DO $$
DECLARE
    v_target_wh UUID := '504e646f-16be-4bba-b903-6a28e2730db2';
    v_source_wh UUID := 'cbf290a6-91cb-4c93-b9a6-db408bb3c274';
    v_org_id UUID := 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150';
    v_now TIMESTAMPTZ := NOW();
    v_count INT;
BEGIN
    SELECT pg_temp.clone_level('zone', v_source_wh, v_target_wh, v_org_id, v_now) INTO v_count;
    RAISE NOTICE '[1/5] Zones cloned: % rows', v_count;

    SELECT pg_temp.clone_level('aisle', v_source_wh, v_target_wh, v_org_id, v_now) INTO v_count;
    RAISE NOTICE '[2/5] Aisles cloned: % rows', v_count;

    SELECT pg_temp.clone_level('bay', v_source_wh, v_target_wh, v_org_id, v_now) INTO v_count;
    RAISE NOTICE '[3/5] Bays cloned: % rows', v_count;

    SELECT pg_temp.clone_level('level', v_source_wh, v_target_wh, v_org_id, v_now) INTO v_count;
    RAISE NOTICE '[4/5] Levels cloned: % rows', v_count;

    SELECT pg_temp.clone_level('bin', v_source_wh, v_target_wh, v_org_id, v_now) INTO v_count;
    RAISE NOTICE '[5/5] Bins cloned: % rows', v_count;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Clone complete!';
    RAISE NOTICE '========================================';
END $$;

DROP FUNCTION IF EXISTS pg_temp.clone_level;
DROP TABLE IF EXISTS _id_map;

COMMIT;
