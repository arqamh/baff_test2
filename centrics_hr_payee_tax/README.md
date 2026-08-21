# Centrics – PAYEE Tax for Payroll (Odoo 16)

Configure PAYEE tax brackets (**below / between / above**) and use them in Odoo Payroll calculations.

## ✅ What's new
- Removed company/currency/active fields — table is **global**.
- `amount_from` / `amount_to` are **Float** (not Monetary).

## 🔧 How it works
Each record represents a single bracket. For a given taxable amount, the module finds
the first matching bracket by sequence and bounds and returns its rate.

## 📍 Navigation
- **Payroll → Configuration → PAYEE Tax Brackets** (tree-only)
- Toggle under **Payroll → Configuration → Settings → PAYEE Tax**

## 🧮 Using in a Salary Rule
Example (Amount Python Code):

```python
amount = 0.0
if env["ir.config_parameter"].sudo().get_param("centrics_hr_payee_tax.payee_tax_enabled"):
    taxable = categories.GROSS  # adjust to your base
    rate = env["hr.payee.tax"]._get_rate_for_amount(taxable)
    amount = taxable * (rate / 100.0)
result = amount
```

## 🧪 Example Monthly Brackets (LK 2025/26)
- Below 150,000 → 0%
- Between 150,000.01 – 233,333.33 → 6%
- Between 233,333.34 – 275,000.00 → 18%
- Between 275,000.01 – 316,666.67 → 24%
- Between 316,666.68 – 358,333.33 → 30%
- Above 358,333.33 → 36%

## 🛡️ Access Rights
- Payroll Manager: full access
- HR Officer: read-only
