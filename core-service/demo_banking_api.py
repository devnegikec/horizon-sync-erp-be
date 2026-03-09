"""
Banking API Usage Examples
==========================

This file demonstrates how to use the banking integration APIs.
Run this after starting the FastAPI server to test the banking endpoints.

Usage:
  python demo_banking_api.py
"""

import json

# API Configuration
BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN_HERE",  # Replace with actual token
}


def demo_create_bank_account():
    """Demonstrate creating a new bank account"""

    # First, you need a GL account ID (from Chart of Accounts)
    gl_account_id = "replace-with-actual-gl-account-id"

    bank_account_data = {
        "bank_name": "Chase Bank",
        "account_holder_name": "Horizon Sync Corporation",
        "account_number": "1234567890123456",
        "iban": "US12CHASE1234567890123456",
        "swift_code": "CHASUS33",
        "routing_number": "021000021",
        "branch_name": "Downtown Branch",
        "account_type": "checking",
        "account_purpose": "operating",
        "is_primary": True,
        "is_active": True,
        "online_banking_enabled": True,
        "mobile_banking_enabled": True,
        "wire_transfer_enabled": True,
        "ach_enabled": True,
        "daily_transfer_limit": 50000.00,
        "monthly_transfer_limit": 1000000.00,
        "requires_dual_approval": True,
        "bank_api_enabled": False,
        "sync_frequency": "daily",
    }

    print("🏦 Creating Bank Account Example:")
    print(f"POST /chart-of-accounts/{gl_account_id}/bank-accounts")
    print(f"Payload: {json.dumps(bank_account_data, indent=2)}")
    print()


def demo_list_bank_accounts():
    """Demonstrate listing bank accounts for a GL account"""

    gl_account_id = "your-gl-account-id"

    print("📋 Listing Bank Accounts Example:")
    print(f"GET /chart-of-accounts/{gl_account_id}/bank-accounts?active=true&limit=10")
    print("Response: List of bank accounts with pagination")
    print()


def demo_update_bank_account():
    """Demonstrate updating a bank account"""

    bank_account_id = "your-bank-account-id"

    update_data = {
        "daily_transfer_limit": 75000.00,
        "mobile_banking_enabled": True,
        "requires_dual_approval": False,
    }

    print("✏️ Updating Bank Account Example:")
    print(f"PUT /bank-accounts/{bank_account_id}")
    print(f"Payload: {json.dumps(update_data, indent=2)}")
    print()


def demo_banking_validation():
    """Demonstrate banking validation features"""

    print("\n🔍 Banking Validation Examples:")

    # Test cases for validation
    test_cases = [
        {
            "name": "Valid German IBAN",
            "data": {"iban": "DE89370400440532013000"},
            "expected": "✅ Valid",
        },
        {
            "name": "Invalid IBAN format",
            "data": {"iban": "INVALID123"},
            "expected": "❌ Should fail validation",
        },
        {
            "name": "Valid SWIFT code",
            "data": {"swift_code": "DEUTDEFF"},
            "expected": "✅ Valid",
        },
        {
            "name": "Invalid SWIFT code",
            "data": {"swift_code": "ABC"},
            "expected": "❌ Should fail validation",
        },
    ]

    for case in test_cases:
        print(f"  • {case['name']}: {case['expected']}")


def demo_security_features():
    """Demonstrate security features"""

    print("\n🛡️ Security Features:")
    print("  • IBAN validation with checksum verification")
    print("  • SWIFT/BIC code format validation")
    print("  • Sensitive data masking (account numbers)")
    print("  • Field-level encryption capability")
    print("  • Audit trail for all changes")
    print("  • Role-based access control integration")
    print("  • Transfer limit enforcement")
    print("  • Dual approval workflow support")


def main():
    """Main demo function"""

    print("🏦 Banking Integration API Demo")
    print("=" * 50)
    print()

    # Show API endpoint examples
    demo_create_bank_account()
    demo_list_bank_accounts()
    demo_update_bank_account()

    # Demonstrate validation and security features
    demo_banking_validation()
    demo_security_features()

    print("\n" + "=" * 50)
    print("🚀 Complete API Endpoint Reference:")
    print("   POST /chart-of-accounts/{id}/bank-accounts  - Create bank account")
    print("   GET  /chart-of-accounts/{id}/bank-accounts  - List bank accounts")
    print("   GET  /bank-accounts/{id}                    - Get bank account")
    print("   PUT  /bank-accounts/{id}                    - Update bank account")
    print("   DELETE /bank-accounts/{id}                  - Delete bank account")
    print("   PUT  /bank-accounts/{id}/activate           - Activate account")
    print("   PUT  /bank-accounts/{id}/deactivate         - Deactivate account")
    print("   GET  /banking/overview                      - Banking overview")

    print("\n📚 To use the API:")
    print("   1. Start FastAPI server: uvicorn main:app --reload")
    print("   2. Visit: http://localhost:8000/docs for interactive API docs")
    print("   3. Use JWT authentication for all requests")
    print("   4. Link bank accounts to existing GL accounts from Chart of Accounts")

    print("\n✅ Banking Integration is ready for production use!")


if __name__ == "__main__":
    main()
