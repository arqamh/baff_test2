from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class PaymentSendForApprovalWizard(models.TransientModel):
    _name = 'payment.sendfor.approval.wizard'
    _description = 'Send for Approval'

    user_id = fields.Many2one('res.users', string="Approver", required=1, domain=lambda self: [('groups_id', 'in', self.env.ref('centrics_payments.centrics_payment_approval_security').id)])
    payment_id = fields.Many2one('account.payment')
    bulk_payment_id = fields.Many2one('account.receipt.payment')
    model_id = fields.Many2one('ir.model')

    def approval_submission(self):
        """Submit request approval"""
        if self.payment_id:
            return self.payment_id.update_payments_approval_request(self.user_id)
        elif self.bulk_payment_id:
            return self.bulk_payment_id.update_payments_approval_request(self.user_id)
