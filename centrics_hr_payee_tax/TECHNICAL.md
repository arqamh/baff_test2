# TECHNICAL.md — Centrics PAYEE Tax (Odoo 16)

## Model: `hr.payee.tax`
| Field | Type | Notes |
|------|------|------|
| `sequence` | Integer | Ordering |
| `condition_type` | Selection | **below / between / above** |
| `amount_from` | Float | Lower bound (incl.) |
| `amount_to` | Float | Upper bound (incl.) |
| `percentage` | Float | Rate (%) |
| `note` | Char | Free text |

**Helpers**
- `_get_rate_for_amount(amount) -> float` — returns the matching percentage
- `_matches(amount) -> bool` — checks if amount falls within this bracket

**Validation**
- Consistency per condition (required fields, `from <= to`, etc.)
- Cross-record **overlap prevention** (global table)

## Views
- **Tree only** for `hr.payee.tax`: sequence, condition, from, to, rate, note
- Settings extension adds `payee_tax_enabled` toggle under Payroll Settings

## Menus
- **Payroll → Configuration → PAYEE Tax Brackets**

## Settings
`res.config.settings.payee_tax_enabled` (config parameter: `centrics_hr_payee_tax.payee_tax_enabled`)

## Salary Rule Snippet
```python
amount = 0.0
if env["ir.config_parameter"].sudo().get_param("centrics_hr_payee_tax.payee_tax_enabled"):
    taxable = categories.GROSS
    rate = env["hr.payee.tax"]._get_rate_for_amount(taxable)
    amount = taxable * (rate / 100.0)
result = amount
```
