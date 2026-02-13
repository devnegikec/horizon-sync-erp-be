"""
Test script to verify search API endpoints are accessible.

Run this script to test the search service endpoints:
    python test_api_endpoint.py
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8002"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4ZDUwOWYyMi01ZmU1LTQ3NjUtOTQ5Ni0zYTIzNmNhZTJhZjEiLCJlbWFpbCI6ImRldmVuZGVyYS5uZWdpQGdtYWlsLmNvbSIsInVzZXJfdHlwZSI6InVzZXIiLCJleHAiOjE3NzA2NDI2NTUsImlhdCI6MTc3MDY0MTc1NSwidHlwZSI6ImFjY2VzcyJ9.HGMn8FOxHM_gsb-zVkUPtISPBAJLULznOLYd1U7kE9Q"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("Testing Health Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_docs():
    """Test if OpenAPI docs are accessible"""
    print("\n" + "="*60)
    print("Testing OpenAPI Docs")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Docs accessible: {response.status_code == 200}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_openapi_json():
    """Test OpenAPI JSON to see available endpoints"""
    print("\n" + "="*60)
    print("Testing OpenAPI JSON (Available Endpoints)")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            openapi = response.json()
            print("\nAvailable Paths:")
            for path in openapi.get("paths", {}).keys():
                print(f"  - {path}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_global_search():
    """Test global search endpoint"""
    print("\n" + "="*60)
    print("Testing Global Search Endpoint")
    print("="*60)
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }
    
    payload = {
        "query": "RM-ALM-011",
        "entity_types": ["items"],
        "filters": {},
        "page": 1,
        "page_size": 20
    }
    
    print(f"\nURL: {BASE_URL}/api/v1/search/global")
    print(f"Headers: {json.dumps({k: v[:50] + '...' if len(v) > 50 else v for k, v in headers.items()}, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/search/global",
            headers=headers,
            json=payload,
            timeout=10
        )
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Connection failed - {e}")
        print("\nPossible issues:")
        print("  1. Search service is not running")
        print("  2. Service is running on a different port")
        print("  3. Docker container is not accessible")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_local_search():
    """Test local search endpoint"""
    print("\n" + "="*60)
    print("Testing Local Search Endpoint")
    print("="*60)
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }
    
    payload = {
        "query": "RM-ALM-011",
        "page": 1,
        "page_size": 20
    }
    
    print(f"\nURL: {BASE_URL}/api/v1/search/items")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/search/items",
            headers=headers,
            json=payload,
            timeout=10
        )
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SEARCH SERVICE API ENDPOINT TESTS")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    
    results = {
        "Health Check": test_health(),
        "OpenAPI Docs": test_docs(),
        "OpenAPI JSON": test_openapi_json(),
        "Global Search": test_global_search(),
        "Local Search": test_local_search(),
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    print("\n" + "="*60)
    if all(results.values()):
        print("All tests passed! ✓")
    else:
        print("Some tests failed. Check the output above for details.")
        print("\nTroubleshooting steps:")
        print("1. Verify the search service is running: docker ps | grep horizon_search")
        print("2. Check service logs: docker logs horizon_search")
        print("3. Verify the service is listening on port 8002")
        print("4. Check if migrations ran successfully")
        print("5. Verify the JWT token is valid and not expired")
    print("="*60)


if __name__ == "__main__":
    main()
