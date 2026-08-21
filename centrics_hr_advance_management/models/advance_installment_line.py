from odoo import models,fields,api,_

MONTHS = [
    ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
    ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')]

class AdvanceInstallmentLine(models.Model):
    _name = 'advance.installment.line'
    _description = 'Installment Line'

    advance_request_id = fields.Many2one('hr.advance.request', string="Advance Request")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    year = fields.Integer(string="Year")
    month = fields.Selection(selection=MONTHS, string="Month")
    installment_amount = fields.Float(string="Installment Amount")
    status = fields.Selection([('draft', 'Draft'), ('paid', 'Paid')], string="Status",
                              defualt='draft')
