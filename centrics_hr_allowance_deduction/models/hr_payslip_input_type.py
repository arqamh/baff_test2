from odoo import models,fields,api,_


class HrPayslipInputType(models.Model):
    _inherit = 'hr.payslip.input.type'

    fixed_type = fields.Selection([
        ('fixed_allowance', 'Fixed Allowance'),
        ('fixed_deduction', 'Fixed Deduction'),
    ], string='Type')