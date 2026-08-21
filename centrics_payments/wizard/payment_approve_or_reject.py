from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class PaymentApproveRjectCommentWizard(models.TransientModel):
    _name = 'payment.approve.reject.comment.wizard'
    _description = 'Payment Approval/Reject Comment'

    comment = fields.Text(string="Approve/Reject Comment")
    payment_id = fields.Many2one('account.payment')
    bulk_payment_id = fields.Many2one('account.receipt.payment')
    model_id = fields.Many2one('ir.model')
    action = fields.Selection([('approve', 'Approved'), ('reject', 'Reject')], string="Action")

    def approval_submission(self):
        """action for submit payment approval"""
        if self.payment_id:
            return self.payment_id.update_payments_with_approve(self.env.user, self.comment)
        elif self.bulk_payment_id:
            return self.bulk_payment_id.update_payments_with_approve(self.env.user, self.comment)

    def reject_submission(self):
        """action for submit payment rejection"""
        if self.payment_id:
            return self.payment_id.update_payment_with_reject(self.env.user, self.comment)
        elif self.bulk_payment_id:
            return self.bulk_payment_id.update_payment_with_reject(self.env.user, self.comment)