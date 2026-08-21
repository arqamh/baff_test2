# Technical Reference — centrics_hr_payroll_no_default_rules

## Module Overview

| Field | Value |
|---|---|
| Technical name | `centrics_hr_payroll_no_default_rules` |
| Display name | Payroll - No Default Salary Rules |
| Version | 16.0.1.0.0 |
| Odoo base | 16 |
| License | OPL-1 |
| Type | Global / foundation (reusable) |

### Dependencies

```
hr_payroll      # owns hr.payroll.structure and the rule_ids default
```

No data files, no security, no views — Python-only behavioral override.

---

## Models

### `hr.payroll.structure` — `models/hr_payroll_structure.py`

Inherits `hr.payroll.structure`. Suppresses the generic salary rules Odoo
auto-adds to every new structure.

#### Why

Core `hr.payroll.structure` defines:

```python
rule_ids = fields.One2many(
    'hr.salary.rule', 'struct_id',
    string='Salary Rules', default=_get_default_rule_ids)
```

`_get_default_rule_ids` returns eight `(0, 0, {...})` commands (BASIC, GROSS,
DEDUCTION, ATTACH_SALARY, ASSIG_SALARY, CHILD_SUPPORT, REIMBURSEMENT, NET). Any
new structure that does not pass `rule_ids` explicitly receives all eight.

#### Fix

| Method | Override | Effect |
|---|---|---|
| `default_get(fields_list)` | `defaults.pop('rule_ids', None)` | New structures start with no rules |

`default_get` is the single chokepoint for field defaults: the web client calls
it when opening a new form, and `create` calls it through
`_add_missing_default_values` (`odoo/models.py`) for any field absent from the
supplied values. Stripping `rule_ids` there blocks the generic rules on **both**
UI creation and ORM/XML creation, without redefining the field or touching the
core method that builds the defaults.

> Overriding `_get_default_rule_ids` alone would **not** work: the field stores
> a direct reference to the original function captured at class definition, so a
> subclass override is never consulted. `default_get` is the reliable hook.

#### Scope / safety

- Affects only the *defaults proposed on new records* — existing structures keep
  their current `rule_ids`.
- No effect on payroll computation: payslips compute from a structure's actual
  `rule_ids`, not from the field default.
- Cleaning up structures already polluted by earlier installs is **out of scope**
  for this generic module (a blanket cleanup would also strip the legitimate
  defaults from core/localization structures). Project modules that created the
  affected structures should ship their own targeted data-cleanup migration.

---

## Relationship to project modules

This module was extracted from `baff_hr_payroll_extend` so the behavior can be
reused across payroll implementations. `baff_hr_payroll_extend` now depends on
this module for the prevention behavior and keeps only its own
project-specific data-cleanup migration.
