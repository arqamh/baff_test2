from odoo import models,fields,api,_


class FixedAllowanceDeductionTemplateLine(models.Model):
    _name = 'fixed.allowance.deduction.template.line'
    _description = 'Fixed Allowance Deduction Template Line'

    fixed_allowance_template_id = fields.Many2one('fixed.allowance.deduction.template', string='Template')
    fixed_deduction_template_id = fields.Many2one('fixed.allowance.deduction.template', string='Template')
    type_id = fields.Many2one(
        'fixed.allowance.deduction',
        string='Type')

    description = fields.Char(string='Description', related='type_id.name')
    is_standard = fields.Boolean(string='Standard', related='type_id.is_standard')
    amount = fields.Float(string='Amount')

    @api.onchange('is_standard','type_id')
    def onchange_amount(self):
        """
            Updates the amount field based on the state of the `is_standard` attribute
            and the selected `type_id`. If `is_standard` is set to True, the `amount`
            is updated with the corresponding value from the `type_id` record.

            Parameters
            ----------
            None

            Returns
            -------
            None
        """
        if self.is_standard:
            self.amount = self.type_id.amount

    @api.onchange('type_id')
    def onchange_type_id(self):
        """
            Updates the domain of the 'type_id' field dynamically based on a contextual filter.

            This function is triggered when the value of the 'type_id' field changes. It checks the
            context for a 'filter_type' entry. If 'filter_type' is found, the function modifies the
            domain of 'type_id' to include only those records whose related 'input_type_id.fixed_type'
            matches the filter value. If 'filter_type' is not found in the context, no filter is applied.

            Returns
            -------
            dict
                A dictionary containing the updated domain for the 'type_id' field. If a filter type
                is provided in the context, it restricts the domain; otherwise, an empty domain is set.
        """

        filter_type = self.env.context.get('filter_type')
        if filter_type:
            return {'domain': {'type_id': [('input_type_id.fixed_type', '=', filter_type)]}}
        else:
            return {'domain': {'type_id': []}}  # No filter applied if filter_type is not in context
