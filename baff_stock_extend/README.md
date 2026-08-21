# Baff Stock Extend

**Version:** 16.0.1.0.0
**Author:** Centrics Business Solutions PVT Ltd
**License:** LGPL-3

## Overview

Extends the `product.category` model to include a chatter, activity scheduling, and field change tracking for key inventory and accounting configuration fields.

## Features

- **Chatter** on Product Category form view — log notes, send messages, follow records.
- **Activity scheduling** — assign to-do activities directly on a product category.
- **Field change tracking** — the following fields are automatically logged in the chatter whenever their value changes:

| Field | Label |
|---|---|
| `property_cost_method` | Costing Method |
| `property_valuation` | Inventory Valuation |
| `property_stock_valuation_account_id` | Stock Valuation Account |
| `property_stock_journal` | Stock Journal |
| `property_stock_account_input_categ_id` | Stock Input Account |
| `property_stock_account_output_categ_id` | Stock Output Account |
| `property_account_income_categ_id` | Income Account |
| `property_account_expense_categ_id` | Expense Account |
| `route_ids` | Routes |

> **Note:** The account and journal fields are `company_dependent` (stored as `ir.property`). Odoo's built-in `tracking=True` does not support these fields, so changes are tracked via a custom `write()` override that posts an internal log note with old → new values.

## Dependencies

- `stock_account`
- `account`

## Installation

1. Copy the module to your custom addons path.
2. Update the apps list.
3. Install **Baff Stock Extend**.

## Technical Notes

- Adds `mail.thread` and `mail.activity.mixin` to `product.category` via `_inherit`.
- `_name = 'product.category'` is explicitly set to ensure Odoo's metaclass resolves the multi-model `_inherit` list correctly (avoids M2M field conflict on `route_ids`).
- Route changes are shown as **Added: X** / **Removed: Y** in the log note.
