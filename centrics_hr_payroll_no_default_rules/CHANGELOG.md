# Changelog — centrics_hr_payroll_no_default_rules

All notable changes to this module are recorded here.
Format: `[version] YYYY-MM-DD — description`

---

## [18.0.1.0.0] — 2026-06-22

### Added
- Initial release. Extracted from `baff_hr_payroll_extend` into a dedicated,
  reusable foundation module.
- **`hr.payroll.structure`** (`models/hr_payroll_structure.py`):
  - Inherits `hr.payroll.structure` and overrides `default_get` to drop the
    `rule_ids` default (`_get_default_rule_ids`), so new structures are created
    with no auto-added generic salary rules (BASIC, GROSS, DEDUCTION,
    ATTACH_SALARY, ASSIG_SALARY, CHILD_SUPPORT, REIMBURSEMENT, NET).
  - Applies to UI and ORM/XML creation; no Odoo core file modified.
