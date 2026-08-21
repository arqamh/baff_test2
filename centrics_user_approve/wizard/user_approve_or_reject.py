from odoo import fields, models, api, _
from datetime import datetime
from datetime import timedelta


class RequestOrApproveUserWizard(models.TransientModel):
    _name = 'request.approve.reject.wizard'
    _description = "Request Approve or Reject Wizard"

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, string="Approvers", required=True)
    requested_user = fields.Many2one('res.users')
    model_id = fields.Many2one('ir.model', default=lambda self: self.env['ir.model'].sudo().search(
        [('model', '=', self._context.get('active_model'))], limit=1).id)
    record_id = fields.Integer(default=lambda self: self._context.get('active_id'))
    action_type = fields.Selection([('approve', 'Approve'), ('first_approve', 'First Approve'), ('production_approve', 'Production Approve'), ('reject', 'Rejected')], default='approve')
    comment = fields.Text()

    def send_email_notification(self, context):
        """Send email Notification"""
        template_id = self.env.ref('centrics_user_approve.mail_template_approve_or_reject')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web?login/#id=' + str(self.record_id) + '&view_type=form&model=' + str(self.sudo().model_id.model)

        context['mail_to'] = str(self.requested_user.partner_id.id)
        context['custom_url'] = url
        context['user'] = self.requested_user.display_name
        self.env['mail.template'].browse(template_id.id).with_context(context).send_mail(self.id, True)

    def submission(self):
        """action for submit or reject wizard data and send email after reject or approve"""

        #   Find related record
        record = self.env[self.sudo().model_id.model].sudo().search([('id', '=', self.record_id)], limit=1)
        context = self.env.context.get('mail_body')

        if self.action_type == 'approve':
            approved_by = self.user_id
            approved_date = fields.Datetime.now()
            approved_note = self.comment

            res = record.action_approve_the_request(approved_by, approved_date, approved_note)
            self.send_email_notification(context)
            return res

        if self.action_type == 'first_approve':
            approved_by = self.user_id
            approved_date = fields.Datetime.now()
            approved_note = self.comment

            res = record.action_approve_the_request(approved_by, approved_date, approved_note)
            self.send_email_notification(context)
            return res

        if self.action_type == 'production_approve':
            approved_by = self.user_id
            approved_date = fields.Datetime.now()
            approved_note = self.comment

            res = record.action_approve_the_request(approved_by, approved_date, approved_note)
            self.send_email_notification(context)
            return res

        if self.action_type == 'reject':
            rejected_by = self.user_id
            rejected_date = fields.Datetime.now()
            rejected_note = self.comment
            record.action_reject_the_request(rejected_by, rejected_date, rejected_note)
            self.send_email_notification(context)




