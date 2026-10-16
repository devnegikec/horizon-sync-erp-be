"""Throwaway: what does the layout compiler/materialiser put on a bin? Delete me."""

from __future__ import annotations

import json
import uuid

from app.layout_design.compile import build_layout
from app.layout_design.materialize import materialize_layout

with open("/tmp/layout.json") as fh:
    doc = json.load(fh)

compiled = build_layout(doc)
print("applyable:", compiled.applyable)
print("diagnostics:", [(d.code, d.severity) for d in compiled.diagnostics][:12])
print("utilization:", doc.get("layout", {}).get("utilization"))

summary = compiled.summary()
print("summary:", summary)

bins = compiled.bins
first = bins[0]
print(
    "first bin:",
    f"{first.path} raw_volume={first.capacityM3} m3 "
    f"usable={first.usableVolumeM3} m3 maxVolumeCc={first.maxVolumeCc} "
    f"maxWeightKg={first.maxWeightKg}",
)

a01l = sorted(
    {b.baySeq for b in bins if b.aisleCode == "A01" and b.laneCode == "A01-L"}
)
print("A01-L baySeqs that produced bins:", a01l)

materialized = materialize_layout(
    compiled,
    organization_id=uuid.uuid4(),
    warehouse_id=uuid.uuid4(),
    qr_codes=None,
    existing_paths={},
)
bin_rows = [r for r in materialized.rows if r.location_type == "bin"]
non_bin = [r for r in materialized.rows if r.location_type != "bin"]
r = bin_rows[0]
print(
    "materialised BIN row columns:",
    f"capacity={r.capacity} total_capacity={r.total_capacity} "
    f"available_capacity={r.available_capacity} capacity_uom={r.capacity_uom} "
    f"max_volume_cc={r.max_volume_cc} max_weight_grams={r.max_weight_grams}",
)
sample = non_bin[0]
print(
    "materialised parent row (e.g. zone/aisle):",
    f"type={sample.location_type} capacity={sample.capacity} "
    f"total_capacity={sample.total_capacity} "
    f"available_capacity={sample.available_capacity}",
)
print("rows:", len(materialized.rows), "bins:", len(bin_rows))
