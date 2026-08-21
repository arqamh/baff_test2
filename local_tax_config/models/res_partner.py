from odoo import fields, api, models


class CustomerInherit(models.Model):
    _inherit = 'res.partner'

    vat_type = fields.Selection([('non_vat', 'Non VAT'),
                                 ('s_vat', 'SVAT'),
                                 ('vat', 'VAT')], string="VAT Type", default='non_vat')
    svat_no = fields.Char('SVAT No')
    vat = fields.Char(string='Tax No',
                      help="The Tax Identification Number. Complete it if the contact is subjected to government taxes. "
                           "Used in some legal statements.")
