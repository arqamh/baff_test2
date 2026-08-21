from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_TRACKED_LINE_FIELDS = {
    'field_id': 'Field',
    'trigger_field_id': 'Trigger Field',
    'trigger_values': 'Trigger Values',
    'override_group_ids': 'Override Groups',
}


class FieldRequiredRuleLine(models.Model):
    _name = 'field.required.rule.line'
    _description = 'Field Required Rule Line'

    rule_id = fields.Many2one(
        'field.required.rule', string='Rule', required=True,
        ondelete='cascade', index=True)

    model_id = fields.Many2one(related='rule_id.model_id')

    field_id = fields.Many2one(
        'ir.model.fields', string='Required Field', required=True,
        ondelete='cascade',
        domain="[('model_id', '=', model_id), ('store', '=', True), "
               "('compute', '=', False)]",
        help='Field that becomes required when the trigger condition is met.')

    trigger_field_id = fields.Many2one(
        'ir.model.fields', string='Trigger Field', required=True,
        ondelete='cascade',
        domain="[('model_id', '=', model_id), "
               "('ttype', 'in', ['selection', 'char', 'text', 'html', "
               "'boolean', 'integer', 'float', 'monetary', 'many2one'])]",
        help='Field on the same model whose value triggers the requirement.')
    trigger_field_name = fields.Char(
        related='trigger_field_id.name', store=True)
    trigger_field_ttype = fields.Selection(
        related='trigger_field_id.ttype', store=True)

    trigger_values = fields.Char(
        string='Trigger Values', required=True,
        help='Comma-separated values that mark the field required.')

    override_group_ids = fields.Many2many(
        'res.groups',
        'field_required_rule_line_group_rel', 'line_id', 'group_id',
        string='Override Groups',
        help='Users belonging to any of these groups bypass this requirement.')

    # ---- Onchange ----

    @api.onchange('trigger_field_id')
    def _onchange_trigger_field_id(self):
        self.trigger_values = False

    # ---- Constraints ----

    @api.constrains('trigger_values', 'rule_id', 'field_id', 'trigger_field_id')
    def _check_trigger_values(self):
        Rule = self.env['field.required.rule']
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
            field = model._fields.get(line.trigger_field_id.name)
            if not field:
                raise ValidationError(_(
                    "Field '%s' not found on model '%s'.",
                    line.trigger_field_id.name, line.rule_id.model_id.model))
            if field.type not in Rule._SUPPORTED_TRIGGER_TYPES:
                raise ValidationError(_(
                    "Field '%(field)s' on '%(model)s' is of type "
                    "'%(ftype)s' which is not supported as a trigger.",
                    field=line.trigger_field_id.name,
                    model=line.rule_id.model_id.model,
                    ftype=field.type))

            raw = line.trigger_values or ''
            parts = [s.strip() for s in raw.split(',') if s.strip()]
            if not parts:
                raise ValidationError(_('Trigger Values cannot be empty.'))

            parsed = Rule._parse_trigger_values(field, raw)
            if not parsed:
                raise ValidationError(_(
                    "Trigger Values '%(raw)s' could not be parsed as "
                    "%(ftype)s for field '%(field)s'.",
                    raw=raw, ftype=field.type,
                    field=line.trigger_field_id.name))

            if field.type == 'selection':
                selection = field.selection
                if callable(selection):
                    try:
                        selection = selection(model)
                    except Exception:
                        selection = []
                valid_keys = {k for k, _l in (selection or [])}
                invalid = [s for s in parts if s not in valid_keys]
                if invalid:
                    raise ValidationError(_(
                        "Invalid selection key(s) %(invalid)s for field "
                        "'%(field)s' on '%(model)s'. Valid keys: %(valid)s.",
                        invalid=', '.join(invalid),
                        field=line.trigger_field_id.name,
                        model=line.rule_id.model_id.model,
                        valid=', '.join(sorted(valid_keys))))

    # ---- CRUD (line audit posts to the parent rule's chatter) ----

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if not line.rule_id:
                continue
            details = ' / '.join(
                '%s: <b>%s</b>' % (label, line._format_line_value(fname))
                for fname, label in _TRACKED_LINE_FIELDS.items()
            )
            line.rule_id.message_post(
                body=_("Added required field — %s", details))
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
                    body=_("Updated required field <b>%(field)s</b> — %(changes)s",
                           field=line.field_id.field_description
                                 or line.field_id.name or '?',
                           changes=' / '.join(changes)))
        return res

    def unlink(self):
        rule_messages = []
        for line in self:
            if not line.rule_id:
                continue
            rule_messages.append((
                line.rule_id,
                _("Removed required field — Field: <b>%(field)s</b> / "
                  "Trigger: <b>%(trigger)s</b> = <b>%(values)s</b>",
                  field=line.field_id.field_description
                        or line.field_id.name or '?',
                  trigger=line.trigger_field_id.field_description
                          or line.trigger_field_id.name or '?',
                  values=line.trigger_values or '')))
        res = super().unlink()
        for rule, body in rule_messages:
            rule.message_post(body=body)
        return res

    # ---- Helpers ----

    def _format_line_value(self, fname):
        self.ensure_one()
        if fname in ('field_id', 'trigger_field_id'):
            rec = self[fname]
            return rec.field_description or rec.name or ''
        if fname == 'override_group_ids':
            return ', '.join(self.override_group_ids.mapped('full_name')) or '∅'
        return self[fname] or ''
