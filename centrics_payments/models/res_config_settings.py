from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_payment_approval = fields.Boolean('Vendor Payment  Approval',
                                              config_parameter='centrics_payments.account_payment_approval')
    payment_approval_amount = fields.Float('Minimum Approval Amount',
                                              config_parameter='centrics_payments.payment_approval_amount')
