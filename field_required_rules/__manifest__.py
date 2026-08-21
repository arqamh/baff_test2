# -*- coding: utf-8 -*-
{
    'name': 'Field Required Rules',
    'version': '16.0.1.0.0',
    'category': 'Technical',
    'summary': 'Configurable required-field rules — pick any model, any '
               'field as the trigger, any matching values, and any fields '
               'to require.',
    'description': """
Defines a configuration model `field.required.rule` that lets administrators
mark fields on arbitrary models as required based on the value of any
non-collection field on that model (selection, char, boolean, integer,
float, monetary, or many2one).

Each rule captures:
- Model
- Trigger field on that model (any supported type)
- Per-required-field trigger values (multiple allowed) and override groups

Enforcement is two-layered:
- `get_view()` override injects `required` modifiers into form/tree views so
  the fields render with the required indicator when the state matches.
- `base.create()` and `base.write()` overrides raise a `UserError` when a
  required field is empty for a record currently in a trigger state.

Rules are cached per model via `ormcache` for O(1) lookup.
""",
    'author': 'Centrics Business Solutions',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/field_required_rule_views.xml',
        'views/field_required_rules_menus.xml',
    ],
    'installable': True,
    'application': False,
}
