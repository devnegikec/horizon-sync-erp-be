Great question! Let me explain how the tax system works and how to connect it to your transactions. I'll reference the design document and show you the complete flow.

## How Tax Templates Connect to Transactions

### Tax Inheritance Hierarchy (3 Levels)

The system uses a **3-level inheritance hierarchy** to determine which tax template applies:

```
1. Item Level (highest priority)
   ↓ (if not set)
2. Item Group Level
   ↓ (if not set)
3. Organization Default Level (fallback)
```

### Step-by-Step Setup Process

#### 1. **Assign Tax Templates to Items or Item Groups**

First, you need to link tax templates to your items or item groups. The database migration already added these columns:

**For Items:**
```sql
-- Items table now has:
sales_tax_template_id   -- Tax template for sales transactions
purchase_tax_template_id -- Tax template for purchase transactions
```

**For Item Groups:**
```sql
-- Item Groups table now has:
sales_tax_template_id
purchase_tax_template_id
```

**For Organization (fallback):**
```sql
-- Organization Settings table now has:
default_sales_tax_template_id
default_purchase_tax_template_id
```

#### 2. **How to Assign Tax Templates**

You can assign tax templates through your existing Item and Item Group APIs:

**Update an Item with Tax Template:**
```http
PUT /api/v1/items/{item_id}
{
  "sales_tax_template_id": "uuid-of-gst-18-template",
  "purchase_tax_template_id": "uuid-of-input-tax-template"
}
```

**Update an Item Group with Tax Template:**
```http
PUT /api/v1/item-groups/{group_id}
{
  "sales_tax_template_id": "uuid-of-gst-18-template",
  "purchase_tax_template_id": "uuid-of-input-tax-template"
}
```

#### 3. **Automatic Tax Calculation in Transactions**

According to the spec (tasks 13, 14, 15), the integration needs to be implemented in the transaction services. Here's how it will work once implemented:

**When creating a Quotation/Sales Order/Invoice:**

1. User adds line items with `item_id` and `qty`
2. System looks up each item's tax template using the hierarchy:
   - Check if item has `sales_tax_template_id` → use it
   - If not, check if item's group has `sales_tax_template_id` → use it
   - If not, use organization's `default_sales_tax_template_id`
3. System calculates taxes for each line item based on the template
4. System calculates total: `grand_total = net_total + total_tax + total_charges`

### Current Implementation Status

Looking at the tasks file, here's what's done and what's pending:

✅ **Completed:**
- Database models and migrations (tasks 1.x)
- Repository layer (tasks 2.1, 2.3)
- Tax calculation engine (task 3.1)
- Charge calculation engine (task 4.1)
- Template services (tasks 5.1, 5.5)
- Transaction integration service (task 7.1)
- Tax template API endpoints (task 9.1 - we just created this)
- Schemas (task 8.1)

⏳ **Pending (Not Yet Integrated):**
- Task 13: Integrate taxes into **Quotation** workflow
- Task 14: Integrate taxes into **Sales Order** workflow
- Task 15: Integrate taxes into **Invoice** workflow
- Tasks 8.2, 8.3: Charge template and calculation schemas
- Tasks 9.2, 10.x, 11.x: More API endpoints and tests

### How It Will Work (Example Flow)

Here's a complete example of how it will work once tasks 13-15 are implemented:

**1. Setup Phase:**
```http
# Create a GST 18% tax template
POST /api/v1/tax-templates
{
  "template_code": "GST_18",
  "template_name": "GST 18%",
  "tax_category": "Output",
  "tax_rules": [
    {"rule_name": "CGST", "tax_rate": 9, ...},
    {"rule_name": "SGST", "tax_rate": 9, ...}
  ]
}

# Assign it to an item
PUT /api/v1/items/{item_id}
{
  "sales_tax_template_id": "{gst_18_template_id}"
}
```

**2. Transaction Phase (once integrated):**
```http
# Create a quotation
POST /api/v1/quotations
{
  "customer_id": "...",
  "line_items": [
    {
      "item_id": "{item_id}",  # This item has GST 18% assigned
      "qty": 10,
      "rate": 100
    }
  ]
}

# Response will include:
{
  "id": "...",
  "line_items": [...],
  "net_total": 1000.00,
  "tax_breakdown": [
    {"tax_type": "CGST", "tax_rate": 9, "tax_amount": 90.00},
    {"tax_type": "SGST", "tax_rate": 9, "tax_amount": 90.00}
  ],
  "total_tax": 180.00,
  "total_charges": 0.00,
  "grand_total": 1180.00
}
```

### What You Need to Do Next

To complete the integration, you need to implement tasks 13-15. Would you like me to:

1. **Implement the quotation integration** (task 13) so taxes are automatically calculated when you create/update quotations?
2. **Show you how to manually assign tax templates to items** using the existing APIs?
3. **Create a complete end-to-end example** with sample data?

The tax calculation engine and services are already built - they just need to be hooked into the quotation/sales order/invoice creation workflows. Let me know which part you'd like me to help with!