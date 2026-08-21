from odoo import models,fields,api,_


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_code = fields.Char(string="Company Code")

    _sql_constraints = [
        ('unique_company_code', 'unique(company_code)', 'The Company Code must be unique.'),
    ]
