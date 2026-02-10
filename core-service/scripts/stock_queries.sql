-- Common SQL Queries for Stock Management Data
-- Use these queries to verify and explore the seeded stock data

-- ============================================================================
-- STOCK LEVELS QUERIES
-- ============================================================================

-- 1. View all stock levels with item and warehouse details
SELECT 
    sl.id,
    i.item_code,
    i.item_name,
    w.code as warehouse_code,
    w.name as warehouse_name,
    sl.quantity_on_hand,
    sl.quantity_reserved,
    sl.quantity_available,
    sl.last_counted_at
FROM stock_levels sl
JOIN items i ON sl.product_id = i.id
JOIN warehouses_extended w ON sl.warehouse_id = w.id
ORDER BY w.code, i.item_code;

-- 2. Stock levels by warehouse
SELECT 
    w.name as warehouse,
    COUNT(*) as items_count,
    SUM(sl.quantity_on_hand) as total_quantity
FROM stock_levels sl
JOIN warehouses_extended w ON sl.warehouse_id = w.id
GROUP BY w.name;

-- 3. Items below reorder level
SELECT 
    i.item_code,
    i.item_name,
    i.reorder_level,
    SUM(sl.quantity_available) as total_available
FROM items i
LEFT JOIN stock_levels sl ON i.id = sl.product_id
WHERE i.maintain_stock = true
GROUP BY i.id, i.item_code, i.item_name, i.reorder_level
HAVING SUM(sl.quantity_available) < i.reorder_level;

-- 4. Stock value by warehouse
SELECT 
    w.name as warehouse,
    SUM(sl.quantity_on_hand * i.valuation_rate) as stock_value
FROM stock_levels sl
JOIN items i ON sl.product_id = i.id
JOIN warehouses_extended w ON sl.warehouse_id = w.id
GROUP BY w.name
ORDER BY stock_value DESC;

-- ============================================================================
-- STOCK MOVEMENTS QUERIES
-- ============================================================================

-- 5. All stock movements with details
SELECT 
    sm.id,
    sm.movement_type,
    i.item_code,
    i.item_name,
    w.code as warehouse_code,
    sm.quantity,
    sm.unit_cost,
    sm.reference_type,
    sm.notes,
    sm.performed_at
FROM stock_movements sm
JOIN items i ON sm.product_id = i.id
JOIN warehouses_extended w ON sm.warehouse_id = w.id
ORDER BY sm.performed_at DESC;

-- 6. Movement summary by type
SELECT 
    movement_type,
    COUNT(*) as movement_count,
    SUM(quantity) as total_quantity,
    SUM(quantity * unit_cost) as total_value
FROM stock_movements
GROUP BY movement_type;

-- 7. Movement history for a specific item
SELECT 
    sm.performed_at,
    sm.movement_type,
    w.name as warehouse,
    sm.quantity,
    sm.unit_cost,
    sm.notes
FROM stock_movements sm
JOIN warehouses_extended w ON sm.warehouse_id = w.id
WHERE sm.product_id = (SELECT id FROM items WHERE item_code = 'FG-WIDGET-001')
ORDER BY sm.performed_at DESC;

-- 8. Daily movement summary
SELECT 
    DATE(performed_at) as movement_date,
    movement_type,
    COUNT(*) as transactions,
    SUM(quantity) as total_quantity
FROM stock_movements
GROUP BY DATE(performed_at), movement_type
ORDER BY movement_date DESC;

-- ============================================================================
-- STOCK ENTRIES QUERIES
-- ============================================================================

-- 9. All stock entries with summary
SELECT 
    se.stock_entry_no,
    se.stock_entry_type,
    se.posting_date,
    se.status,
    fw.name as from_warehouse,
    tw.name as to_warehouse,
    se.total_value,
    se.remarks,
    COUNT(sei.id) as item_count
FROM stock_entries se
LEFT JOIN warehouses_extended fw ON se.from_warehouse_id = fw.id
LEFT JOIN warehouses_extended tw ON se.to_warehouse_id = tw.id
LEFT JOIN stock_entry_items sei ON se.id = sei.stock_entry_id
GROUP BY se.id, se.stock_entry_no, se.stock_entry_type, se.posting_date, 
         se.status, fw.name, tw.name, se.total_value, se.remarks
