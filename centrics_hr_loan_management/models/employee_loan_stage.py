from odoo import models, fields, api, _


class EmployeeLoanStage(models.Model):
    _name = 'employee.loan.stage'
    _description = 'Employee Loan Stage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=1, tracking=True)
    fold = fields.Boolean('Folded in Kanban')
    allow_print = fields.Boolean('Allow Print', default=False, help="If checked, the user can print the loan document at this stage.")
