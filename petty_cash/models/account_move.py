from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    is_reversed_journal = fields.Boolean(default=False)
    petty_cash_payment_id = fields.Many2one('petty.cash.release')
    petty_cash_amount = fields.Monetary(string='Petty cash Amount', store=True, tracking=True)

