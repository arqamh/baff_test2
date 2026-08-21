from dateutil.relativedelta import relativedelta
from odoo import models,fields,api,_
from odoo.exceptions import UserError,ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    name_initials = fields.Char(string='Initials of the Name')
    first_name = fields.Char(string='First Name')
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name')
    employee_number = fields.Char(string='Employee Number')
    requested_by = fields.Many2one('res.users', string="Requested By", readonly=True,
                                   help="User who submitted the profile for approval")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'HR Manager Approval'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
    ], string='Status', copy=False,
        tracking=True, help='Status of the Employee', default='draft')
    joined_date = fields.Date(string='Joined Date')
    retirement_date = fields.Date(string='Retirement Date', compute='_compute_retirement_date', store=True)
    to_show_statusbar = fields.Boolean(related="company_id.employee_approval_needed")
    to_generate_employee_number = fields.Boolean(related="company_id.employee_number_auto_generate")
    approver_id = fields.Many2one(
        'res.users',
        string="Approver",
        domain=lambda self: [('groups_id', '=', self.env.ref('centrics_hr.employee_profile_approve').id)],
        help="Select the user responsible for approving the employee profile."
    )
     
    
    @api.depends('joined_date', 'birthday', 'company_id.retirement_age')
    def _compute_retirement_date(self):
        """
        Computes and sets the retirement date for each record based on the joined
        date, birthday, and the retirement age defined by the associated company.
        If either the joined date or birthday is missing, the retirement date will
        be set to None.

        Parameters
        ----------
        self : object
            The current instance of the model for which the retirement date
            computation applies.

        Notes
        -----
        The computed retirement date is derived by adding the company's retirement
        age (in years) to the employee's birthday. This computation will only occur
        if both the joined date and birthday values are available. Otherwise, the
        retirement date is assigned as None.
        """
        for record in self:
            if record.joined_date and record.birthday:
                record.retirement_date = record.birthday + relativedelta(years=record.company_id.retirement_age)
            else:
                record.retirement_date = None

    @api.model
    def create(self, vals):
        """
        Creates a new HR employee record with optional features based on company settings.

        This method overrides the default create operation to incorporate custom behaviors
        based on company-level preferences. If the company's `employee_approval_needed`
        setting is enabled, the newly created employee record will be inactive. Additionally,
        if `employee_number_auto_generate` is enabled and `employee_approval_needed`
        is disabled, an auto-generated employee number will be assigned to the record.

        """
        res = super(HrEmployee, self).create(vals)
        if self.env.company.employee_approval_needed:
            res.active = False
        if self.env.company.employee_number_auto_generate and not self.env.company.employee_approval_needed:
            res.employee_number = self.env['ir.sequence'].next_by_code('employee.number') or ''
        if not self.env.company.employee_approval_needed:
            res.joined_date = fields.Date.today()
        return res

    def action_send_for_approval(self):
        """Mail will send to Manager after clicking the button"""
        email_values = {'user': self.parent_id.user_id.login, 'name': self.parent_id.user_id.name}
        self.env.ref('centrics_hr.to_approve_mail_template').with_context(
            order=email_values).send_mail(self.id, force_send=True)
        self.write({'state': 'waiting', 'requested_by': self.env.user.id})

    def action_approved(self):
        """
        Sends an approval email, updates the employee number if needed, and changes the state of the record to approved.

        This method performs three primary actions:
        1. Sends an email notification to indicate that the action has been approved.
        2. Auto-generates an employee number based on the configured sequence if company settings
           require automatic generation and the employee does not already have an assigned number.
        3. Updates the record to set it as active and change its state to 'approve'.
        """
        email_values = {'user': self.create_uid.login, 'name': self.create_uid.name}
        self.env.ref('centrics_hr.new_approved_mail_template').with_context(
            order=email_values).send_mail(self.id, force_send=True)
        if self.env.company.employee_number_auto_generate and not self.employee_number:
            self.employee_number = self.env['ir.sequence'].next_by_code('employee.number') or ''
        if self.env.company.employee_approval_needed:
            self.joined_date = fields.Date.today()
        self.write({'active': True,'state':'approve'})

    def action_rejection(self):
        """Rejection mail will send to record created user. Capturing the reason also"""
        rejection_form = self.env.ref('centrics_hr.employee_profile_rejection_view_form')
        return {
            'name': _('Employee Rejection Reason'),
            'res_model': 'employee.profile.rejection',
            'view_mode': 'form',
            'views': [(rejection_form.id, 'form')],
            'view_id': rejection_form.id,
            'context': {
                'active_model': 'hr.employee',
                'active_ids': self.ids,
                'default_employee_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_reset_to_draft(self):
        """After Rejection this button will be visible"""
        self.state = 'draft'


