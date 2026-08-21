from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Field labels used by the line audit messages: technical name → display label.
_TRACKED_LINE_FIELDS = {
    'field_ids': 'Fields to Lock',
    'trigger_field_id': 'Trigger Field',
    'trigger_selection_ids': 'Trigger Values',
    'override_group_ids': 'Override Groups',
}


class FieldReadonlyRuleLine(models.Model):
    _name = 'field.readonly.rule.line'
    _description = 'Field Readonly Rule Line'

    rule_id = fields.Many2one(
        'field.readonly.rule', string='Rule', required=True,
        ondelete='cascade', index=True)

    model_id = fields.Many2one(related='rule_id.model_id')

    field_ids = fields.Many2many(
        'ir.model.fields',
        'field_readonly_rule_line_field_rel',
        'line_id', 'field_id',
        string='Fields to Lock', required=True,
        domain="[('model_id', '=', model_id), ('store', '=', True), "
               "('readonly', '=', False), ('compute', '=', False)]",
        help='Fields that become read-only when the trigger condition is met.')

    trigger_field_id = fields.Many2one(
        'ir.model.fields', string='Trigger Field', required=True,
        ondelete='cascade',
        domain="[('model_id', '=', model_id), ('ttype', '=', 'selection')]",
        help='Selection field on the same model whose value triggers the lock.')
    trigger_field_name = fields.Char(
        related='trigger_field_id.name', store=True)

    trigger_field_origin_id = fields.Many2one(
        'ir.model.fields',
        compute='_compute_trigger_field_origin',
        help='Resolved source field for selection lookup (follows related chain).')

    trigger_selection_ids = fields.Many2many(
        'ir.model.fields.selection',
        'field_readonly_rule_line_selection_rel',
        'line_id', 'selection_id',
        string='Trigger Values', required=True,
        help='Select one or more values that will trigger the field lock.')

    override_group_ids = fields.Many2many(
        'res.groups',
        'field_readonly_rule_line_group_rel', 'line_id', 'group_id',
        string='Override Groups',
        help='Users belonging to any of these groups keep edit access to '
             'this field even when the trigger condition is met.')

    # ---- Compute ----

    @api.depends('trigger_field_id', 'trigger_field_id.related', 'model_id')
    def _compute_trigger_field_origin(self):
        IrField = self.env['ir.model.fields']
        for line in self:
            tf = line.trigger_field_id
            if not tf:
                line.trigger_field_origin_id = False
                continue
            if not tf.related:
                line.trigger_field_origin_id = tf
                continue
            # Walk the related path (e.g. 'order_id.state') to find the
            # field that actually owns the selection options.
            parts = tf.related.split('.')
            model_name = line.model_id.model if line.model_id else tf.model
            origin = tf
            for i, part in enumerate(parts):
                field_rec = IrField.search(
                    [('model', '=', model_name), ('name', '=', part)], limit=1)
                if not field_rec:
                    break
                if i == len(parts) - 1:
                    origin = field_rec
                    break
                model_name = field_rec.relation or ''
                if not model_name:
                    break
            line.trigger_field_origin_id = origin

    # ---- Onchange ----

    @api.onchange('trigger_field_id')
    def _onchange_trigger_field_id(self):
        self.trigger_selection_ids = [(5, 0, 0)]
        # Explicitly recompute so the client receives the updated origin field
        # in the onchange response — needed for the trigger_selection_ids domain.
        self._compute_trigger_field_origin()

    # ---- Constraints ----

    @api.constrains('field_ids', 'trigger_selection_ids', 'rule_id', 'trigger_field_id')
    def _check_trigger_values(self):
        for line in self:
            if not line.trigger_field_id:
                raise ValidationError(_('Trigger Field is required.'))
            if line.trigger_field_id.model_id != line.rule_id.model_id:
                raise ValidationError(_(
                    "Trigger Field '%s' does not belong to the rule's model.",
                    line.trigger_field_id.name))
            model = line.env.get(line.rule_id.model_id.model)
            if model is None:
                raise ValidationError(_(
                    "Model '%s' is not loaded in the registry.",
                    line.rule_id.model_id.model))
            if not model._fields.get(line.trigger_field_id.name):
                raise ValidationError(_(
                    "Field '%s' not found on model '%s'.",
                    line.trigger_field_id.name, line.rule_id.model_id.model))
            if not line.field_ids:
                raise ValidationError(_('At least one Field to Lock is required.'))
            if not line.trigger_selection_ids:
                raise ValidationError(_('Trigger Values cannot be empty.'))

    # ---- CRUD (line audit posts to the parent rule's chatter) ----

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        self.env.registry.clear_caches()
        for line in lines:
            if not line.rule_id:
                continue
            details = ' / '.join(
                '%s: <b>%s</b>' % (label, line._format_line_value(fname))
                for fname, label in _TRACKED_LINE_FIELDS.items()
            )
            line.rule_id.message_post(
                body=_("Added field lock — %s", details))
        return lines

    def write(self, vals):
        watched = set(vals.keys()) & set(_TRACKED_LINE_FIELDS)
        if not watched:
            return super().write(vals)
        before = {
            line.id: {f: line._format_line_value(f) for f in watched}
            for line in self
        }
        res = super().write(vals)
        self.env.registry.clear_caches()
        for line in self:
            if not line.rule_id:
                continue
            changes = []
            for f in watched:
                old = before[line.id][f]
                new = line._format_line_value(f)
                if old != new:
                    changes.append('%s: <i>%s</i> → <b>%s</b>' % (
                        _TRACKED_LINE_FIELDS[f], old or '∅', new or '∅'))
            if changes:
                line.rule_id.message_post(
                    body=_("Updated field lock — %s", ' / '.join(changes)))
        return res

    def unlink(self):
        rule_messages = []
        for line in self:
            if not line.rule_id:
                continue
            rule_messages.append((
                line.rule_id,
                _("Removed field lock — Fields: <b>%(fields)s</b> / "
                  "Trigger: <b>%(trigger)s</b> = <b>%(values)s</b>",
                  fields=', '.join(
                      f.field_description or f.name
                      for f in line.field_ids) or '?',
                  trigger=line.trigger_field_id.field_description
                          or line.trigger_field_id.name or '?',
                  values=', '.join(line.trigger_selection_ids.mapped('name')) or '')))
        res = super().unlink()
        self.env.registry.clear_caches()
        for rule, body in rule_messages:
            rule.message_post(body=body)
        return res

    # ---- Helpers ----

    def _format_line_value(self, fname):
        self.ensure_one()
        if fname == 'field_ids':
            return ', '.join(
                f.field_description or f.name for f in self.field_ids) or '∅'
        if fname == 'trigger_field_id':
            rec = self[fname]
            return rec.field_description or rec.name or ''
        if fname == 'trigger_selection_ids':
            return ', '.join(self.trigger_selection_ids.mapped('name')) or '∅'
        if fname == 'override_group_ids':
            return ', '.join(self.override_group_ids.mapped('full_name')) or '∅'
        return self[fname] or ''