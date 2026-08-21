from odoo import api, fields, models, tools


class FieldInvisibleRule(models.Model):
    _name = 'field.invisible.rule'
    _description = 'Field Invisible Rule'
    _inherit = ['mail.thread']
    _order = 'model_id, name'

    _SUPPORTED_TRIGGER_TYPES = (
        'selection', 'char', 'text', 'html', 'boolean',
        'integer', 'float', 'monetary', 'many2one',
    )

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
        'field.invisible.rule.line', 'rule_id',
        string='Field Lines', copy=True,
        help='One line per hidden field, with its own trigger field, '
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

    # ---- Helpers (cache + value parsing) ----

    def _invalidate_rules_cache(self):
        self.env.registry.clear_caches()

    @staticmethod
    def _parse_trigger_values(field, raw):
        parts = [s.strip() for s in (raw or '').split(',') if s.strip()]
        if not parts:
            return frozenset()
        ftype = field.type
        try:
            if ftype == 'boolean':
                return frozenset(
                    p.strip().lower() in ('1', 'true', 'yes', 't', 'y')
                    for p in parts)
            if ftype == 'integer':
                return frozenset(int(p) for p in parts)
            if ftype in ('float', 'monetary'):
                return frozenset(float(p) for p in parts)
            if ftype == 'many2one':
                return frozenset(int(p) for p in parts)
        except (ValueError, TypeError):
            return frozenset()
        return frozenset(parts)

    @api.model
    @tools.ormcache('model_name')
    def _get_cached_rules_for_model(self, model_name):
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
                if not line.field_id or not line.trigger_field_id:
                    continue
                tfname = line.trigger_field_id.name
                if not tfname or tfname not in model._fields:
                    continue
                tfield = model._fields[tfname]
                values = self._parse_trigger_values(
                    tfield, line.trigger_values or '')
                if not values:
                    continue
                entries.append({
                    'trigger_field': tfname,
                    'trigger_field_type': tfield.type,
                    'trigger_values': values,
                    'field_name': line.field_id.name,
                    'override_group_ids': frozenset(line.override_group_ids.ids),
                    'rule_name': r.name,
                })
        return tuple(entries)
