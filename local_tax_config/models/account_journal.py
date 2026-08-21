from odoo import fields, api, models


class InheritAccountJournal(models.Model):
    _inherit = 'account.journal'

    vat_type = fields.Selection([('vat', 'VAT'), ('s_vat', 'SVAT'), ('non_vat', 'Non VAT')], string="Tax Type")
