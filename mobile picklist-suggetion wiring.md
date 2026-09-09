Fixed. The "suggested bin service" was never wired into the mobile pick flow.


Root cause
Pick lists can be generated in two modes (OutboundOrderService.create_pick_lists_from_order(..., mode)):

auto → calls resolve_bin_locations (FIFO/FEFO) and reserves bins, so each line has a bin_location_id.
manual → deliberately leaves bin_location_id = NULL (the worker assigns bins while picking).
The mobile PickScreen only read the pre-assigned bin_location_path / bin_location_id for its "📍 bin" hint — which is NULL in manual mode. The smart suggestion engine (POST /wms-3d/suggest, task_type='pick') existed but was only used by the web 3D warehouse view, never the mobile app.

I confirmed the data path: active pick lists PL-2026-00008 (in_progress, 2 items) and PL-2026-00004 (draft, 1 item) had 0 items with bins — the manual-mode ones.

Changes (mobile BWmobile)
src/api/pickService.ts — added suggestPickBins() that calls POST /wms-3d/suggest with task_type: 'pick'.
src/types/pick.ts — added PickBinSuggestion / PickBinSuggestResponse types.
src/screens/PickScreen.tsx — added loadSuggestedBins(): when the pick list loads, for every line with no assigned bin it fetches the top-ranked bin (per item_id, best-effort) and stores the label.
src/components/pick/PickItemsTable.tsx — shows "📍 Suggested: {bin}" for manual-mode lines that have no resolved bin (auto-mode lines keep the existing "📍 {bin}").
The suggestion service's bin_code is WarehouseLocation.full_path or code, so it displays the same human-readable path as auto mode.

Verified
No TypeScript/lint errors in the four edited files.
The endpoint is reachable from the mobile client (coreClient base URL includes /api/v1).
warehouse_work_user already has warehouse.read, which /wms-3d/suggest requires — so the worker's token can call it.
Note: suggestions are a hint only — in manual mode the worker still assigns the actual bin during picking, matching the backend's intent.