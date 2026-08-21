from datetime import date,datetime,timedelta
from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError


MONTHS = [
    ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
    ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')]


class HrAdvanceRequest(models.Model):
    _name = 'hr.advance.request'
    _description = 'Hr Advance Request'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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

    name = fields.Char(default="New", tracking=True,
                       help="The unique name of the advance request, auto-generated or user-defined.")
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True,
                                  help="The employee requesting the advance.")
    contract_id = fields.Many2one('hr.contract', compute='_compute_contract_id', tracking=True,
                                  help="The contract associated with the employee." , store=True)
    type_id = fields.Many2one('advance.type', required=True, string="Advance Type", tracking=True,
                              help="The type of advance being requested.")

    requested_amount = fields.Monetary(string="Requested Amount", required=True, default=0.0, tracking=True,
                                       help="The amount of money requested as an advance.")
    allowed_amount = fields.Monetary(compute='_compute_allowed_amount', tracking=True, store=True,
                                     string="Allowed Amount",
                                     help="The maximum amount of money the employee is allowed to request.")
    remaining_balance = fields.Monetary(compute='_compute_remaining_balance', tracking=True, store=True,
                                        string="Remaining Balance",
                                        help="The remaining balance of the employee's advance request.")
    currency_id = fields.Many2one('res.currency', related='type_id.currency_id', tracking=True, store=True,
                                  string="Currency",
                                  help="The currency applicable to the advance request.")
    repayment_method = fields.Selection([
        ('current_payroll', 'Current Month Payroll'),
        ('next_month_payroll', 'Next Month Payroll'),
        ('installments', 'Installments')], string="Repayment Method", tracking=True, default='current_payroll',
        required=1)
    no_of_installments = fields.Integer(string="No. of Installments", tracking=True,
                                        help="The number of installments for the advance.")
    advance_expected_date = fields.Date(
        string="Expected Date",
        tracking=True,
        required=1,
        default=lambda self: date.today() + timedelta(days=10),
        help="The expected date on which the advance will be paid."
    )

    processed_amount = fields.Monetary(string="Processed Amount", tracking=True,
                                       help="The amount of money processed for the advance.")

    effective_year = fields.Integer(string="Year", tracking=True, default=date.today().year)
    effective_month = fields.Selection(selection=MONTHS, string="Month")

    is_allowance = fields.Boolean(string="Is Allowance", default=False, tracking=True)
    is_lines_generated = fields.Boolean(string="Is Lines Generated", default=False, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid')
    ], default='draft', tracking=True, help="The current state of the advance request.")
    submitted_date = fields.Datetime(string="Submitted Date", tracking=True,
                                     help="The date and time when the advance was submitted.")
    submitted_user_id = fields.Many2one('res.users', string="Submitted By", tracking=True,
                                        help="The user who submitted the request.")
    approved_date = fields.Datetime(string="Approved Date", tracking=True,
                                    help="The date and time when the advance was approved.")
    approved_user_id = fields.Many2one('res.users', string="Approved By", tracking=True,
                                       help="The user who approved the request.")
    rejected_date = fields.Datetime(string="Rejected Date", tracking=True,
                                    help="The date and time when the advance was rejected.")
    rejected_user_id = fields.Many2one('res.users', string="Rejected By", tracking=True,
                                       help="The user who rejected the request.")
    paid_date = fields.Datetime(string="Paid Date", tracking=True,
                                help="The date and time when the advance was marked as paid.")
    paid_user_id = fields.Many2one('res.users', string="Paid By", tracking=True,
                                   help="The user who marked the request as paid.")
    notes = fields.Text(tracking=True, help="Additional observations or notes for the advance request.")
    company_id = fields.Many2one('res.company', related='employee_id.company_id', string="Company",
                                 store=True, readonly=True, tracking=True)

    advance_installment_line_ids = fields.One2many('advance.installment.line', 'advance_request_id', string="Installments")

    paid_journal_entry_id = fields.Many2one('account.move', string="Journal Entry")
    returned_journal_entry_id = fields.Many2one('account.move', string="Return Journal Entry")

    @api.onchange('advance_expected_date')
    def onchange_advance_expected_date(self):
        """
        Prevent the user from setting the advance_expected_date to a past date.
        """
        if self.advance_expected_date and self.advance_expected_date < date.today():
            raise ValidationError("The 'Expected Date' cannot be a past date.")

    @api.depends('requested_amount','type_id')
    def _compute_remaining_balance(self):
        for record in self:
            allowed_amount = record.allowed_amount
            valid_time_period = record.type_id.time_period
            to_month = datetime.now().month
            from_month = datetime.now().month - valid_time_period

            # Calculate the sum of installment_amount for the defined criteria
            pending_installment_ids = self.env['advance.installment.line'].search([
                ('advance_request_id.employee_id', '=', record.employee_id.id),
                ('status', '=', 'draft'),
                ('advance_request_id.type_id', '=', record.type_id.id),
            ])
            pending_installment_sum = 0
            if pending_installment_ids:
                pending_installment_sum = sum(pending_installment_ids.filtered(
                    lambda line: from_month <= int(line.month) <= to_month
                ).mapped('installment_amount'))

            record.remaining_balance = allowed_amount - pending_installment_sum
            if allowed_amount - pending_installment_sum < record.requested_amount:
                record.processed_amount = allowed_amount - pending_installment_sum
            else:
                record.processed_amount = record.requested_amount

    @api.depends('employee_id')
    def _compute_contract_id(self):
        """
           This computation uses the Odoo ORM method `search` to find a single corresponding
           contract based on the conditions ['employee_id', '=', rec.employee_id.id] and
           ['state', '=', 'open']. Only the first matching contract is returned due to the `limit=1`
           constraint. If no active contract is found, a ValidationError is raised.
        """
        for rec in self:
            rec.contract_id = self.env['hr.contract'].search(
                [('employee_id', '=', rec.employee_id.id), ('state', '=', 'open')],
                limit=1) if rec.employee_id else False
            if not rec.contract_id and rec.employee_id:
                raise ValidationError(
                    "To process advance requests, the employee must have an active running contract."
                )

    @api.depends('type_id', 'employee_id', 'contract_id')
    def _compute_allowed_amount(self):
        """
        Computes the allowed amount for each record based on the type of calculation method and related dependencies. The
        computed value is stored in the `allowed_amount` field of the record.

        The computation logic depends on the specified calculation method in the `type_id` field. For fixed amounts, the
        predefined fixed amount is applied. For percentage-based calculations, the amount is calculated based on the
        employee's wage and the configured percentage. For Python-based calculations, custom Python code is evaluated
        using context variables.
        """
        for rec in self:
            if rec.type_id:
                if rec.type_id.calculation_method == 'fixed':
                    rec.allowed_amount = rec.type_id.fixed_amount

                elif rec.type_id.calculation_method == 'percentage':
                    if rec.contract_id.wage:
                        rec.allowed_amount = (rec.contract_id.wage * rec.type_id.percentage_of_wage) / 100.0
                    else:
                        rec.allowed_amount = 0.0

                elif rec.type_id.calculation_method == 'python':
                    localdict = {
                        'employee': rec.employee_id,
                        'contract': rec.contract_id,
                        'wage': rec.contract_id.wage,
                        'env': self.env,
                    }
                    try:
                        rec.allowed_amount = float(safe_eval(rec.type_id.python_code, localdict))
                    except Exception:
                        rec.allowed_amount = 0.0
                elif rec.type_id.calculation_method == 'from_contract':
                    if rec.contract_id:
                        limit_line = self.env['hr.contract.advance.limit.line'].search([('contract_id', '=', rec.contract_id.id), ('advance_type_id', '=', rec.type_id.id)], limit=1)
                        if limit_line:
                            rec.allowed_amount = limit_line.maximum_amount
                        else:
                            rec.allowed_amount = 0.0
                    else:
                        rec.allowed_amount = 0.0
            else:
                rec.allowed_amount = 0.0

    def action_submit(self):
        """
        The method validates the requested amount to ensure it is greater than zero and does not
        exceed the allowed amount. Upon successful validation, the record's state is updated to
        'submitted', and the submission date and user are logged. An email notification is sent
        to the employee using a predefined template.
        """
        for rec in self:
            if rec.requested_amount == 0:
                raise ValidationError("Requested amount cannot be 0.")
            if rec.requested_amount > rec.remaining_balance:
                raise ValidationError("Requested amount cannot be greater than the remaining balance.")
            rec.state = 'submitted'
            rec.submitted_date = fields.Datetime.now()
            rec.submitted_user_id = self.env.user
            rec.effective_month = str(int(date.today().strftime('%m')))
            rec.effective_year = date.today().strftime('%Y')

            employee_template = self.env.ref(
                'centrics_hr_advance_management.centrics_hr_advance_management_mail_template_employee_request_submission')
            employee_template.send_mail(self.id, force_send=True)

    def action_approve(self):
        """
        Updates the state of a record to 'approved' and assigns approval-related details.

        For each record in the recordset, this method sets the state to 'approved', updates the
        approval date to the current datetime, and assigns the currently logged-in user as
        the approver.

        """
        for rec in self:
            rec.state = 'approved'
            rec.approved_date = fields.Datetime.now()
            rec.approved_user_id = self.env.user

    def action_reject(self):
        """
        Sets the state of a record to 'rejected', updates the rejection date to the
        current datetime, and records the user responsible for the rejection.

        This method modifies the records in-place. The state and rejection-related
        fields are updated with the corresponding values when this method is
        called.
        """
        for rec in self:
            rec.state = 'rejected'
            rec.rejected_date = fields.Datetime.now()
            rec.rejected_user_id = self.env.user

    def action_paid(self):
        """
        Executes the process of marking an advance as paid, creating and posting journal entries, and updating relevant
        records and statuses within the system. The method ensures that all required configurations, such as journal,
        credit account, and debit account mappings, are properly set for the corresponding advance type. If the process
        is related to an allowance, additional accounts are validated accordingly. It creates accounting entries and
        updates the state of the advance and its related records.
        """
        self.ensure_one()
        journal_id = None
        credit_account_id = None
        debit_account_id = None

        if self.type_id.journal_id:
            journal_id = self.type_id.journal_id.id
        else:
            raise ValidationError(f"Please map a journal for the advance type: {self.type_id.name}")

        if self.type_id.credit_account_id:
            credit_account_id = self.type_id.credit_account_id.id
        else:
            raise ValidationError(f"Please map a credit account for the advance type: {self.type_id.name}")

        if self.type_id.debit_account_id:
            debit_account_id = self.type_id.debit_account_id.id
        else:
            raise ValidationError(f"Please map a debit account for the advance type: {self.type_id.name}")

        if self.is_allowance:
            if self.type_id.allowance_credit_account_id:
                credit_account_id = self.type_id.allowance_credit_account_id.id
            else:
                raise ValidationError(f"Please map a credit account for the advance type: {self.type_id.name}")

            if self.type_id.allowance_debit_account_id:
                debit_account_id = self.type_id.allowance_debit_account_id.id
            else:
                raise ValidationError(f"Please map a debit account for the advance type: {self.type_id.name}")

        journal_entry_vals = {
            'date': datetime.now().date(),
            'journal_id': journal_id,
            'ref': self.display_name,
            'company_id': self.company_id.id,
            'line_ids': []
        }

        journal_entry_vals['line_ids'].append(self.get_journal_items(
            credit_account_id,
            self.display_name,
            self.employee_id.sudo().address_home_id.id,
            self.processed_amount,
            'credit'
        ))

        journal_entry_vals['line_ids'].append(self.get_journal_items(
            debit_account_id,
            self.display_name,
            self.employee_id.sudo().address_home_id.id,
            self.processed_amount,
            'debit'
        ))

        journal_entry = self.env['account.move'].create(journal_entry_vals)
        journal_entry.action_post()

        if self.paid_journal_entry_id:
            self.paid_journal_entry_id.button_draft()
            self.paid_journal_entry_id.button_cancel()

        self.paid_journal_entry_id = journal_entry.id

        self.state = 'paid'
        self.paid_date = fields.Datetime.now()
        self.paid_user_id = self.env.user

        if self.is_allowance:
            # Update all installment lines' status to 'paid'
            self.advance_installment_line_ids.write({'status': 'paid'})



    def action_generate_installment(self):
        """
        Generates and manages installment lines for an advance request based on the specified repayment method.

        This method handles the creation of installment records in the `advance.installment.line` model. It first
        removes any existing installment lines associated with the advance request. Depending on the `repayment_method`
        of the advance request, it creates new installment lines with the appropriate configuration. The method supports
        three repayment methods: `current_payroll`, `next_month_payroll`, and `installments`. Installments can be evenly
        distributed over multiple months if specified.

        This function assumes that models such as `advance.installment.line` and fields including
        `repayment_method`, `requested_amount`, and `no_of_installments` are correctly configured in the environment.
        """
        self.ensure_one()
        self.env['advance.installment.line'].search([('advance_request_id', '=', self.id)]).unlink()
        if self.repayment_method == 'current_payroll':
            self.env['advance.installment.line'].create({
                'advance_request_id': self.id,
                'year': date.today().year,
                'month': str(int(date.today().strftime('%m'))),
                'installment_amount': self.requested_amount,
                'status': 'draft'
            })
            self.is_lines_generated = True
        elif self.repayment_method == 'next_month_payroll':
            self.env['advance.installment.line'].create({
                'advance_request_id': self.id,
                'year': date.today().year,
                'month': str(int((date.today().month + 1).strftime('%m'))),
                'installment_amount': self.requested_amount,
                'status': 'draft'
            })
            self.is_lines_generated = True
        elif self.repayment_method == 'installments':
            if self.no_of_installments > 0:
                for i in range(int(date.today().strftime('%m')), int(date.today().strftime('%m')) +self.no_of_installments):
                    self.env['advance.installment.line'].create({
                        'advance_request_id': self.id,
                        'year': date.today().year,
                        'month': str(i),
                        'installment_amount': self.requested_amount / self.no_of_installments,
                        'status': 'draft'
                    })
            self.is_lines_generated = True

    def action_reset_to_draft(self):
        """
        Resets the state of the object to 'draft' and clears all associated date
        and user fields. This method ensures that only one record is processed
        at a time by applying a condition, and updates the state and relevant
        fields to remove any previously set data about submission, approval,
        rejection, or payment.

        Resets the following fields:
        - State is changed to 'draft'.
        - Submission date and user ID.
        - Approval date and user ID.
        - Rejection date and user ID.
        - Payment date.

        Remove all installment lines.

        """
        self.ensure_one()
        self.advance_installment_line_ids.unlink()
        self.is_lines_generated = False
        self.write({
            'state': 'draft',
            'submitted_date': False,
            'submitted_user_id': False,
            'approved_date': False,
            'approved_user_id': False,
            'rejected_date': False,
            'rejected_user_id': False,
            'paid_date': False,
        })

    def action_return(self):
        """
        Generates a return journal entry for the paid entry, effectively reversing the paid journal entry.
        """
        self.ensure_one()

        journal_id = None

        if not self.paid_journal_entry_id:
            raise ValidationError("No paid journal entry exists to return.")

        if self.type_id.journal_id:
            journal_id = self.type_id.journal_id.id
        else:
            raise ValidationError(f"Please map a journal for the advance type: {self.type_id.name}")


        journal_entry_vals = {
            'date': datetime.now().date(),
            'journal_id': journal_id,
            'ref': f"Return for {self.display_name}",
            'company_id': self.company_id.id,
            'line_ids': []
        }

        for line in self.paid_journal_entry_id.line_ids:
            journal_entry_vals['line_ids'].append((0, 0, {
                'account_id': line.account_id.id,
                'name': f"Return: {line.name}",
                'partner_id': line.partner_id.id,
                'credit': line.debit,
                'debit': line.credit,
            }))

        journal_entry = self.env['account.move'].create(journal_entry_vals)
        journal_entry.action_post()

        self.returned_journal_entry_id = journal_entry.id

    @api.model
    def create(self, vals):
        """
        Creates a new record for the HR Advance Request model while ensuring a unique
        sequence for the 'name' field. If the 'name' field in the provided values (`vals`)
        is 'New', the sequence is either fetched or created to generate a unique name.

        """
        if vals.get('name', "New") == "New":
            # Fetch or create the sequence
            vals['name'] = self.env['ir.sequence'].next_by_code(self.type_id.advance_sequence_id.code) or 'New'
        return super(HrAdvanceRequest, self).create(vals)
