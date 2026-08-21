# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import fields, models, _


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'mail.thread', 'mail.activity.mixin']

    # ---------------------------------------------------
    # Tracked fields (company-dependent + M2M)
    # ---------------------------------------------------

    _CHATTER_TRACKED_FIELDS = {
        'property_cost_method': 'Costing Method',
        'property_valuation': 'Inventory Valuation',
        'property_stock_valuation_account_id': 'Stock Valuation Account',
        'property_stock_journal': 'Stock Journal',
        'property_stock_account_input_categ_id': 'Stock Input Account',
        'property_stock_account_output_categ_id': 'Stock Output Account',
        'property_account_income_categ_id': 'Income Account',
        'property_account_expense_categ_id': 'Expense Account',
        'route_ids': 'Routes',
    }

    def write(self, vals):
        fields_to_track = {
            f: label
            for f, label in self._CHATTER_TRACKED_FIELDS.items()
            if f in vals
        }

        if not fields_to_track:
            return super().write(vals)

        # Build selection display maps before write
        sel_maps = {}
        for field_name in fields_to_track:
            field = self._fields.get(field_name)
            if field and field.type == 'selection':
                sel_maps[field_name] = dict(field._description_selection(self.env))

        # Capture old values before write
        old_values = {}
        for record in self:
            old_values[record.id] = {}
            for field_name in fields_to_track:
                field = self._fields.get(field_name)
                if not field:
                    continue
                value = record[field_name]
                if field.type == 'many2one':
                    old_values[record.id][field_name] = (
                        value.id,
                        value.display_name if value else _('None'),
                    )
                elif field.type == 'many2many':
                    old_values[record.id][field_name] = set(value.ids)
                else:
                    old_values[record.id][field_name] = value

        res = super().write(vals)

        # Post a log note for each record that had changes
        for record in self:
            lines = []
            for field_name, label in fields_to_track.items():
                field = self._fields.get(field_name)
                if not field:
                    continue

                old = old_values[record.id][field_name]

                if field.type == 'many2one':
                    old_id, old_name = old
                    new_value = record[field_name]
                    new_id = new_value.id if new_value else False
                    if old_id != new_id:
                        new_name = new_value.display_name if new_value else _('None')
                        lines.append(
                            Markup('<li><b>{label}</b>: {old} &#8594; {new}</li>').format(
                                label=label,
                                old=old_name,
                                new=new_name,
                            )
                        )

                elif field.type == 'selection':
                    new_val = record[field_name]
                    if old != new_val:
                        sel = sel_maps.get(field_name, {})
                        old_display = sel.get(old, old) if old else _('None')
                        new_display = sel.get(new_val, new_val) if new_val else _('None')
                        lines.append(
                            Markup('<li><b>{label}</b>: {old} &#8594; {new}</li>').format(
                                label=label,
                                old=old_display,
                                new=new_display,
                            )
                        )

                elif field.type == 'many2many':
                    old_ids = old
                    new_ids = set(record[field_name].ids)
                    added_ids = new_ids - old_ids
                    removed_ids = old_ids - new_ids
                    if added_ids or removed_ids:
                        parts = []
                        if added_ids:
                            added_names = ', '.join(
                                self.env[field.comodel_name].browse(list(added_ids)).mapped('display_name')
                            )
                            parts.append(_('Added: %s') % added_names)
                        if removed_ids:
                            removed_names = ', '.join(
                                self.env[field.comodel_name].browse(list(removed_ids)).mapped('display_name')
                            )
                            parts.append(_('Removed: %s') % removed_names)
                        lines.append(
                            Markup('<li><b>{label}</b>: {detail}</li>').format(
                                label=label,
                                detail='; '.join(parts),
                            )
                        )

            if lines:
                body = Markup('<ul>') + Markup('').join(lines) + Markup('</ul>')
                record._message_log(body=body)

        return res
