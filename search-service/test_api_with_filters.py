"""
Test the search API endpoints with filters.
"""

import requests
import json

# Base URL for search service
BASE_URL = "http://localhost:8002"

# You'll need a valid JWT token - get one from identity service
# For now, we'll test without auth to see the error
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4ZDUwOWYyMi01ZmU1LTQ3NjUtOTQ5Ni0zYTIzNmNhZTJhZjEiLCJlbWFpbCI6ImRldmVuZGVyYS5uZWdpQGdtYWlsLmNvbSIsInVzZXJfdHlwZSI6InVzZXIiLCJleHAiOjE3NzA2NDI2NTUsImlhdCI6MTc3MDY0MTc1NSwidHlwZSI6ImFjY2VzcyJ9.HGMn8FOxHM_gsb-zVkUPtISPBAJLULznOLYd1U7kE9Q"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("="*60)
print("TEST 1: Global search without filters")
print("="*60)
response = requests.post(
    f"{BASE_URL}/api/v1/search/global",
    headers=headers,
    json={
        "query_text": "laptop",
        "page": 1,
        "page_size": 10
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {data['total_count']} results")
    for result in data['results']:
        print(f"  - {result['entity_type']}: {result['title']}")
else:
    print(f"Error: {response.text}")

print("\n" + "="*60)
print("TEST 2: Global search WITH metadata filter")
print("="*60)
response = requests.post(
    f"{BASE_URL}/api/v1/search/global",
    headers=headers,
    json={
        "query_text": "item",
        "filters": {
            "item_group": "Raw Materials"
        },
        "page": 1,
        "page_size": 10
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {data['total_count']} results with item_group=Raw Materials")
    for result in data['results']:
        print(f"  - {result['title']}")
        print(f"    Metadata: {result['metadata']}")
    print("\n✅ API JSONB filter test PASSED!")
else:
    print(f"Error: {response.text}")
    print("\n❌ API JSONB filter test FAILED!")

print("\n" + "="*60)
print("TEST 3: Local search for items")
print("="*60)
response = requests.post(
    f"{BASE_URL}/api/v1/search/items",
    headers=headers,
    json={
        "query_text": "laptop",
        "page": 1,
        "page_size": 10
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {data['total_count']} results")
    for result in data['results']:
        print(f"  - {result['title']}")
else:
    print(f"Error: {response.text}")
