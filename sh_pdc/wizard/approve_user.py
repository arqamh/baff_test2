from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class PDCPaymentsApproverUserWizard(models.TransientModel):
    _name = 'pdc.payments.approver.user.wizard'
    _description = 'Approval'

    user_id = fields.Many2one('res.users', string="Approver", required=1, domain=lambda self: [('groups_id', 'in', self.env.ref('sh_pdc.group_account_payment_pdc_approval_security').id)])
    pdc_id = fields.Many2one('pdc.wizard')
    move_id = fields.Many2one('account.move')
    model_id = fields.Many2one('ir.model')

    def approval_submission(self):
        """action for request approval in wizard"""
        if self.pdc_id:
            template_id = self.env.ref('sh_pdc.mail_template_for_pdc_payment_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web?login/#id=' + str(self._context.get('active_id')) + '&view_type=form&model=pdc.wizard'
            self.pdc_id.write({
                'custom_url': url,
                'state': 'waiting_approval',
                'triggered_approval': True,
            })
            self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)
            return True
        if self.move_id:
            template_id = self.env.ref('sh_pdc.mail_template_for_pdc_payment_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web?login/#id=' + str(self._context.get('active_id')) + '&view_type=form&model=account.move'
            self.move_id.write({
                'custom_url': url,
                'state': 'waiting_approval',
                'triggered_approval': True,
            })
            self.env['mail.template'].browse(template_id.id).send_mail(self.id, True)
            return True
