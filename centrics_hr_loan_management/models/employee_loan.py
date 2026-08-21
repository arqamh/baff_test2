import math
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo import models,fields,api,_,exceptions



LOAN_STATUS = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('approved', 'Approved'),
    ('paid', 'Paid'),
    ('in_recovery', 'In Recovery'),
    ('recovered', 'Recovered'),
    ('rejected', 'Rejected')
]

CALCULATION_TYPE = [
    ('equated_balance','Equated Balance'),
    ('reducing_balance', 'Reducing Balance')]

MONTHS = [
    ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),('7', 'July')
    ,('8', 'August'),('9', 'September'),('10', 'October'),('11', 'November'),('12', 'December')
]


class EmployeeLoan(models.Model):
    _name = 'employee.loan'
    _description = 'Employee Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_employee_id(self):
        """Retrieve the employee record linked to the current user."""
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        return employee.id if employee else False

    def _default_payroll_effective_month(self):
        """Get the default effective month as the next month from the current date."""
        next_month = (fields.Date.today().month % 12) + 1  # Calculates the next month (rolls from 12 to 1)
        return str(next_month)

    def get_journal_items(self, account_id, name, partner_id, amount, amount_type):
        """return journal item lines"""
        data = {
            'account_id': account_id,
            'name': name,
            'partner_id': partner_id,
            'credit': amount if amount_type == 'credit' else 0,  # if type is credit then amount is written else 0
            'debit': amount if amount_type == 'debit' else 0,  # if type is debit then amount is written else 0
        }
        return (0, 0, data)

    name = fields.Char(string="Loan Number", default="New", tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee_id, tracking=True)
    loan_type = fields.Many2one('employee.loan.type', string="Loan Type", tracking=True)
    interest_rate = fields.Float(string="Loan Interest", readonly=True, related='loan_type.loan_interest', store=True,
                                 tracking=True)
    is_minimum_loan_amount = fields.Boolean(string="Minimum Loan Amount", readonly=True,
                                            related='loan_type.is_minimum_loan_amount', store=True, tracking=True)
    is_maximum_loan_amount = fields.Boolean(string="Maximum Loan Amount", readonly=True,
                                            related='loan_type.is_maximum_loan_amount', store=True, tracking=True)
    minimal_loan_amount = fields.Float(string="Minimal Loan Amount", readonly=True,
                                       related='loan_type.minimal_loan_amount', store=True, tracking=True)
    maximal_loan_amount = fields.Float(string="Maximal Loan Amount", readonly=True,
                                       related='loan_type.maximal_loan_amount', store=True, tracking=True)
    loan_amount = fields.Float(string="Loan Amount", tracking=True)
    number_of_installments = fields.Integer(string="Number of Installments", required=True, tracking=True)
    calculation_type = fields.Selection(selection=CALCULATION_TYPE, string="Calculation Type",
                                        default='equated_balance', tracking=True)
    purpose = fields.Text(string="Purpose", required=True, tracking=True)
    staff_notes = fields.Text(string="Staff Notes", tracking=True)
    rejections_reason = fields.Text(string="Rejections Reasons", tracking=True)
    processed_amount = fields.Float(string="Processed Amount", tracking=True, related='loan_amount', store=True)
    is_skip_guarantor_validation = fields.Boolean(string="Skip Guarantor Validation", default=False, tracking=True)
    loan_status = fields.Selection(selection=LOAN_STATUS, string="Loan Status", default='draft', tracking=True)
    loan_requested_date = fields.Date(string="Loan Requested Date", tracking=True)
    loan_approved_date = fields.Date(string="Loan Approved Date", tracking=True)
    loan_rejected_date = fields.Date(string="Loan Rejected Date", tracking=True)
    loan_paid_date = fields.Date(string="Loan Paid Date", tracking=True)
    deduct_from_payroll = fields.Selection(selection=MONTHS, string="Deduct StartFrom",
                                           default=_default_payroll_effective_month,
                                           help="Deduction start from the selected month.", tracking=True)
    payroll_effective_month = fields.Selection(selection=MONTHS, string="Effective Month(Payroll)",
                                               default=_default_payroll_effective_month,
                                               help="Actual Payroll effective month.", tracking=True)
    employee_loan_installment_line_ids = fields.One2many('employee.loan.installment.line', 'employee_loan_id',
                                                         string="Loan Installments")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True,
                                 store=True, tracking=True)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True,)
    total_loan_amount = fields.Monetary(string="Total Loan Amount", compute="_compute_total_loan_amount", store=True,
                                        tracking=True, currency_field='company_currency_id')
    total_due_amount = fields.Monetary(string="Total Due Amount", compute="_compute_total_due_amount", store=True,
                                       tracking=True, currency_field='company_currency_id')
    paid_amount = fields.Monetary(string="Paid Amount", compute="_compute_paid_amounts", store=True, tracking=True,
                                  currency_field='company_currency_id')
    paid_interest_amount = fields.Monetary(string="Paid Interest Amount", compute="_compute_paid_amounts", store=True,
                                           tracking=True, currency_field='company_currency_id')
    paid_capital_amount = fields.Monetary(string="Paid Capital Amount", compute="_compute_paid_amounts", store=True,
                                          tracking=True, currency_field='company_currency_id')
    loan_guarantor_ids = fields.One2many('employee.loan.guarantor', 'employee_loan_id', string="Loan Guarantor")

    loan_stage_id = fields.Many2one('employee.loan.stage', string='Loan Stage', compute='_compute_loan_stage_id', inverse='_inverse_loan_stage_id', store=True)
    is_allow_print = fields.Boolean(string='Allow Print', related='loan_stage_id.allow_print', store=True)
    color = fields.Integer(string="Color Index")

    paid_entry_id = fields.Many2one('account.move', string="Paid Entry", readonly=True, copy=False)
    issued_user_id = fields.Many2one('res.users', string="Issued By", readonly=True, copy=False)

    loan_progress = fields.Float(string="Loan Progress (%)", compute='_compute_loan_progress', store=True)

    is_skip_default_journal = fields.Boolean(string="Skip Default Journal", default=False, tracking=True)
    loan_payment_journal_id = fields.Many2one('account.journal', string="Loan Payment Journal", copy=False)

    @api.depends('employee_loan_installment_line_ids.status', 'employee_loan_installment_line_ids.installment_amount')
    def _compute_total_due_amount(self):
        """
        Calculate the total due amount as the sum of 'draft' installment amounts.
        """
        for record in self:
            record.total_due_amount = sum(
                line.installment_amount - (line.paid_capital_amount + line.paid_interest_amount)
                for line in record.employee_loan_installment_line_ids
                if line.status == 'draft'
            )

    @api.depends('employee_loan_installment_line_ids.status', 'employee_loan_installment_line_ids.capital_amount',
                 'employee_loan_installment_line_ids.interest_amount')
    def _compute_paid_amounts(self):
        """
        Calculate the paid amount, paid capital, and paid interest from installment lines marked as 'paid'.
        """
        for record in self:
            installment_lines = record.employee_loan_installment_line_ids
            record.paid_amount = sum(line.paid_capital_amount + line.paid_interest_amount for line in installment_lines)
            record.paid_interest_amount = sum(line.paid_interest_amount for line in installment_lines)
            record.paid_capital_amount = sum(line.paid_capital_amount for line in installment_lines)

    @api.depends('loan_stage_id')
    def _compute_loan_progress(self):
        Stage = self.env['employee.loan.stage']
        all_stages = Stage.search([], order='sequence')
        total = len(all_stages)
        for record in self:
            if record.loan_stage_id:
                index = list(all_stages.ids).index(record.loan_stage_id.id) + 1
                record.loan_progress = round((index / total) * 100, 2)
            else:
                record.loan_progress = 0.0

    @api.depends('loan_status')
    def _compute_loan_stage_id(self):
        """Compute the loan stage based on the loan status."""
        stage_map = {
            'draft': 'Draft',
            'submitted': 'Submitted',
            'approved': 'Approved',
            'paid': 'Paid',
            'in_recovery': 'In Recovery',
            'recovered': 'Recovered',
            'rejected': 'Rejected',
        }
        for rec in self:
            name = stage_map.get(rec.loan_status)
            rec.loan_stage_id = self.env['employee.loan.stage'].search([('name', '=', name)], limit=1)

    @api.depends('employee_loan_installment_line_ids.installment_amount')
    def _compute_total_loan_amount(self):
        """
        Compute the total loan amount as the sum of all installment amounts.
        """
        for record in self:
            record.total_loan_amount = sum(
                line.installment_amount for line in record.employee_loan_installment_line_ids
            )

    def _inverse_loan_stage_id(self):
        # Map the loan stage name back to the loan status
        reverse_map = {
            'Draft': 'draft',
            'Submitted': 'submitted',
            'Approved': 'approved',
            'Paid': 'paid',
            'In Recovery': 'in_recovery',
            'Recovered': 'recovered',
            'Rejected': 'rejected',
        }
        for rec in self:
            if rec.loan_stage_id:
                # Update the loan status based on the loan stage
                rec.loan_status = reverse_map.get(rec.loan_stage_id.name.lower().capitalize(), 'draft')


    @api.onchange('loan_amount', 'is_minimum_loan_amount', 'is_maximum_loan_amount', 'minimal_loan_amount',
                  'maximal_loan_amount', 'employee_id')
    def _onchange_loan_amount(self):
        if self.loan_amount > 0:
            """Validate the loan amount against the minimal and maximal thresholds."""
            if self.is_minimum_loan_amount and self.loan_amount < self.minimal_loan_amount:
                return {
                    'warning': {
                        'title': _("Validation Error"),
                        'message': _("Loan amount cannot be less than the minimal loan amount.")
                    }
                }
            if self.is_maximum_loan_amount and self.loan_amount > self.maximal_loan_amount:
                return {
                    'warning': {
                        'title': _("Validation Error"),
                        'message': _("Loan amount cannot exceed the maximal loan amount.")
                    }
                }

            # Check if we should validate against basic salary
            if not self.is_maximum_loan_amount and self.company_id.use_basic_salary_as_max_loan and self.employee_id:
                # Get the employee's current contract
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('state', '=', 'open')
                ], limit=1, order='date_start desc')

                if contract and contract.wage:
                    if self.loan_amount > contract.wage:
                        return {
                            'warning': {
                                'title': _("Validation Error"),
                                'message': _("Loan amount cannot exceed the employee's basic salary (%.2f).") % contract.wage
                            }
                        }
                elif not contract:
                    return {
                        'warning': {
                            'title': _("Validation Warning"),
                            'message': _("No active contract found for the employee. Cannot validate against basic salary.")
                        }
                    }

    @api.onchange('loan_type')
    def _onchange_loan_type(self):
        """Retrieve the default number of installments when the loan type changes."""
        self.number_of_installments = self.loan_type.standard_number_of_installments if self.loan_type else 0

    def _validate_guarantors(self):
        """
        Validate guarantor rules.
        """
        # Check maximum guarantee loans
        if self.company_id.allow_max_guarantee_loans and self.company_id.max_guarantee_loans > 0:
            guarantor_employee_ids = [g.employee_id.id for g in self.loan_guarantor_ids]
            for guarantor_id in guarantor_employee_ids:
                guarantor_loans_count = self.env['employee.loan.guarantor'].search_count([
                    ('employee_id', '=', guarantor_id)
                ])
                if guarantor_loans_count > self.company_id.max_guarantee_loans:
                    raise exceptions.ValidationError(_(
                        f"Employee {self.env['hr.employee'].browse(guarantor_id).name} "
                        f"has guaranteed {guarantor_loans_count} loans, which exceeds the limit of "
                        f"{self.company_id.max_guarantee_loans} loans allowed."
                    ))

        # Check minimum guarantor requirements
        if self.company_id.min_guarantors_required and self.company_id.no_of_minimum_guarantors > 0:
            if len(self.loan_guarantor_ids) < self.company_id.no_of_minimum_guarantors:
                raise exceptions.ValidationError(_(
                    f"The loan requires at least {self.company_id.no_of_minimum_guarantors} guarantors. "
                    f"Please add more guarantors to proceed."
                ))

    def action_submit_loan(self):
        """Submit the loan, update the status to 'submitted', and notify the approver and the employee via email."""
        self.ensure_one()
        if not self.loan_type:
            raise exceptions.ValidationError(_("Loan Type is required to submit the loan."))
        if self.loan_amount <= 0:
            raise exceptions.ValidationError(_("Loan amount cannot be zero or negative."))
        if self.number_of_installments <= 0:
            raise exceptions.ValidationError(_("Number of installments cannot be zero or negative."))

        # Validate loan amount against minimum/maximum thresholds
        if self.is_minimum_loan_amount and self.loan_amount < self.minimal_loan_amount:
            raise exceptions.ValidationError(_("Loan amount cannot be less than the minimal loan amount."))

        if self.is_maximum_loan_amount and self.loan_amount > self.maximal_loan_amount:
            raise exceptions.ValidationError(_("Loan amount cannot exceed the maximal loan amount."))

        # Validate against basic salary if configured
        if not self.is_maximum_loan_amount and self.company_id.use_basic_salary_as_max_loan and self.employee_id:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1, order='date_start desc')

            if contract and contract.wage:
                if self.loan_amount > contract.wage:
                    raise exceptions.ValidationError(
                        _("Loan amount (%.2f) cannot exceed the employee's basic salary (%.2f).")
                        % (self.loan_amount, contract.wage)
                    )
            elif not contract:
                raise exceptions.ValidationError(
                    _("No active contract found for employee %s. Cannot validate loan amount against basic salary.")
                    % self.employee_id.name
                )

        self.loan_status = 'submitted'
        self.loan_requested_date = fields.Date.today()
        self.name = self.env['ir.sequence'].next_by_code(self.loan_type.loan_sequence_id.code) or 'New'

        employee_template = self.env.ref('centrics_hr_loan_management.hr_loan_management_mail_template_employee_request_submission')
        employee_template.send_mail(self.id, force_send=True)

        manager_group = self.env.ref('centrics_hr_loan_management.group_loan_manager')
        managers = manager_group.users
        manager_template = self.env.ref('centrics_hr_loan_management.hr_loan_management_mail_template_manager_approval')

        for user in managers:
            manager_template.with_context(manager_name=user.name).send_mail(
                self.id,
                force_send=True,
                email_values={'email_to': user.email})

    def action_reset_to_draft(self):
        """Reset the loan record to the draft stage, clearing all related dates."""
        self.ensure_one()
        self.loan_status = 'draft'

    def action_approve_loan(self):
        """
        Approves the loan by validating necessary conditions.

        This method ensures the current record is in single mode and validates whether 
        loan installment lines and guarantors are appropriately specified. If the validation 
        passes, it updates the loan status to 'approved' and sets the loan approval date 
        to the current date. Additionally, it includes a placeholder for the system to 
        send emails to the relevant parties.

        Parameters
        ----------
        self : Model
            The recordset being processed. Must contain exactly one record.

        Raises
        ------
        ValidationError
            If the loan installment lines are absent while trying to approve the loan.

        Notes
        -----
        This method only performs updates and validation checks. No email sending logic 
        has been implemented yet. See the TODO section in the comments for potential 
        future actions.
        """
        self.ensure_one()
        if not self.employee_loan_installment_line_ids:
            raise exceptions.ValidationError(_("Loan installment lines are required to approve the loan.Please click on 'Generate Installments' button to generate."))
        if not self.is_skip_guarantor_validation:
            self._validate_guarantors()
        self.loan_status = 'approved'
        self.loan_approved_date = fields.Date.today()

        employee_template = self.env.ref('centrics_hr_loan_management.hr_loan_management_mail_template_approved_loan_employee')
        employee_template.send_mail(self.id, force_send=True)

        loan_record = self.env['employee.loan'].search([('employee_id', '=', self.employee_id.id)])
        return self.env.ref('centrics_hr_loan_management.action_report_employee_loan').report_action(loan_record)

    def action_reject_loan(self):
        """Reject the loan by updating the status to 'rejected' and setting the rejected date. Notify the employee via email."""
        
        self.ensure_one()
        if not self.rejections_reason:
            raise exceptions.ValidationError(_("Rejections reason is required to reject the loan."))
        self.loan_status = 'rejected'
        self.loan_rejected_date = fields.Date.today()

        employee_template = self.env.ref('centrics_hr_loan_management.hr_loan_management_mail_template_rejected_loan_employee')
        employee_template.send_mail(self.id, force_send=True)

    def action_pay_loan(self):
        """Pay the loan by updating the status to 'paid' and setting the paid date."""
        self.ensure_one()

        journal_id = None
        bank_cash_account_id = None
        receivable_account_id = None


        # Validating required accounts
        if self.is_skip_default_journal:
            if self.loan_payment_journal_id:
                journal_id = self.loan_payment_journal_id
                if self.loan_payment_journal_id.default_account_id:
                    bank_cash_account_id = self.loan_payment_journal_id.default_account_id
                else:
                    raise exceptions.ValidationError(
                        _('Please select a default account for the paying journal.')
                    )
            else:
                raise exceptions.ValidationError(
                    _('Please select a default journal for the paying loan.')
                )
        else :
            if self.loan_type.default_pay_journal_id:
                journal_id = self.loan_type.default_pay_journal_id
            else:
                raise exceptions.ValidationError(
                    _('Please select a default journal for the loan type.')
                )
            if self.loan_type.default_bank_cash_account_id:
                bank_cash_account_id = self.loan_type.default_bank_cash_account_id
            else:
                raise exceptions.ValidationError(
                    _('Please select a default account for the Loan type.')
                )

        if not self.loan_type.default_receivable_account_id:
            raise exceptions.ValidationError(
                _("Please select a default receivable account for the Loan type."))
        else :
            receivable_account_id = self.loan_type.default_receivable_account_id

            journal_entry_vals = {
                'date': datetime.now().date(),
                'journal_id': journal_id.id,
                'ref': self.display_name,
                'company_id': self.company_id.id,
                'line_ids': []
            }

            journal_entry_vals['line_ids'].append(self.get_journal_items(
                bank_cash_account_id.id,
                self.display_name,
                self.employee_id.sudo().address_home_id.id,
                self.processed_amount,
                'credit'
            ))

            journal_entry_vals['line_ids'].append(self.get_journal_items(
                receivable_account_id.id,
                self.display_name,
                self.employee_id.sudo().address_home_id.id,
                self.processed_amount,
                'debit'
            ))

            journal_entry = self.env['account.move'].create(journal_entry_vals)
            journal_entry.action_post()

            self.paid_entry_id = journal_entry.id
            self.issued_user_id = self._uid

        self.loan_status = 'paid'
        self.loan_paid_date = fields.Date.today()

        employee_template = self.env.ref('centrics_hr_loan_management.hr_loan_management_mail_template_loan_granted_employee')
        employee_template.send_mail(self.id, force_send=True)

    def action_generate_loan_installment_lines(self):
        """Generate loan installment lines based on the loan amount and number of installments."""
        self.ensure_one()
        self.employee_loan_installment_line_ids.unlink()
        if self.processed_amount <= 0:
            raise exceptions.ValidationError(_("Loan Processing amount cannot be zero."))
        if self.number_of_installments <= 0:
            raise exceptions.ValidationError(_("Number of installments cannot be zero."))

        # Determine the starting year based on deduct_from_payroll
        today = fields.Date.today()
        starting_month_int = int(self.deduct_from_payroll)
        current_month = today.month
        current_year = today.year

        # If the effective month has already passed this year, start from next year
        if starting_month_int < current_month:
            starting_year = current_year + 1
        else:
            starting_year = current_year

        if self.calculation_type == 'equated_balance':
            loan_amount  =  self.processed_amount
            loan_period  = self.number_of_installments
            loan_interest = self.interest_rate
            starting_month = self.deduct_from_payroll
            if loan_interest > 0:
                # installment_value = loan_amount * (loan_interest / 100) / (1 - (1 + loan_interest / 100) ** (-loan_period))
                installment_value = float((float(loan_amount) * (float(float(loan_interest) / float((100 * 12)))))) / float(
                    (1 - (math.pow((1 + (float(loan_interest) / float((100 * 12)))), -loan_period))))
                running_balance = loan_amount
                sum_of_capital = 0
                sum_of_interest = 0
                for count in range(loan_period):
                    # Calculate the installment date starting from payroll_effective_month and starting_year
                    payroll_effective_date = datetime(starting_year, starting_month_int, 1).date() + relativedelta(months=count)
                    related_month = str(payroll_effective_date.month)
                    interest_value = (running_balance * loan_interest) / (12 * 100)
                    capital_value = installment_value - interest_value
                    running_balance -= capital_value
                    sum_of_capital += capital_value
                    sum_of_interest += interest_value
                    ref_number = "LO/" + str(self.loan_type.loan_sequence_prefix) + "/" + str(count + 1).zfill(4)
                    self.env['employee.loan.installment.line'].create({
                        'employee_loan_id': self.id,
                        'employee_id': self.employee_id.id,
                        'installment_ref_number': ref_number,
                        'year': payroll_effective_date.year,
                        'month': related_month,
                        'capital_amount' : capital_value,
                        'interest_amount': interest_value,
                        'installment_amount': installment_value,
                        'running_balance': running_balance,
                        'status': 'draft'
                    })

                    count += 1
            else:
                installment_value = float(loan_amount) / float(loan_period)
                running_balance = loan_amount
                sum_of_capital = 0
                sum_of_interest = 0
                for count in range(loan_period):
                    # Calculate the installment date starting from payroll_effective_month and starting_year
                    payroll_effective_date = datetime(starting_year, starting_month_int, 1).date() + relativedelta(months=count)
                    related_month = str(payroll_effective_date.month)
                    interest_value = 0
                    capital_value = installment_value
                    running_balance -= capital_value
                    sum_of_capital += capital_value
                    sum_of_interest += interest_value
                    ref_number = "LO/" + str(self.loan_type.loan_sequence_prefix) + "/" + str(count + 1).zfill(4)

                    self.env['employee.loan.installment.line'].create({
                        'employee_loan_id': self.id,
                        'employee_id': self.employee_id.id,
                        'installment_ref_number': ref_number,
                        'year': payroll_effective_date.year,
                        'month': related_month,
                        'capital_amount': capital_value,
                        'interest_amount': interest_value,
                        'installment_amount': installment_value,
                        'running_balance': running_balance,
                        'status': 'draft'
                    })
        else:
            loan_amount = self.processed_amount
            period = self.number_of_installments
            interest = self.interest_rate
            starting_month = self.deduct_from_payroll

            capital_value = loan_amount / period
            running_balance = loan_amount
            sum_of_interest = 0
            sum_of_capital = 0

            for count in range(period):
                # Calculate the installment date starting from payroll_effective_month and starting_year
                payroll_effective_date = datetime(starting_year, starting_month_int, 1).date() + relativedelta(months=count)
                related_month = str(payroll_effective_date.month)
                interest_value = (running_balance * interest) / (12 * 100)
                running_balance -= capital_value
                sum_of_capital += capital_value
                sum_of_interest += interest_value
                ref_number = "LO/" + str(self.loan_type.loan_sequence_prefix) + "/" + str(count + 1).zfill(4)
                self.env['employee.loan.installment.line'].create({
                    'employee_loan_id': self.id,
                    'employee_id': self.employee_id.id,
                    'installment_ref_number': ref_number,
                    'year': payroll_effective_date.year,
                    'month': related_month,
                    'capital_amount': capital_value,
                    'interest_amount': interest_value,
                    'installment_amount': capital_value,
                    'running_balance': running_balance,
                    'status': 'draft'
                })
                count += 1

    @api.model
    def create(self, vals):
        """
        Override the create method to include guarantor validation.
        """
        guarantor_ids = vals.get('loan_guarantor_ids', [])
        unique_guarantors = {guarantor[2]['employee_id'] for guarantor in guarantor_ids if guarantor[0] != 2}
        if len(unique_guarantors) != len(guarantor_ids):
            raise exceptions.ValidationError(
                _("The same employee cannot be added as a guarantor more than once for the same loan."))
        loan = super(EmployeeLoan, self).create(vals)
        return loan

    def write(self, vals):
        """
        Override the write method to include guarantor validation when guarantors are updated.
        """
        if 'loan_guarantor_ids' in vals:
            guarantor_ids = vals.get('loan_guarantor_ids', [])

            # Ensure all guarantors are valid before accessing their indices
            updated_guarantors = {
                guarantor[2]['employee_id']
                for guarantor in guarantor_ids
                if isinstance(guarantor, (list, tuple)) and len(guarantor) > 2 and isinstance(guarantor[2],
                                                                                              dict) and 'employee_id' in
                   guarantor[2] and guarantor[0] != 2
            }

            loan_guarantor_ids = {guarantor.employee_id.id for guarantor in self.loan_guarantor_ids}
            all_guarantors = loan_guarantor_ids.union(updated_guarantors)

            if len(all_guarantors) != len(loan_guarantor_ids) + len(updated_guarantors):
                raise exceptions.ValidationError(
                    _("The same employee cannot be added as a guarantor more than once for the same loan."))

        res = super(EmployeeLoan, self).write(vals)
        return res

    def action_print_loan(self):
        """Print the loan document."""
        self.ensure_one()
        return self.env.ref('centrics_hr_loan_management.action_report_employee_loan').report_action(self)

