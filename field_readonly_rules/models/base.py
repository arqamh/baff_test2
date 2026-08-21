import json
from collections import defaultdict

from lxml import etree

from odoo import models
from odoo.tools import frozendict


class Base(models.AbstractModel):
    """Inherit `base` so every model in the registry:
      - renders configured fields as readonly in form/tree views when the
        record's trigger field matches one of the configured values, and
      - silently drops writes to those fields for matching records
        (server-side safety net — no error is raised).
    """
    _inherit = 'base'

    # Models that must never be affected by user-defined readonly rules —
    # avoids recursion and protects the plumbing.
    _FIELD_READONLY_SKIP_MODELS = {
        'field.readonly.rule',
        'field.readonly.rule.line',
        'ir.model',
        'ir.model.fields',
        'ir.model.access',
        'ir.ui.view',
        'ir.ui.menu',
        'ir.actions.actions',
        'ir.translation',
        'ir.config_parameter',
    }

    # ---- View rendering: inject readonly modifiers ----

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type not in ('form', 'tree'):
            return result
        if self._skip_field_readonly():
            return result
        Rule = self.env.get('field.readonly.rule')
        if Rule is None:
            return result

        user_group_ids = set(self.env.user.groups_id.ids)

        # --- Rules for the current model ---
        try:
            rules = Rule._get_cached_rules_for_model(self._name)
        except Exception:
            rules = ()

        field_rules = self._build_field_rules(rules, self._fields, user_group_ids)

        # --- Rules for embedded One2many / Many2many sub-models ---
        # Only form views embed sub-model trees inline; tree views don't.
        sub_model_rules = {}  # relational_field_name -> (sub_model, field_rules_dict)
        if view_type == 'form':
            for fname, field in self._fields.items():
                if field.type not in ('one2many', 'many2many'):
                    continue
                sub_name = getattr(field, 'comodel_name', None)
                if not sub_name:
                    continue
                sub_model = self.env.get(sub_name)
                if sub_model is None or sub_model._skip_field_readonly():
                    continue
                try:
                    s_rules = Rule._get_cached_rules_for_model(sub_name)
                except Exception:
                    continue
                if not s_rules:
                    continue
                s_field_rules = self._build_field_rules(
                    s_rules, sub_model._fields, user_group_ids)
                if s_field_rules:
                    sub_model_rules[fname] = (sub_model, s_field_rules)

        if not field_rules and not sub_model_rules:
            return result

        try:
            doc = etree.fromstring(result['arch'])
        except Exception:
            return result

        trigger_fields_needed = set()
        modified = False

        # --- Inject modifiers for top-level fields of the current model ---
        for fname, conditions in field_rules.items():
            nodes = [n for n in doc.xpath("//field[@name='%s']" % fname)
                     if not self._is_nested_view_node(n)]
            if not nodes:
                continue
            new_readonly, tfs = self._build_readonly_domain(conditions)
            trigger_fields_needed |= tfs
            for node in nodes:
                if self._merge_readonly_modifier(node, new_readonly):
                    modified = True

        # --- Inject modifiers into embedded sub-model inline trees ---
        for rel_fname, (sub_model, s_field_rules) in sub_model_rules.items():
            rel_nodes = [n for n in doc.xpath("//field[@name='%s']" % rel_fname)
                         if not self._is_nested_view_node(n)]
            for rel_node in rel_nodes:
                sub_trigger_fields = set()
                sub_modified = False
                for locked_fname, conditions in s_field_rules.items():
                    inner_nodes = rel_node.xpath(
                        ".//field[@name='%s']" % locked_fname)
                    if not inner_nodes:
                        continue
                    new_readonly, tfs = self._build_readonly_domain(conditions)
                    sub_trigger_fields |= tfs
                    for node in inner_nodes:
                        if self._merge_readonly_modifier(node, new_readonly):
                            sub_modified = True
                if not sub_modified:
                    continue
                modified = True
                # Ensure trigger fields are present inside the sub-view so the
                # client can evaluate the readonly condition per row.
                sub_views = rel_node.xpath('.//tree | .//form')
                if sub_views:
                    existing_in_sub = {
                        n.get('name') for n in rel_node.xpath('.//field[@name]')}
                    for tf_name in sub_trigger_fields - existing_in_sub:
                        el = etree.SubElement(sub_views[0], 'field')
                        el.set('name', tf_name)
                        el.set('modifiers', json.dumps(
                            {'invisible': True, 'column_invisible': True}))
                # Register sub-model trigger fields in the models dict so the
                # client knows to load them.
                if sub_trigger_fields:
                    models_dict = dict(result.get('models') or {})
                    current = set(models_dict.get(sub_model._name, ()))
                    current |= sub_trigger_fields
                    models_dict[sub_model._name] = tuple(current)
                    try:
                        result['models'] = frozendict(
                            {k: tuple(v) for k, v in models_dict.items()})
                    except Exception:
                        result['models'] = {
                            k: tuple(v) for k, v in models_dict.items()}

        # Add any missing top-level trigger fields as invisible in form views.
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

    # ---- Helpers ----

    @staticmethod
    def _build_field_rules(rules, fields_dict, user_group_ids):
        """Return field_name -> [(trigger_field, frozenset(values))] for rules
        that are applicable to the given fields_dict and user groups."""
        field_rules = defaultdict(list)
        for rule in rules:
            tf = rule['trigger_field']
            if tf not in fields_dict or not rule['trigger_values']:
                continue
            if rule['override_group_ids'] & user_group_ids:
                continue
            field_rules[rule['field_name']].append((tf, rule['trigger_values']))
        return field_rules

    @staticmethod
    def _build_readonly_domain(conditions):
        """Convert a list of (trigger_field, frozenset(values)) pairs into an
        Odoo domain clause list and the set of trigger field names used."""
        clauses = []
        trigger_fields = set()
        for tf, values in conditions:
            trigger_fields.add(tf)
            for v in sorted(values):  # sorted for deterministic arch output
                clauses.append([tf, '=', v])
        domain = (clauses if len(clauses) == 1
                  else ['|'] * (len(clauses) - 1) + clauses)
        return domain, trigger_fields

    @staticmethod
    def _merge_readonly_modifier(node, new_readonly):
        """Merge new_readonly domain into the node's existing modifiers.
        Returns True if the node was modified."""
        try:
            modifiers = json.loads(node.get('modifiers') or '{}')
        except Exception:
            modifiers = {}
        existing = modifiers.get('readonly')
        if existing is True:
            return False
        if isinstance(existing, list) and existing:
            combined = ['|'] + new_readonly + existing
        else:
            combined = new_readonly
        modifiers['readonly'] = combined
        node.set('modifiers', json.dumps(modifiers))
        return True

    def _skip_field_readonly(self):
        return (self._name in self._FIELD_READONLY_SKIP_MODELS
                or self._transient or self._abstract)

    @staticmethod
    def _is_nested_view_node(node):
        # A <field> whose ancestor is another <field> is part of an inline
        # sub-view (one2many/many2many) — skip it, it's not a direct field
        # of the current model.
        for ancestor in node.iterancestors():
            if ancestor.tag == 'field':
                return True
        return False

    @staticmethod
    def _record_trigger_value(rec, trigger_field, trigger_field_type):
        """Return the comparable scalar of a record's trigger field, matching
        the value space produced by `_get_cached_rules_for_model`."""
        val = rec[trigger_field]
        if trigger_field_type == 'many2one':
            return val.id if val else False
        if trigger_field_type == 'boolean':
            return bool(val)
        return val if val not in (False, None) else False

    # ---- Write: silently strip locked keys ----

    def write(self, vals):
        if not vals or self.env.context.get('bypass_field_readonly'):
            return super().write(vals)
        if self._skip_field_readonly():
            return super().write(vals)
        Rule = self.env.get('field.readonly.rule')
        if Rule is None:
            return super().write(vals)
        try:
            with self.env.cr.savepoint():
                rules = Rule._get_cached_rules_for_model(self._name)
        except Exception:
            return super().write(vals)
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