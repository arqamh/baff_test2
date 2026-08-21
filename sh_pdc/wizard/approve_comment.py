from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class PDCPaymentApproveCommentWizard(models.TransientModel):
    _name = 'pdc.payment.approve.comment.wizard'
    _description = 'Approval/Reject Comment'

    comment = fields.Text(string="Approve/Reject Comment")
    pdc_id = fields.Many2one('pdc.wizard')
    move_id = fields.Many2one('account.move')
    model_id = fields.Many2one('ir.model')
    action = fields.Char(string="Action")

    def approval_submission(self):
        """action for approval wizard"""
        if self.action == 'Approved':
            if self.pdc_id:
                template_id = self.env.ref('sh_pdc.mail_template_for_approved_pdc_payment')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web?login/#id=' + str(self.pdc_id.id) + '&view_type=form&model=pdc.wizard'
                self.pdc_id.write({
                    'custom_url': url,
                    'approved_by': self._uid,
                    'state': 'approved',
                    'approve_Date': datetime.today().date(),
                    'comment': self.comment,
                })
                self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)
            if self.move_id:
                template_id = self.env.ref('account_payment_approval.mail_template_for_approved_register_payment')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web?login/#id=' + str(self.move_id.id) + '&view_type=form&model=account.move'
                self.move_id.write({
                    'custom_url': url,
                    'approved_by': self._uid,
                    'state': 'approved',
                    'approve_Date': datetime.today().date(),
                    'comment': self.comment,
                })
                self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)

        if self.action == 'Rejected':
            if self.pdc_id:
                template_id = self.env.ref('sh_pdc.mail_template_for_reject_pdc_payment')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web?login/#id=' + str(self.pdc_id.id) + '&view_type=form&model=pdc.wizard'
                self.pdc_id.write({
                    'custom_url': url,
                    'approved_by': self._uid,
                    'state': 'cancel',
                    'approve_Date': datetime.today().date(),
                    'comment': self.comment,
                    'triggered_approval': False,
                })
                self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)
            if self.move_id:
                template_id = self.env.ref('account_payment_approval.mail_template_for_reject_register_payment')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web?login/#id=' + str(self.move_id.id) + '&view_type=form&model=account.move'
                self.move_id.write({
                    'custom_url': url,
                    'approved_by': self._uid,
                    'state': 'cancel',
                    'approve_Date': datetime.today().date(),
                    'comment': self.comment,
                    'triggered_approval': False,
                })
                self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)