ORDER BY se.posting_date DESC;

-- 10. Stock entry details with items
SELECT 
    se.stock_entry_no,
    se.stock_entry_type,
    i.item_code,
    i.item_name,
    sei.qty,
    sei.uom,
    sei.basic_rate,
    sei.basic_amount,
    sw.name as source_warehouse,
    tw.name as target_warehouse
FROM stock_entries se
JOIN stock_entry_items sei ON se.id = sei.stock_entry_id
JOIN items i ON sei.item_id = i.id
LEFT JOIN warehouses_extended sw ON sei.source_warehouse_id = sw.id
LEFT JOIN warehouses_extended tw ON sei.target_warehouse_id = tw.id
WHERE se.stock_entry_no = 'STE-2024-001';

-- 11. Stock entries by type
SELECT 
    stock_entry_type,
    COUNT(*) as entry_count,
    SUM(total_value) as total_value,
    AVG(total_value) as avg_value
FROM stock_entries
GROUP BY stock_entry_type;

-- 12. Recent stock entries (last 7 days)
SELECT 
    se.stock_entry_no,
    se.stock_entry_type,
    se.posting_date,
    se.status,
    se.total_value
FROM stock_entries se
WHERE se.posting_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY se.posting_date DESC;

-- ============================================================================
-- STOCK RECONCILIATIONS QUERIES
-- ============================================================================

-- 13. All reconciliations with summary
SELECT 
    sr.reconciliation_no,
    sr.purpose,
    sr.posting_date,
    sr.status,
    COUNT(sri.id) as item_count,
    SUM(sri.qty_difference) as total_difference
FROM stock_reconciliations sr
LEFT JOIN stock_reconciliation_items sri ON sr.id = sri.reconciliation_id
GROUP BY sr.id, sr.reconciliation_no, sr.purpose, sr.posting_date, sr.status
ORDER BY sr.posting_date DESC;

-- 14. Reconciliation details with items
SELECT 
    sr.reconciliation_no,
    sr.purpose,
    i.item_code,
    i.item_name,
    w.name as warehouse,
    sri.current_qty,
    sri.qty as counted_qty,
    sri.qty_difference,
    sri.valuation_rate,
    (sri.qty_difference * sri.valuation_rate) as value_difference
FROM stock_reconciliations sr
JOIN stock_reconciliation_items sri ON sr.id = sri.reconciliation_id
JOIN items i ON sri.item_id = i.id
JOIN warehouses_extended w ON sri.warehouse_id = w.id
WHERE sr.reconciliation_no = 'RECON-2024-001';

-- 15. Reconciliation impact summary
SELECT 
    sr.reconciliation_no,
    sr.purpose,
    SUM(CASE WHEN sri.qty_difference > 0 THEN sri.qty_difference ELSE 0 END) as total_gains,
    SUM(CASE WHEN sri.qty_difference < 0 THEN ABS(sri.qty_difference) ELSE 0 END) as total_losses,
    SUM(ABS(sri.qty_difference * sri.valuation_rate)) as total_value_impact
FROM stock_reconciliations sr
JOIN stock_reconciliation_items sri ON sr.id = sri.reconciliation_id
GROUP BY sr.id, sr.reconciliation_no, sr.purpose;

-- ============================================================================
-- COMBINED ANALYSIS QUERIES
-- ============================================================================

-- 16. Stock movement vs current levels
SELECT 
    i.item_code,
    i.item_name,
    SUM(CASE WHEN sm.movement_type = 'in' THEN sm.quantity ELSE 0 END) as total_in,
    SUM(CASE WHEN sm.movement_type = 'out' THEN sm.quantity ELSE 0 END) as total_out,
    SUM(CASE WHEN sm.movement_type = 'in' THEN sm.quantity 
             WHEN sm.movement_type = 'out' THEN -sm.quantity 
             ELSE 0 END) as net_movement,
    COALESCE(SUM(sl.quantity_on_hand), 0) as current_stock
