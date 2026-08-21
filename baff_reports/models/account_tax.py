# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict

from collections import defaultdict
import math
import re


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    vat_type = fields.Selection([('vat', 'VAT'), ('s_vat', 'SVAT'), ('other', 'Other')], string="Local Tax Type")



class AccountTax(models.Model):
    _inherit = 'account.tax'


    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None):
        # Override Tax total function for add svat calculation
        """ Compute the tax totals details for the business documents.
        :param base_lines:  A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param currency:    The currency set on the business document.
        :param tax_lines:   Optional list of python dictionaries created using the '_convert_to_tax_line_dict' method.
                            If specified, the taxes will be recomputed using them instead of recomputing the taxes on
                            the provided base lines.
        :return: A dictionary in the following form:
            {
                'amount_total':                 The total amount to be displayed on the document, including every total
                                                types.
                'amount_untaxed':               The untaxed amount to be displayed on the document.
                'formatted_amount_total':       Same as amount_total, but as a string formatted accordingly with
                                                partner's locale.
                'formatted_amount_untaxed':     Same as amount_untaxed, but as a string formatted accordingly with
                                                partner's locale.
                'groups_by_subtotals':          A dictionary formed liked {'subtotal': groups_data}
                                                Where total_type is a subtotal name defined on a tax group, or the
                                                default one: 'Untaxed Amount'.
                                                And groups_data is a list of dict in the following form:
                    {
                        'tax_group_name':                   The name of the tax groups this total is made for.
                        'tax_group_amount':                 The total tax amount in this tax group.
                        'tax_group_base_amount':            The base amount for this tax group.
                        'formatted_tax_group_amount':       Same as tax_group_amount, but as a string formatted accordingly
                                                            with partner's locale.
                        'formatted_tax_group_base_amount':  Same as tax_group_base_amount, but as a string formatted
                                                            accordingly with partner's locale.
                        'tax_group_id':                     The id of the tax group corresponding to this dict.
                    }
                'subtotals':                    A list of dictionaries in the following form, one for each subtotal in
                                                'groups_by_subtotals' keys.
                    {
                        'name':                             The name of the subtotal
                        'amount':                           The total amount for this subtotal, summing all the tax groups
                                                            belonging to preceding subtotals and the base amount
                        'formatted_amount':                 Same as amount, but as a string formatted accordingly with
                                                            partner's locale.
                    }
                'subtotals_order':              A list of keys of `groups_by_subtotals` defining the order in which it needs
                                                to be displayed
            }
        """

        # ==== Compute the taxes ====

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        def grouping_key_generator(base_line, tax_values):
            source_tax = tax_values['tax_repartition_line'].tax_id
            return {'tax_group': source_tax.tax_group_id}

        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        tax_group_vals_list = []
        for tax_detail in global_tax_details['tax_details'].values():
            tax_group_vals = {
                'tax_group': tax_detail['tax_group'],
                'base_amount': tax_detail['base_amount_currency'],
                'tax_amount': tax_detail['tax_amount_currency'],
            }

            # Handle a manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if x['tax_repartition_line'].tax_id.tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        tax_group_vals_list = sorted(tax_group_vals_list, key=lambda x: (x['tax_group'].sequence, x['tax_group'].id))

        # ==== Partition the tax group values by subtotals ====

        amount_untaxed = global_tax_details['base_amount_currency']
        amount_tax = 0.0

        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']

            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(subtotal_order.get(subtotal_title, float('inf')), sequence)
            tax_percentage = self.env['account.tax'].search([('tax_group_id', '=', tax_group.id),('vat_type','=','s_vat')], limit=1).amount
            if tax_group_vals['base_amount'] * tax_percentage > 0:
                svat_amount = tax_group_vals['base_amount'] * tax_percentage / 100
                svat_state = True
            else:
                svat_amount = 0
                svat_state = False
            groups_by_subtotal[subtotal_title].append({
                'tax_amount': svat_amount,
                'is_svat': svat_state,
                'group_key': tax_group.id,
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'],
                                                              currency_obj=currency),
            })

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(self.env, amount_total, currency_obj=currency),
            })
            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax

        display_tax_base = (len(global_tax_details['tax_details']) == 1 and currency.compare_amounts(
            tax_group_vals_list[0]['base_amount'], amount_untaxed) != 0) \
                           or len(global_tax_details['tax_details']) > 1

        return {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': display_tax_base
        }