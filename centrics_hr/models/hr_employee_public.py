from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    employee_number = fields.Char(string='Employee Number')
    requested_by = fields.Many2one('res.users', string="Requested By", readonly=True,
                                   help="User who submitted the profile for approval")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'HR Manager Approval'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
    ], string='Status', copy=False,
        tracking=True, help='Status of the Employee', default='draft')
    joined_date = fields.Date(string='Joined Date')
    retirement_date = fields.Date(string='Retirement Date')
    approver_id = fields.Many2one(
        'res.users',
        string="Approver",
        help="Select the user responsible for approving the employee profile."
    )
