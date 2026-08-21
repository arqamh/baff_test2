from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class PDCConfirmationWizard(models.TransientModel):
    """
    confirmation wizard for iou Request
    """
    _name = 'pdc.confirmation.wizard'
    _description = 'PDC Confirmation Wizard'

    pdc_payment_id = fields.Many2one('pdc.wizard')
    message = fields.Text()

    def submission(self):
        """wizard submission"""
        context = self.env.context.copy()
        context.update({
            'confirm_cheque_date': True
        })
        self.pdc_payment_id.with_context(context).action_deposited()

    def reject_deposit(self):
        """wizard cancellation"""
        if self.pdc_payment_id.state != 'registered':
            self.pdc_payment_id.button_register()
        else:
            pass
