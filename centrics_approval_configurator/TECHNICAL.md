# TECHNICAL DOCUMENTATION - Approval Configurator

## Overview

This module allows dynamic configuration of approval levels for any Odoo model. Admin users can define how many levels of approval are needed and assign multiple users per level.

## Models

### approval.config

| Field Name         | Type         | Description                                      |
|--------------------|--------------|--------------------------------------------------|
| name               | Char         | Configuration name                               |
| model_id           | Many2one     | Reference to `ir.model`                          |
| approval_level     | Selection    | Number of approval levels (1, 2, or 3)           |
| user_ids_level1    | Many2many    | Users for level 1 approval                       |
| user_ids_level2    | Many2many    | Users for level 2 approval (if applicable)       |
| user_ids_level3    | Many2many    | Users for level 3 approval (if applicable)       |

## Views

- Tree view for listing configurations
- Form view for defining approval logic
- Views are grouped under the `Approval Config` menu

## Security

Basic access rights are provided to base users:
- `base.group_user`: can read/create/update/delete configurations

## Extension Logic

To enforce approval logic in models such as `sale.order`, you can fetch approval configuration like so:

```python
config = self.env['approval.config'].search([('model_id.model', '=', 'sale.order')], limit=1)
if config:
    # implement level-wise approval logic
```

## Future Enhancements

- Add state tracking for approval status in configured models
- Introduce automatic email or chatter notifications for pending approvals
- Enable rule-based level transitions (e.g., amount > X requires level 3)

