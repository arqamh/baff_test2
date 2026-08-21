from odoo import models,fields,api,_


class FixedAllowanceDeductionTemplate(models.Model):
    _name = 'fixed.allowance.deduction.template'
    _description = 'Fixed Allowance Deduction Template'

    name = fields.Char(string="Name")
    fixed_allowance_template_line_ids = fields.One2many('fixed.allowance.deduction.template.line', 'fixed_allowance_template_id')
    fixed_deduction_template_line_ids = fields.One2many('fixed.allowance.deduction.template.line', 'fixed_deduction_template_id')