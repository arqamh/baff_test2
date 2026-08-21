from odoo import models, fields, api, _


class BoatType(models.Model):
    _name = 'boat.type'
    _description = "Boat Type"

    name = fields.Char(string='Name')
    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    length_overall = fields.Char(string="Length Overall")
    maximum_beam = fields.Char(string="Maximum Beam")
    draft = fields.Char(string="Draft")
    standard_engine = fields.Char(string="Standard Engine")
    selected_capacity = fields.Char(string="Selected Capacity")
    maximum_capacity = fields.Char(string="Maximum Allowed Capacity")
    color = fields.Char(string="Color")
