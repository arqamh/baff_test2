from odoo import fields, api, models
from odoo.exceptions import UserError


class InheritAccountTax(models.Model):
    _inherit = 'account.tax'

    vat_type = fields.Selection([('vat', 'VAT'), ('s_vat', 'SVAT'), ('other', 'Other')], string="Local Tax Type")
    sscl_tax = fields.Boolean(string="SSCL Tax", default=False)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, type_tax_use, vat_type)', 'Tax names must be unique !'),
    ]

    @api.onchange('type_tax_use')
    def onchange_type_tax_use(self):
        """Creating domain to filter journal selections according to the tax type"""
        for record in self:
            if record.type_tax_use:
                if record.type_tax_use == 'none':
                    return {'domain': {'journal_id': []}}
                else:
                    return {'domain': {'journal_id': [('type', '=', record.type_tax_use)]}}
