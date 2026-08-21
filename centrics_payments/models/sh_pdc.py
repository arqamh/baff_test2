from odoo import fields, models, api, _


class InheritPDC_wizard(models.Model):
    _inherit = 'pdc.wizard'

    receipt_id = fields.Many2one('account.receipt.payment')