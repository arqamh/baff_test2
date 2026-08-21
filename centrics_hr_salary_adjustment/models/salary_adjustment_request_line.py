from odoo import models,fields,api,_

class SalaryAdjustmentRequestLine(models.Model):
    _name = 'salary.adjustment.request.line'
    _description = 'Salary Adjustment Request Line'

    request_id = fields.Many2one('salary.adjustment.request', string='Request')
    type = fields.Selection([('basic', 'Basic'),('allowance', 'Allowance'), ('deduction', 'Deduction')], string='Type')
    allowance_deduction_id = fields.Many2one('fixed.allowance.deduction', string='Allowance/Deduction')
    existing_record_id= fields.Integer(string='Existing Record')
    current_amount = fields.Float(string='Current Amount')
    new_amount = fields.Float(string='New Amount')

