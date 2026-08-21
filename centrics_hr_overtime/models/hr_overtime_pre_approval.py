from odoo import models,fields,api,_
from odoo.exceptions import ValidationError


class HrOvertimePreApproval(models.Model):
    _name = 'hr.overtime.pre.approval'
    _description = 'Hr Overtime Pre Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string="Name", tracking=True)
    department_id = fields.Many2one('hr.department', string="Department", tracking=True)
    job_id = fields.Many2one(
        'hr.job',
        string="Job",
        domain="[('department_id', '=', department_id)]",
        tracking=True
    )
    start_date = fields.Date(string="Start Date", tracking=True)
    end_date = fields.Date(string="End Date", tracking=True)
    status = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        string="Status", default='draft',
        tracking=True)
    employee_ids = fields.Many2many(
        'hr.employee',
        string="Employees",
        domain="[('department_id', '=', department_id), ('job_id', '=', job_id)]",
        tracking=True
    )
    description = fields.Text(string="Description", tracking=True)
    notes = fields.Text(string="Notes", tracking=True)

    @api.constrains('start_date', 'end_date')
    def _check_date_validation(self):
        """
        Check that the start date is before or equal to the end date.
        Raise a ValidationError if the start date is after the end date.
        """
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_("Start Date cannot be later than the End Date."))

    def action_submit(self):
        """
        Submit the overtime pre-approval.
        If no name is assigned, generate a sequence number for the record.
        Update the status to 'submitted' and log a message in the chatter.
        """
        for record in self:
            if not record.name:
                record.name = self.env['ir.sequence'].next_by_code('hr.overtime.pre.approval')
            record.write({'status': 'submitted'})
            record.message_post(body="Overtime Pre Approval has been submitted.")

    def action_approve(self):
        """
        Approve the overtime pre-approval.
        Update the status to 'approved' and log a message in the chatter.
        """
        self.write({'status': 'approved'})
        self.message_post(body="Overtime Pre Approval has been approved.")

    def action_reject(self):
        """
        Reject the overtime pre-approval.
        Update the status to 'rejected' and log a message in the chatter.
        """
        self.write({'status': 'rejected'})
        self.message_post(body="Overtime Pre Approval has been Rejected.")

    def action_reset_to_draft(self):
        # Reset the status of the overtime pre-approval to 'draft' and log a message in the chatter.
        self.write({'status': 'draft'})
        self.message_post(body="Overtime Pre Approval has been reset to draft.")
