from odoo import models,fields,api, _


class FixedAllowanceDeduction(models.Model):

    _name = 'fixed.allowance.deduction'
    _description = 'Fixed Allowances and Deductions'

    name =  fields.Char(string='Name')
    input_type_id = fields.Many2one('hr.payslip.input.type',string='Input Type')
    is_standard = fields.Boolean(string='Standard')
    amount = fields.Float(string='Amount')


