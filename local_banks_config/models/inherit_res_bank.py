from odoo import fields, models, api, _


class InheritResBank(models.Model):
    _inherit = 'res.bank'

    main_bank_id = fields.Many2one('main.bank', string="Bank")
    is_slips_allowed = fields.Boolean(string="Is Slip Transfer Allowed")
