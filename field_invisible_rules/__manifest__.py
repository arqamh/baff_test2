# -*- coding: utf-8 -*-
{
    'name': 'Field Invisible Rules',
    'version': '16.0.1.0.0',
    'category': 'Technical',
    'summary': 'Configurable field hiding — pick any model, any field as '
               'the trigger, any matching values, and any fields to hide.',
    'description': """
Defines a configuration model `field.invisible.rule` that lets administrators
hide fields on arbitrary models based on the value of any non-collection
field on that model (selection, char, boolean, integer, float, monetary,
or many2one).

Each rule captures:
- Model
- Trigger field on that model (any supported type)
- Per-hidden-field trigger values (multiple allowed) and override groups

Enforcement is two-layered and silent:
- `get_view()` override injects `invisible` (form) or `column_invisible`
  (tree) modifiers so the fields disappear when the state matches.
- `base.write()` override silently drops hidden-field keys for records
  currently in a trigger state (safety net for API / RPC writes).

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
        'views/field_invisible_rule_views.xml',
        'views/field_invisible_rules_menus.xml',
    ],
    'installable': True,
    'application': False,
}
