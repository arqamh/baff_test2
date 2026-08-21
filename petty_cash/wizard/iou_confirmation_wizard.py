from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class IOUConfirmationWizard(models.TransientModel):
    """
    confirmation wizard for iou Request
    """
    _name = 'iou.confirmation.wizard'
    _description = 'IOU Confirmation Wizard'

    user_id = fields.Many2one('res.users', string="Approver",  default=lambda self: self.env.user.id)
    iou_request = fields.Many2one('petty.cash.release')
    message = fields.Text()
    currency_id = fields.Many2one('res.currency', readonly=False,
                                  string='Currency')

    def submission(self):
        """wizard submission"""
        self.iou_request.button_petty_cash_complete()
