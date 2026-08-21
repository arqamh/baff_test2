from odoo import fields, api, models


class CompanyInherit(models.Model):
    _inherit = 'res.company'

    svat_no = fields.Char(related='partner_id.svat_no', string='SVAT No', readonly=False)
    vat = fields.Char(related='partner_id.vat', string="VAT No", readonly=False)
    active = fields.Boolean(string="Active", default=True)
