from odoo import models,fields,api,_


class FixedAllowanceDeductionLine(models.Model):
    _name = 'fixed.allowance.deduction.line'
    _description = 'Fixed Allowance Deduction Line'

    hr_contract_allowance_id = fields.Many2one('hr.contract', string='Contract')
    hr_contract_deduction_id = fields.Many2one('hr.contract', string='Contract')
    type_id = fields.Many2one(
        'fixed.allowance.deduction',
        string='Type')

    description = fields.Char(string='Description', related='type_id.name')
    is_standard = fields.Boolean(string='Standard', related='type_id.is_standard')
    amount = fields.Float(string='Amount')



    @api.onchange('type_id')
    def onchange_type_id(self):
        """
        Updates the `amount` field based on the `type_id` field selection and the
        value of `is_standard`. This ensures that the `amount` is consistent with
        the `type_id`'s predefined amount when a standard type is selected.

        Parameters
        ----------
        None

        Raises
        ------
        None
        """
        if self.type_id and self.is_standard:
            self.amount = self.type_id.amount

        filter_type = self.env.context.get('filter_type')
        if filter_type:
            return {'domain': {'type_id': [('input_type_id.fixed_type', '=', filter_type)]}}
        else:
            return {'domain': {'type_id': []}}  # No filter applied if filter_type is not in context

