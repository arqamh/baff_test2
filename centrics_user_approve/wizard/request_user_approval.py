from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class RequestUserApprove(models.TransientModel):
    _name = 'request.user.approve.wizard'
    _description = "Request approval Wizard"

    def _domain_user_ids_groups(self):
        """changed the user groups when is there a context with user group"""
        domain = []
        if self._context.get('approve_group'):
            domain = [('groups_id', 'in', self._context.get('approve_group'))]
        return domain

    user_ids = fields.Many2many('res.users', 'request_approve_user_rel', 'request_id', 'appror_id', string="Approvers", required=True, domain=_domain_user_ids_groups)
    model_id = fields.Many2one('ir.model', default=lambda self: self.env['ir.model'].sudo().search([('model', '=', self._context.get('active_model'))], limit=1).id)
    record_id = fields.Integer(default=lambda self: self._context.get('active_id'))
    request_by = fields.Many2one('res.users', string="Request By", default=lambda self: self.env.user)

    # domain = lambda self: [('groups_id', 'in', self.env.ref('petty_cash.petty_cash_group_manager').id)]
    def request_approve(self):
        """function for confirm approval request"""
        record_obj = self.env[self.sudo().model_id.model].sudo().search([('id', '=', self.record_id)], limit=1)
        if record_obj:
            approval_requested_by = self.request_by.id
            approval_requested_date = fields.Datetime.now()
            approval_requested_users = [(6, 0, self.user_ids.ids )]
            # Changed status
            res = record_obj.action_requested_approval(approval_requested_by, approval_requested_date, approval_requested_users)

            # Send Email
            template_id = self.env.ref('centrics_user_approve.mail_template_for_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web?login/#id=' + str(self.record_id) + '&view_type=form&model=' + str(self.sudo().model_id.model)
            context = self.env.context.get('mail_body')

            context['mail_to'] = ','.join([str(x.partner_id.id) for x in self.user_ids])
            context['custom_url'] = url
            self.env['mail.template'].sudo().browse(template_id.id).with_context(context).send_mail(self.id, True)
            return res

