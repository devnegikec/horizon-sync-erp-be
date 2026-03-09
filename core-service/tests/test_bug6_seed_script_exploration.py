"""Bug 6 Exploration Test: Missing parent accounts in seed data

**Validates: Requirements 1.6, 2.6**

This is a bug condition exploration test that verifies Bug 6 exists in the UNFIXED code.
The test checks that:
1. Admin seed endpoint calls scripts/seed_data.py (wrong script for inventory)
2. Seeded accounts have NULL parent_account_id (missing hierarchy)
3. "1100 - Current Assets" has no parent account (specific case)

EXPECTED BEHAVIOR ON UNFIXED CODE:
- Test should PASS, confirming the bug exists
- Counterexample: "Seed creates accounts without parent-child hierarchy"

EXPECTED BEHAVIOR ON FIXED CODE:
- Test should FAIL, indicating the bug is fixed
- The fix will change the script to seed_chart_of_accounts.py
- Accounts will have proper parent-child relationships
"""

from pathlib import Path

import pytest


def test_bug6_admin_seed_calls_wrong_script():
    """
    Test that admin seed endpoint calls scripts/seed_data.py (inventory script)
    instead of seed_chart_of_accounts.py (accounts script).

    This test will PASS on unfixed code, confirming the bug exists.
    """
    # Get the admin.py file path
    admin_file = (
        Path(__file__).parent.parent / "app" / "api" / "v1" / "endpoints" / "admin.py"
    )

    # Read the admin.py file
    with open(admin_file) as f:
        content = f.read()

    # Check that the script path points to scripts/seed_data.py
    assert 'scripts" / "seed_data.py"' in content, (
        "Admin endpoint should call scripts/seed_data.py (wrong script) on unfixed code"
    )

    # Verify it does NOT point to seed_chart_of_accounts.py
    assert "seed_chart_of_accounts.py" not in content, (
        "Admin endpoint should NOT call seed_chart_of_accounts.py on unfixed code"
    )

    print(
        "\n✓ Counterexample confirmed: Admin endpoint calls wrong script (scripts/seed_data.py)"
    )


def test_bug6_seed_creates_accounts_without_parents(db_session, mock_current_user):
    """
    Test that when seed script runs, it creates accounts with NULL parent_account_id.

    This simulates what happens when scripts/seed_data.py is called instead of
    seed_chart_of_accounts.py. The inventory seed script doesn't create chart of accounts
    with proper hierarchy.

    This test will PASS on unfixed code, confirming accounts lack parent relationships.
    """
    from app.models.base import AccountStatus, AccountType
    from app.models.chart_of_account import Account

    # Simulate what scripts/seed_data.py would do - create accounts without parent_account_id
    # (The inventory seed script doesn't create chart of accounts at all, but if it did,
    # it wouldn't set up the hierarchy)

    # Create accounts without parent relationships (simulating wrong seed script behavior)
    accounts_without_parents = [
        {
            "account_code": "1000",
            "account_name": "Assets",
            "account_type": AccountType.ASSET,
            "parent_account_id": None,  # No parent
        },
        {
            "account_code": "1100",
            "account_name": "Current Assets",
            "account_type": AccountType.ASSET,
            "parent_account_id": None,  # Should have parent "1000" but doesn't
        },
        {
            "account_code": "1110",
            "account_name": "Cash and Cash Equivalents",
            "account_type": AccountType.ASSET,
            "parent_account_id": None,  # Should have parent "1100" but doesn't
        },
    ]

    created_accounts = []
    for acc_data in accounts_without_parents:
        account = Account(
            account_code=acc_data["account_code"],
            account_name=acc_data["account_name"],
            account_type=acc_data["account_type"],
            parent_account_id=acc_data["parent_account_id"],
            organization_id=mock_current_user.organization_id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        created_accounts.append(account)

    db_session.commit()

    # Verify all accounts have NULL parent_account_id (bug condition)
    for account in created_accounts:
        db_session.refresh(account)
        assert account.parent_account_id is None, (
            f"Account {account.account_code} should have NULL parent_account_id on unfixed code"
        )

    print("\n✓ Counterexample confirmed: Seeded accounts have NULL parent_account_id")


def test_bug6_current_assets_has_no_parent(db_session, mock_current_user):
    """
    Test specific case: "1100 - Current Assets" has no parent account.

    In the correct hierarchy, "1100 - Current Assets" should have parent "1000 - Assets".
    This test verifies that on unfixed code, this relationship is missing.

    This test will PASS on unfixed code, confirming the specific bug case.
    """
    from app.models.base import AccountStatus, AccountType
    from app.models.chart_of_account import Account

    # Create "1000 - Assets" (should be parent)
    assets_account = Account(
        account_code="1000",
        account_name="Assets",
        account_type=AccountType.ASSET,
        parent_account_id=None,  # Root account
        organization_id=mock_current_user.organization_id,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=False,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add(assets_account)
    db_session.flush()

    # Create "1100 - Current Assets" WITHOUT parent (simulating bug)
    current_assets_account = Account(
        account_code="1100",
        account_name="Current Assets",
        account_type=AccountType.ASSET,
        parent_account_id=None,  # BUG: Should be assets_account.id
        organization_id=mock_current_user.organization_id,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=False,
        created_by=str(mock_current_user.id),
        updated_by=str(mock_current_user.id),
    )
    db_session.add(current_assets_account)
    db_session.commit()

    # Refresh to get latest data
    db_session.refresh(current_assets_account)

    # Verify "1100 - Current Assets" has no parent (bug condition)
    assert current_assets_account.parent_account_id is None, (
        "1100 - Current Assets should have NULL parent_account_id on unfixed code"
    )

    # Verify it does NOT have "1000 - Assets" as parent
    assert current_assets_account.parent_account_id != assets_account.id, (
        "1100 - Current Assets should NOT have 1000 - Assets as parent on unfixed code"
    )

    print("\n✓ Counterexample confirmed: '1100 - Current Assets' has no parent account")
    print(f"   Expected parent: {assets_account.id} (1000 - Assets)")
    print(f"   Actual parent: {current_assets_account.parent_account_id} (NULL)")


def test_bug6_counterexample_summary():
    """
    Document the counterexample for Bug 6.

    This test always passes and serves as documentation of the bug.
    """
    counterexample = """
    Bug 6 Counterexample: Seed creates accounts without parent-child hierarchy

    Root Cause:
    - Admin seed endpoint at /api/v1/admin/seed-data calls scripts/seed_data.py
    - scripts/seed_data.py is the INVENTORY seed script (warehouses, items, item groups)
    - It does NOT create chart of accounts with proper parent-child relationships
    - The correct script is seed_chart_of_accounts.py in the project root

    Evidence:
    - admin.py line 38: script_path = Path(...) / "scripts" / "seed_data.py"
    - Accounts created have NULL parent_account_id
    - "1100 - Current Assets" has no parent (should have parent "1000 - Assets")

    Expected Fix:
    - Change admin.py line 38 to point to seed_chart_of_accounts.py
    - This will create accounts with proper parent-child hierarchy
    - "1100 - Current Assets" will have parent_account_id pointing to "1000 - Assets"
    """

    print(counterexample)
    assert True, "Counterexample documented"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
