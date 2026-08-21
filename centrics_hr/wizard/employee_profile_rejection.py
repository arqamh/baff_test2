from odoo import api, fields, models, _


class EmployeeProfileRejection(models.TransientModel):
    _name = 'employee.profile.rejection'
    _description = 'Employee Profile Rejection'

    rejection_reason = fields.Char(string="Rejection Reason")
    employee_id = fields.Many2one('hr.employee')

    def action_confirm_reject(self):
        """Rejection mail will send."""
        email_values = {'user': self.employee_id.create_uid.login, 'name': self.employee_id.create_uid.name,'reason':self.rejection_reason}
        self.env.ref('centrics_hr.reject_mail_template').with_context(
            order=email_values).send_mail(self.employee_id.id, force_send=True) 
        self.employee_id.write({'state':'reject',})