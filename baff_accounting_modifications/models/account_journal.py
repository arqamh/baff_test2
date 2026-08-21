from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    bypass_currency_validation = fields.Boolean(
        string="Bypass Currency Validation",
        default=False,
        help="When enabled, allows changing the currency on accounts even if "
             "there are existing journal entries with different foreign currencies."
    )