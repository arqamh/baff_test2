# -*- coding: utf-8 -*-
{
    'name': 'Field Readonly Rules',
    'version': '16.0.1.0.0',
    'category': 'Technical',
    'summary': 'Configurable field lock — pick any model, any field as the '
               'trigger, any matching values, and any fields to freeze.',
    'description': """
Defines a configuration model `field.readonly.rule` that lets administrators
mark fields on arbitrary models as read-only based on the value of any
non-collection field on that model (selection, char, boolean, integer,
float, monetary, or many2one).

Each rule captures:
- Model
- Trigger field on that model (any supported type)
- Per-locked-field trigger values (multiple allowed) and override groups

Enforcement is two-layered and silent (no error messages):
- `get_view()` override injects `readonly` modifiers into form/tree views so
  the fields render disabled when the state matches.
- `base.write()` override silently drops locked keys for records currently
  in a trigger state (safety net for API / RPC writes).

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
        'views/field_readonly_rule_views.xml',
        'views/field_readonly_rules_menus.xml',
    ],
    'installable': True,
    'application': False,
}
