from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    partner_id = fields.Many2one('res.partner', string="Related Partner")
