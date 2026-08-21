import json
from collections import defaultdict

from lxml import etree

from odoo import models
from odoo.tools import frozendict


class Base(models.AbstractModel):
    """Inherit `base` so every model in the registry:
      - hides configured fields in form/tree views when the record's trigger
        field matches one of the configured values, and
      - silently drops writes to those fields for matching records
        (server-side safety net — no error is raised).
    """
    _inherit = 'base'

    _FIELD_INVISIBLE_SKIP_MODELS = {
        'field.invisible.rule',
        'field.invisible.rule.line',
        'field.readonly.rule',
        'field.readonly.rule.line',
        'field.required.rule',
        'field.required.rule.line',
        'ir.model',
        'ir.model.fields',
        'ir.model.access',
        'ir.ui.view',
        'ir.ui.menu',
        'ir.actions.actions',
        'ir.translation',
        'ir.config_parameter',
    }

    # ---- View rendering: inject invisible / column_invisible modifiers ----

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type not in ('form', 'tree'):
            return result
        if self._skip_field_invisible():
            return result
        Rule = self.env.get('field.invisible.rule')
        if Rule is None:
            return result
        try:
            rules = Rule._get_cached_rules_for_model(self._name)
        except Exception:
            return result
        if not rules:
            return result

        user_group_ids = set(self.env.user.groups_id.ids)

        field_rules = defaultdict(list)
        for rule in rules:
            tf = rule['trigger_field']
            if tf not in self._fields or not rule['trigger_values']:
                continue
            if rule['override_group_ids'] & user_group_ids:
                continue
            field_rules[rule['field_name']].append(
                (tf, rule['trigger_values']))
        if not field_rules:
            return result

        try:
            doc = etree.fromstring(result['arch'])
        except Exception:
            return result

        modifier_key = 'column_invisible' if view_type == 'tree' else 'invisible'

        trigger_fields_needed = set()
        modified = False

        for fname, conditions in field_rules.items():
            nodes = [n for n in doc.xpath("//field[@name='%s']" % fname)
                     if not self._is_nested_view_node(n)]
            if not nodes:
                continue
            clauses = []
            for tf, values in conditions:
                trigger_fields_needed.add(tf)
                for v in values:
                    clauses.append([tf, '=', v])
            new_invisible = (clauses if len(clauses) == 1
                             else ['|'] * (len(clauses) - 1) + clauses)

            for node in nodes:
                try:
                    modifiers = json.loads(node.get('modifiers') or '{}')
                except Exception:
                    modifiers = {}
                existing = modifiers.get(modifier_key)
                if existing is True:
                    continue
                if isinstance(existing, list) and existing:
                    combined = ['|'] + new_invisible + existing
                else:
                    combined = new_invisible
                modifiers[modifier_key] = combined
                node.set('modifiers', json.dumps(modifiers))
                modified = True

        if modified and view_type == 'form':
            existing_field_names = {
                f.get('name') for f in doc.xpath('//field[@name]')
                if not self._is_nested_view_node(f)
            }
            missing = trigger_fields_needed - existing_field_names
            if missing:
                anchor = doc.xpath('//sheet')
                parent = anchor[0] if anchor else doc
                for tf in missing:
                    el = etree.SubElement(parent, 'field')
                    el.set('name', tf)
                    el.set('modifiers', json.dumps(
                        {'invisible': True, 'column_invisible': True}))

        if modified:
            result['arch'] = etree.tostring(doc, encoding='unicode')
            if trigger_fields_needed:
                models_dict = dict(result.get('models') or {})
                current = set(models_dict.get(self._name, ()))
                current |= trigger_fields_needed
                models_dict[self._name] = tuple(current)
                try:
                    result['models'] = frozendict(
                        {k: tuple(v) for k, v in models_dict.items()})
                except Exception:
                    result['models'] = {
                        k: tuple(v) for k, v in models_dict.items()}
        return result

    def _skip_field_invisible(self):
        return (self._name in self._FIELD_INVISIBLE_SKIP_MODELS
                or self._transient or self._abstract)

    @staticmethod
    def _is_nested_view_node(node):
        for ancestor in node.iterancestors():
            if ancestor.tag == 'field':
                return True
        return False

    @staticmethod
    def _record_trigger_value(rec, trigger_field, trigger_field_type):
        val = rec[trigger_field]
        if trigger_field_type == 'many2one':
            return val.id if val else False
        if trigger_field_type == 'boolean':
            return bool(val)
        return val if val not in (False, None) else False

    # ---- Write: silently strip hidden-field keys ----

    def write(self, vals):
        if not vals or self.env.context.get('bypass_field_invisible'):
            return super().write(vals)
        if self._skip_field_invisible():
            return super().write(vals)
        Rule = self.env.get('field.invisible.rule')
        if Rule is None:
            return super().write(vals)
        rules = Rule._get_cached_rules_for_model(self._name)
        if not rules:
            return super().write(vals)

        user_group_ids = set(self.env.user.groups_id.ids)
        touched = set(vals.keys())
        partitions = defaultdict(lambda: self.browse())
        for rec in self:
            strip = set()
            for rule in rules:
                tf = rule['trigger_field']
                if tf not in self._fields:
                    continue
                fname = rule['field_name']
                if fname not in touched:
                    continue
                if rule['override_group_ids'] & user_group_ids:
                    continue
                rec_val = self._record_trigger_value(
                    rec, tf, rule['trigger_field_type'])
                if rec_val in rule['trigger_values']:
                    strip.add(fname)
            partitions[frozenset(strip)] |= rec

        result = True
        for strip, recs in partitions.items():
            sub_vals = {k: v for k, v in vals.items() if k not in strip} if strip else vals
            if sub_vals and not super(Base, recs).write(sub_vals):
                result = False
        return result
