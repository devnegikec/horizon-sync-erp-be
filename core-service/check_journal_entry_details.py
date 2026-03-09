"""
Check journal entry details to verify all fields are populated correctly.
"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"


def check_journal_entries():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("=" * 80)
        print("CHECKING JOURNAL ENTRY DETAILS")
        print("=" * 80)
        print()

        # Get all journal entries with their lines
        result = conn.execute(
            text("""
            SELECT 
                je.id,
                je.entry_no,
                je.posting_date,
                je.voucher_type,
                je.status,
                je.total_debit,
                je.total_credit,
                je.remarks as je_remarks,
                jel.id as line_id,
                jel.debit,
                jel.credit,
                jel.remarks as line_remarks,
                a.account_code,
                a.account_name
            FROM journal_entries je
            LEFT JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id
            LEFT JOIN accounts a ON jel.account_id = a.id
            ORDER BY je.created_at DESC, jel.sort_order
            LIMIT 20
        """)
        )

        entries = {}
        for row in result.fetchall():
            entry_id = str(row[0])
            if entry_id not in entries:
                entries[entry_id] = {
                    "entry_no": row[1],
                    "posting_date": row[2],
                    "voucher_type": row[3],
                    "status": row[4],
                    "total_debit": row[5],
                    "total_credit": row[6],
                    "remarks": row[7],
                    "lines": [],
                }

            if row[8]:  # line_id exists
                entries[entry_id]["lines"].append(
                    {
                        "debit": row[9],
                        "credit": row[10],
                        "remarks": row[11],
                        "account_code": row[12],
                        "account_name": row[13],
                    }
                )

        if not entries:
            print("❌ No journal entries found!")
            return

        for entry_id, entry in entries.items():
            print(f"Journal Entry: {entry['entry_no'] or '❌ MISSING'}")
            print(f"  Posting Date: {entry['posting_date']}")
            print(f"  Voucher Type: {entry['voucher_type'] or '❌ MISSING'}")
            print(f"  Status: {entry['status']}")
            print(f"  Remarks: {entry['remarks'] or '❌ MISSING'}")
            print(f"  Total Debit: {entry['total_debit']}")
            print(f"  Total Credit: {entry['total_credit']}")
            print(f"  Lines: {len(entry['lines'])}")

            for i, line in enumerate(entry["lines"], 1):
                print(f"    Line {i}:")
                print(
                    f"      Account: {line['account_code'] or '❌ MISSING'} - {line['account_name'] or '❌ MISSING'}"
                )
                print(f"      Debit: {line['debit']}")
                print(f"      Credit: {line['credit']}")
                print(f"      Remarks: {line['remarks'] or '❌ MISSING'}")

            print()

        print("=" * 80)
        print("✅ CHECK COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    try:
        check_journal_entries()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
