"""Temporary script to verify scan-events routes are registered."""
from app.api.v1.router import api_router

routes = [r.path for r in api_router.routes]
scan_event_routes = [r for r in routes if "scan-events" in r]
print(f"Scan event routes found: {scan_event_routes}")
assert len(scan_event_routes) > 0, "No scan-events routes found!"
print("All good - scan-events endpoint registered successfully")
