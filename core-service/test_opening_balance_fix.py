"""
Test script to verify opening balance fix for Chart of Account creation
"""

from app.schemas.chart_of_account import ChartOfAccountCreate, ChartOfAccountResponse


def test_opening_balance_schema():
    """Test that opening_balance field is properly included in schemas"""

    # Test ChartOfAccountCreate schema accepts opening_balance
    try:
        create_data = ChartOfAccountCreate(
            account_code="TEST001",
            account_name="Test Account",
            account_type="asset",
            opening_balance=1000.0,
        )
        print("✅ ChartOfAccountCreate successfully accepts opening_balance field")
        print(f"   Created with opening_balance: {create_data.opening_balance}")
    except Exception as e:
        print(f"❌ ChartOfAccountCreate failed to accept opening_balance: {e}")
        return False

    # Test that we can access opening_balance field
    assert hasattr(create_data, "opening_balance"), (
        "opening_balance field should be accessible"
    )
    assert create_data.opening_balance == 1000.0, (
        f"opening_balance should be 1000.0, got {create_data.opening_balance}"
    )

    # Test response schema structure
    try:
        # Create a mock response data
        response_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "organization_id": "123e4567-e89b-12d3-a456-426614174001",
            "account_code": "TEST001",
            "account_name": "Test Account",
            "account_type": "asset",
            "parent_account_id": None,
            "parent": None,
            "currency": "USD",
            "status": "active",
            "is_posting_account": True,
            "description": None,
            "opening_balance": 1000.0,
            "current_balance": 1000.0,
            "created_by": "user123",
            "updated_by": "user123",
            "created_at": "2026-02-27T10:11:38.463290Z",
            "updated_at": "2026-02-27T10:11:38.463296Z",
        }

        response = ChartOfAccountResponse(**response_data)
        print("✅ ChartOfAccountResponse successfully includes opening_balance field")
        print(f"   Response opening_balance: {response.opening_balance}")
        print(f"   Response current_balance: {response.current_balance}")

    except Exception as e:
        print(f"❌ ChartOfAccountResponse failed to include balance fields: {e}")
        return False

    return True


def test_schema_validation():
    """Test various opening_balance scenarios"""

    # Test with None opening_balance
    try:
        create_data = ChartOfAccountCreate(
            account_code="TEST002",
            account_name="Test Account 2",
            account_type="asset",
            opening_balance=None,
        )
        print("✅ ChartOfAccountCreate accepts None opening_balance")
        assert create_data.opening_balance is None
    except Exception as e:
        print(f"❌ ChartOfAccountCreate failed with None opening_balance: {e}")
        return False

    # Test without opening_balance (should default to None)
    try:
        create_data = ChartOfAccountCreate(
            account_code="TEST003", account_name="Test Account 3", account_type="asset"
        )
        print("✅ ChartOfAccountCreate works without opening_balance field")
        assert create_data.opening_balance is None
    except Exception as e:
        print(f"❌ ChartOfAccountCreate failed without opening_balance: {e}")
        return False

    # Test with negative opening_balance
    try:
        create_data = ChartOfAccountCreate(
            account_code="TEST004",
            account_name="Test Account 4",
            account_type="liability",
            opening_balance=-500.0,
        )
        print("✅ ChartOfAccountCreate accepts negative opening_balance")
        assert create_data.opening_balance == -500.0
    except Exception as e:
        print(f"❌ ChartOfAccountCreate failed with negative opening_balance: {e}")
        return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("TESTING OPENING BALANCE SCHEMA FIX")
    print("=" * 60)

    success1 = test_opening_balance_schema()
    print()
    success2 = test_schema_validation()

    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    if success1 and success2:
        print("🎉 All tests passed! Opening balance fix appears to be working.")
        print()
        print("The fix includes:")
        print("  ✅ ChartOfAccountCreate now accepts opening_balance field")
        print("  ✅ ChartOfAccountResponse now includes opening_balance field")
        print("  ✅ ChartOfAccountResponse now includes current_balance field")
        print(
            "  ✅ Schemas handle various opening_balance scenarios (None, negative, etc.)"
        )
        print()
        print("Next steps:")
        print("  1. Test with actual API endpoint")
        print("  2. Verify service logic calculates balance correctly")
        print("  3. Check if journal entries are created properly")

        exit(0)
    else:
        print("❌ Some tests failed. Schema fix needs more work.")
        exit(1)
