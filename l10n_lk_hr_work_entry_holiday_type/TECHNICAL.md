# TECHNICAL DOCUMENTATION

## Overview
This module extends `hr.work.entry.type` to add a selection field for Sri Lankan holiday classification.  
It is intended to be consumed by payroll rules, overtime logic, and reports.

## Models
- **Inherit**: `hr.work.entry.type`
  - **Fields**
    - `holiday_mapping` (selection, tracking=True)  
      Values: `none`, `public`, `mercantile`, `poya`, `religious`, `company`

> Note: By design, this module **does not** modify payroll calculations directly. Use the
> mapping in custom rules and code.

## Views
- **Form view inheritance**: `hr_work_entry.hr_work_entry_type_view_form` → adds `holiday_mapping` after `name`.

## Coding Conventions
- **One class per file**; the **Python file name equals the class name** (CamelCase).
- Module directory uses snake_case.
- PEP8 guidelines for Python code; functions include meaningful docstrings.

## Dependencies
- `hr_work_entry_holidays_enterprise`

## Example Reference in Code
```python
public_wet = self.env["hr.work.entry.type"].search([("holiday_mapping", "=", "public")], limit=1)
if public_wet:
    # apply special logic for public holiday entries
    pass
```

## Packaging
The module should include:
- `__manifest__.py`, `__init__.py`
- `models/` (each class in its own file, e.g., `hr_work_etnry_type.py`)
- `views/` (e.g., `hr_work_entry_type_views.xml`)
- `README.md`, `TECHNICAL.md`
