# Tax Template Assignment Guide

This guide shows how to assign tax templates to Items and Item Groups so that taxes are automatically applied to transactions.

## Overview

The tax system uses a **3-level inheritance hierarchy**:

```
1. Item Level (highest priority)
   ↓ (if not set)
2. Item Group Level
   ↓ (if not set)
3. Organization Default Level (fallback)
```

## Step 1: Create Tax Templates

First, create your tax templates using the Tax Template API.

### Example: Create GST 18% Template

```http
POST /api/v1/tax-templates
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "template_code": "GST_18",
  "template_name": "GST 18%",
  "description": "Standard GST rate - 9% CGST + 9% SGST",
  "tax_category": "Output",
  "is_default": false,
  "is_active": true,
  "tax_rules": [
    {
      "rule_name": "CGST",
      "tax_type": "CGST",
      "description": "Central GST",
      "tax_rate": 9.0,
      "account_head_id": "{account_head_uuid}",
      "is_compound": false,
      "sequence": 1
    },
    {
      "rule_name": "SGST",
      "tax_type": "SGST",
      "description": "State GST",
      "tax_rate": 9.0,
      "account_head_id": "{account_head_uuid}",
      "is_compound": false,
      "sequence": 2
    }
  ]
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "template_code": "GST_18",
  "template_name": "GST 18%",
  ...
}
```

Save the `id` - you'll need it to assign to items/groups.

### Example: Create GST 5% Template

```http
POST /api/v1/tax-templates

{
  "template_code": "GST_5",
  "template_name": "GST 5%",
  "description": "Reduced GST rate - 2.5% CGST + 2.5% SGST",
  "tax_category": "Output",
  "is_default": false,
  "is_active": true,
  "tax_rules": [
    {
      "rule_name": "CGST",
      "tax_type": "CGST",
      "tax_rate": 2.5,
      "account_head_id": "{account_head_uuid}",
      "is_compound": false,
      "sequence": 1
    },
    {
      "rule_name": "SGST",
      "tax_type": "SGST",
      "tax_rate": 2.5,
      "account_head_id": "{account_head_uuid}",
      "is_compound": false,
      "sequence": 2
    }
  ]
}
```

## Step 2: Assign Tax Templates to Item Groups

Assign tax templates at the item group level for categories of products.

### Example: Assign GST 18% to Electronics Group

```http
PUT /api/v1/item-groups/{item_group_id}
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "sales_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  "purchase_tax_template_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "id": "{item_group_id}",
  "name": "Electronics",
  "code": "ELEC",
  "sales_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  "purchase_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  ...
}
```

Now all items in the "Electronics" group will inherit GST 18% unless overridden at the item level.

## Step 3: Assign Tax Templates to Individual Items

Override the group-level tax template for specific items.

### Example: Create Item with Tax Template

```http
POST /api/v1/items
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "item_code": "LAPTOP-001",
  "item_name": "Dell Laptop",
  "item_group_id": "{electronics_group_id}",
  "item_type": "stock",
  "uom": "Nos",
  "standard_rate": 50000.00,
  "sales_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  "purchase_tax_template_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Example: Update Existing Item with Tax Template

```http
PUT /api/v1/items/{item_id}
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "sales_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  "purchase_tax_template_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Example: Remove Tax Template from Item (Use Group Default)

```http
PUT /api/v1/items/{item_id}
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "sales_tax_template_id": null,
  "purchase_tax_template_id": null
}
```

This will make the item inherit the tax template from its item group.

## Step 4: Set Organization Default Tax Templates

Set fallback tax templates at the organization level (coming soon - requires organization settings API update).

## Tax Template Inheritance Examples

### Example 1: Item-Level Override

```
Organization Default: GST 18%
Item Group (Electronics): GST 18%
Item (Laptop): GST 28%

Result: Laptop uses GST 28% (item level wins)
```

### Example 2: Group-Level Inheritance

```
Organization Default: GST 18%
Item Group (Food): GST 5%
Item (Rice): No tax template set

Result: Rice uses GST 5% (inherits from group)
```

### Example 3: Organization Default Fallback

```
Organization Default: GST 18%
Item Group (Misc): No tax template set
Item (Pen): No tax template set

Result: Pen uses GST 18% (falls back to organization default)
```

## Verification

### Check Item's Tax Template

```http
GET /api/v1/items/{item_id}
```

Response will include:
```json
{
  "id": "{item_id}",
  "item_code": "LAPTOP-001",
  "item_name": "Dell Laptop",
  "sales_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  "purchase_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  ...
}
```

### Check Item Group's Tax Template

```http
GET /api/v1/item-groups/{item_group_id}
```

Response will include:
```json
{
  "id": "{item_group_id}",
  "name": "Electronics",
  "sales_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  "purchase_tax_template_id": "550e8400-e29b-41d4-a716-446655440000",
  ...
}
```

### Get Applicable Tax Template for an Item

```http
GET /api/v1/tax-templates/applicable?item_id={item_id}&transaction_type=Sales
```

Response:
```json
{
  "template": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "template_code": "GST_18",
    "template_name": "GST 18%",
    "tax_rules": [...]
  },
  "source": "item"  // or "item_group" or "organization_default"
}
```

## Common Scenarios

### Scenario 1: Different Tax Rates for Sales vs Purchase

```http
PUT /api/v1/items/{item_id}

{
  "sales_tax_template_id": "{gst_18_template_id}",
  "purchase_tax_template_id": "{input_tax_template_id}"
}
```

### Scenario 2: Tax-Exempt Items

```http
PUT /api/v1/items/{item_id}

{
  "sales_tax_template_id": null,
  "purchase_tax_template_id": null
}
```

Then mark the customer as tax-exempt or handle at transaction level.

### Scenario 3: Bulk Update Item Group

Update all items in a group by updating the group's tax template:

```http
PUT /api/v1/item-groups/{group_id}

{
  "sales_tax_template_id": "{new_tax_template_id}"
}
```

All items without an item-level tax template will now use the new group template.

## Next Steps

Once the transaction integration is complete (tasks 13-15), taxes will be automatically calculated when you:

1. Create a Quotation with line items
2. Create a Sales Order with line items
3. Create an Invoice with line items
4. Create a Purchase Order with line items

The system will:
1. Look up each item's tax template (using the inheritance hierarchy)
2. Calculate taxes based on the template's rules
3. Add tax breakdown to the transaction
4. Calculate grand total = net total + taxes + charges

## API Reference

### Item API
- `POST /api/v1/items` - Create item with tax templates
- `PUT /api/v1/items/{id}` - Update item's tax templates
- `GET /api/v1/items/{id}` - View item's tax templates

### Item Group API
- `POST /api/v1/item-groups` - Create group with tax templates
- `PUT /api/v1/item-groups/{id}` - Update group's tax templates
- `GET /api/v1/item-groups/{id}` - View group's tax templates

### Tax Template API
- `POST /api/v1/tax-templates` - Create tax template
- `GET /api/v1/tax-templates` - List all templates
- `GET /api/v1/tax-templates/{id}` - Get specific template
- `GET /api/v1/tax-templates/applicable` - Get applicable template for item

## Troubleshooting

### Tax template not applying?

1. Check if item has a tax template assigned
2. Check if item's group has a tax template assigned
3. Check if organization has a default tax template
4. Verify the tax template is active (`is_active: true`)
5. Check applicability rules on the template

### Wrong tax template being used?

Remember the hierarchy:
1. Item level (highest priority)
2. Item group level
3. Organization default (lowest priority)

Use the `/api/v1/tax-templates/applicable` endpoint to see which template is being selected and why.
