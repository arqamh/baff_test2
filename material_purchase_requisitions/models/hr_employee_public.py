from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    dest_location_id = fields.Many2one('stock.location', string='Destination Location')
