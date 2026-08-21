from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    vendor_bill_journal = fields.Many2one(comodel_name='account.journal',domain="[('type','in', ('bank','cash'))]")