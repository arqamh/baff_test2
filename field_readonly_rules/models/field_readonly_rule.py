from odoo import api, fields, models, tools


class FieldReadonlyRule(models.Model):
    _name = 'field.readonly.rule'
    _description = 'Field Readonly Rule'
    _inherit = ['mail.thread']
    _order = 'model_id, name'

    name = fields.Char(
        required=True, tracking=True,
        help='Short description of the rule.')
    active = fields.Boolean(default=True, tracking=True)

    model_id = fields.Many2one(
        'ir.model', string='Model', required=True, ondelete='cascade',
        tracking=True)
    model_name = fields.Char(
        string='Technical Model', related='model_id.model',
        store=True, index=True)

    line_ids = fields.One2many(
        'field.readonly.rule.line', 'rule_id',
        string='Field Lines', copy=True,
        help='One line per locked field, with its own trigger field, '
             'trigger values, and override groups.')

    # ---- Onchange ----

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.line_ids = [(5, 0, 0)]

    # ---- Constraints ----

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Rule name must be unique.'),
    ]

    # ---- CRUD ----

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._invalidate_rules_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._invalidate_rules_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self._invalidate_rules_cache()
        return res

    # ---- Helpers (cache) ----

    def _invalidate_rules_cache(self):
        self.env.registry.clear_caches()

    @api.model
    @tools.ormcache('model_name')
    def _get_cached_rules_for_model(self, model_name):
        """Return a tuple of rule entry dicts — one per line — for the given
        model, cached per registry."""
        model = self.env.get(model_name)
        if model is None:
            return ()
        rules = self.sudo().search([
            ('active', '=', True),
            ('model_name', '=', model_name),
        ])
        entries = []
        for r in rules:
            for line in r.line_ids:
                if not line.field_ids or not line.trigger_field_id:
                    continue
                tfname = line.trigger_field_id.name
                if not tfname or tfname not in model._fields:
                    continue
                values = frozenset(line.trigger_selection_ids.mapped('value'))
                if not values:
                    continue
                override_group_ids = frozenset(line.override_group_ids.ids)
                for locked_field in line.field_ids:
                    if locked_field.name not in model._fields:
                        continue
                    entries.append({
                        'trigger_field': tfname,
                        'trigger_field_type': 'selection',
                        'trigger_values': values,
                        'field_name': locked_field.name,
                        'override_group_ids': override_group_ids,
                        'rule_name': r.name,
                    })
        return tuple(entries)