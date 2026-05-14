"""Quick verification script for WarehouseLocation model"""
import sys
sys.path.insert(0, '.')

from app.models.warehouse_location import (
    WarehouseLocation,
    LocationType,
    PutAwayListStatus,
    PutAwayListItemStatus,
    WorkerTaskType,
    WorkerTaskStatus,
    ScanType,
    AllocationType,
)

print("Enums:")
print(f"  LocationType values: {[e.value for e in LocationType]}")
print(f"  PutAwayListStatus values: {[e.value for e in PutAwayListStatus]}")
print(f"  PutAwayListItemStatus values: {[e.value for e in PutAwayListItemStatus]}")
print(f"  WorkerTaskType values: {[e.value for e in WorkerTaskType]}")
print(f"  WorkerTaskStatus values: {[e.value for e in WorkerTaskStatus]}")
print(f"  ScanType values: {[e.value for e in ScanType]}")
print(f"  AllocationType values: {[e.value for e in AllocationType]}")
print()

print("Model columns:")
for col in WarehouseLocation.__table__.columns:
    print(f"  {col.name}: {col.type}")

print()
print("Constraints:")
for constraint in WarehouseLocation.__table__.constraints:
    print(f"  {constraint}")

print()
print("Relationships:")
for rel in WarehouseLocation.__mapper__.relationships:
    print(f"  {rel.key} -> {rel.mapper.class_.__name__}")

print()
print("All checks passed!")
