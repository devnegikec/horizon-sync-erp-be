"""DEPRECATED — the wms_workers table was consolidated into identity `users`.

Warehouse workers are now first-class `users` rows (user_type =
warehouse_worker) with warehouse assignment via `warehouse_users`. The
`wms_workers` table and its `WMSWorker` model have been retired (see
identity-service migration 018). This module is kept only as a stub so any
stale import fails loudly at attribute access rather than silently mapping a
dropped table.
"""

raise ImportError(
    "app.models.wms_worker is deprecated: workers now live in identity `users` "
    "(user_type='warehouse_worker'). Use the identity /identity/workers API."
)
