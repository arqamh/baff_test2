# centrics_hr_payroll_no_default_rules — No Default Salary Rules

Global, reusable foundation module that stops Odoo from automatically adding
the eight generic salary rules to **new** Salary Structures.

## The problem

Core `hr.payroll.structure` defines the `rule_ids` field with a default:

```python
rule_ids = fields.One2many(
    'hr.salary.rule', 'struct_id',
    string='Salary Rules', default=_get_default_rule_ids)
```

`_get_default_rule_ids` returns eight generic rules — **Basic, Gross, Deduction,
Attachment of Salary, Assignment of Salary, Child Support, Reimbursement, Net**.
Any structure created without an explicit `rule_ids` value receives all eight.

When an implementation defines its own complete rule set — typically through XML
data files — each structure ends up with the generic rules **plus** the intended
ones, i.e. duplicate / unwanted rules.

## What this module does

Overrides `default_get` on `hr.payroll.structure` to strip the `rule_ids`
default. A new structure therefore starts **empty**; only the rules added
explicitly (in the UI or via XML data files) are linked to it.

- Works for both UI creation and ORM/XML creation.
- Does not modify any Odoo core file.
- Does not touch existing structures or payroll computation — it only affects
  the defaults proposed on a newly created structure.

## When to use it

Add it to the dependency list of any payroll implementation that ships its own
salary structure + rules and must not inherit the generic defaults. Because the
behavior is generic and reusable, it is intended to be shared across projects
rather than embedded in a single client module.

```python
'depends': ['centrics_hr_payroll_no_default_rules', ...],
```

## Dependencies

Requires `hr_payroll` only.

## Documentation

- `TECHNICAL.md` — implementation detail and rationale.
- `CHANGELOG.md` — version history.
