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
    comment = fields.Text()

    def submission(self):
        """ Rejecting RFQ and sending email """
        record = self.env[self.sudo().model_id.model].sudo().search([('id', '=', self.record_id)], limit=1)
        approver_line = record.job_costing_approval_line_ids.filtered(
            lambda x: x.id == self.env.context.get('approver_line'))
        approver_line.write({
            'state': 'rejected',
            'status_updated_datetime': datetime.now(),
            'comment': self.comment
        })
        record.button_cancel()
        record.write({
            'state': 'rejected'
        })
        template_id = self.env.ref(
            'odoo_job_costing_management.odoo_job_costing_management_request_for_approval_mail_template')
        msg = 'The following Job Costing is rejected by %s' % self.env['res.users'].browse(self._uid).name

        record.with_context(mail_body={}).send_email_purchase(record.id, 'job.costing', "Rejected",
                                                            record.create_uid, template_id, msg)



