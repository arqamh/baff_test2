from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class PDCConfirmationWizard(models.TransientModel):
    _inherit = 'pdc.confirmation.wizard'

    account_payment_id = fields.Many2one('account.payment')

    def submission(self):
        """Override submission Function

        """
        context = self.env.context.copy()
        context.update({
            'confirm_cheque_date': True
        })
        if self.pdc_payment_id:
            self.pdc_payment_id.with_context(context).action_deposited()
        else:
            if self.account_payment_id.state == "waiting_approval":
                return self.account_payment_id.with_context(context).action_approve_payment()
            else:
                return self.account_payment_id.action_post()

    def reject_deposit(self):
        """wizard cancellation"""
        if self.pdc_payment_id and self.pdc_payment_id.state != 'registered':
            self.pdc_payment_id.button_register()
        else:
            pass
