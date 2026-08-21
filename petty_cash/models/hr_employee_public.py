from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    pay_petty_cash = fields.Float(default=0.00)