FROM items i
LEFT JOIN stock_movements sm ON i.id = sm.product_id
LEFT JOIN stock_levels sl ON i.id = sl.product_id
WHERE i.maintain_stock = true
GROUP BY i.id, i.item_code, i.item_name;

-- 17. Warehouse utilization
SELECT 
    w.name as warehouse,
    w.total_capacity,
    w.capacity_uom,
    COUNT(DISTINCT sl.product_id) as unique_items,
    SUM(sl.quantity_on_hand) as total_quantity,
    SUM(sl.quantity_on_hand * i.valuation_rate) as total_value
FROM warehouses_extended w
LEFT JOIN stock_levels sl ON w.id = sl.warehouse_id
LEFT JOIN items i ON sl.product_id = i.id
GROUP BY w.id, w.name, w.total_capacity, w.capacity_uom;

-- 18. Item movement frequency
SELECT 
    i.item_code,
    i.item_name,
    COUNT(sm.id) as movement_count,
    MIN(sm.performed_at) as first_movement,
    MAX(sm.performed_at) as last_movement,
    SUM(CASE WHEN sm.movement_type = 'in' THEN sm.quantity ELSE 0 END) as total_received,
    SUM(CASE WHEN sm.movement_type = 'out' THEN sm.quantity ELSE 0 END) as total_issued
FROM items i
LEFT JOIN stock_movements sm ON i.id = sm.product_id
WHERE i.maintain_stock = true
GROUP BY i.id, i.item_code, i.item_name
ORDER BY movement_count DESC;

-- 19. Stock aging analysis (items not moved recently)
SELECT 
    i.item_code,
    i.item_name,
    w.name as warehouse,
    sl.quantity_on_hand,
    sl.last_counted_at,
    MAX(sm.performed_at) as last_movement_date,
    CURRENT_DATE - DATE(MAX(sm.performed_at)) as days_since_movement
FROM stock_levels sl
JOIN items i ON sl.product_id = i.id
JOIN warehouses_extended w ON sl.warehouse_id = w.id
LEFT JOIN stock_movements sm ON i.id = sm.product_id AND w.id = sm.warehouse_id
GROUP BY i.id, i.item_code, i.item_name, w.name, sl.quantity_on_hand, sl.last_counted_at
HAVING MAX(sm.performed_at) IS NOT NULL
ORDER BY days_since_movement DESC;

-- 20. Complete stock audit trail for an item
SELECT 
    'Stock Entry' as source,
    se.stock_entry_no as reference,
    se.posting_date as date,
    sei.qty as quantity,
    tw.name as warehouse,
    'IN' as direction
FROM stock_entry_items sei
JOIN stock_entries se ON sei.stock_entry_id = se.id
JOIN items i ON sei.item_id = i.id
LEFT JOIN warehouses_extended tw ON sei.target_warehouse_id = tw.id
WHERE i.item_code = 'FG-WIDGET-001'

UNION ALL

SELECT 
    'Stock Movement' as source,
    sm.reference_type as reference,
    sm.performed_at as date,
    sm.quantity,
    w.name as warehouse,
    sm.movement_type as direction
FROM stock_movements sm
JOIN items i ON sm.product_id = i.id
JOIN warehouses_extended w ON sm.warehouse_id = w.id
WHERE i.item_code = 'FG-WIDGET-001'

UNION ALL

SELECT 
    'Reconciliation' as source,
    sr.reconciliation_no as reference,
    sr.posting_date as date,
    sri.qty_difference as quantity,
    w.name as warehouse,
    CASE WHEN sri.qty_difference > 0 THEN 'GAIN' ELSE 'LOSS' END as direction
FROM stock_reconciliation_items sri
JOIN stock_reconciliations sr ON sri.reconciliation_id = sr.id
JOIN items i ON sri.item_id = i.id
JOIN warehouses_extended w ON sri.warehouse_id = w.id
WHERE i.item_code = 'FG-WIDGET-001'

ORDER BY date DESC;
