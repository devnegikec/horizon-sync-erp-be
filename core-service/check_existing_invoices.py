"""Check existing invoices for payment testing"""
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://horizon_user:horizon_pass@localhost:5432/core_db')
conn = engine.connect()

# Count total invoices
result = conn.execute(text('SELECT COUNT(*) FROM invoices'))
count = result.fetchone()[0]
print(f'Total invoices in database: {count}\n')

if count > 0:
    # Get invoices with outstanding balance
    result = conn.execute(text("""
        SELECT invoice_no, party_type, posting_date, grand_total, outstanding_amount, status 
        FROM invoices 
        WHERE outstanding_amount > 0 
        ORDER BY posting_date DESC 
        LIMIT 10
    """))
    
    invoices = result.fetchall()
    
    if invoices:
        print(f'Invoices with outstanding balance ({len(invoices)}):')
        print('-' * 80)
        for inv in invoices:
            print(f'  {inv[0]} | {inv[1]} | {inv[2]} | Total: ${inv[3]} | Outstanding: ${inv[4]} | {inv[5]}')
        print()
        print('✅ You can use these invoices to test payments!')
        print()
        print('To test:')
        print('  1. Go to Revenue > Payments')
        print('  2. Create a new payment')
        print('  3. Allocate to one of the invoices above')
        print('  4. Confirm the payment')
        print('  5. Go to Books > Journal Entries to see the journal entry')
    else:
        print('❌ No invoices with outstanding balance found.')
        print('   All invoices are fully paid.')
else:
    print('❌ No invoices found in database.')
    print('   You need to create invoices first.')
