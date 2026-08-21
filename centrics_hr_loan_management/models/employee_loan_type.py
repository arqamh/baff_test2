from odoo import models, fields, api, exceptions, _


class EmployeeLoanType(models.Model):
    _name = 'employee.loan.type'
    _description = 'Employee Loan Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Loan Type", tracking=True)
    loan_sequence_prefix = fields.Char(string="Sequence Prefix", tracking=True, required=True)
    loan_sequence_id = fields.Many2one('ir.sequence', string="Loan Sequence", tracking=True)
    is_interest = fields.Boolean(string="With Interest ? ", tracking=True)
    loan_interest = fields.Float(string="Interest Rate", tracking=True)
    standard_number_of_installments = fields.Integer(string="Standard Number of Installments(Months)", tracking=True,
                                                     required=True, default=1)
    is_minimum_loan_amount = fields.Boolean(string="Minimum Loan Amount", tracking=True)
    is_maximum_loan_amount = fields.Boolean(string="Maximum Loan Amount", tracking=True)
    minimal_loan_amount = fields.Float(string="Minimal Loan Amount", tracking=True)
    maximal_loan_amount = fields.Float(string="Maximal Loan Amount", tracking=True)

    default_pay_journal_id = fields.Many2one('account.journal', string="Default Pay Journal", tracking=True)
    default_receivable_account_id = fields.Many2one('account.account', string="Default Receivable Account",
                                                    tracking=True)
    default_payable_account_id = fields.Many2one('account.account', string="Default Payable Account", tracking=True)
    default_interest_account_id = fields.Many2one('account.account', string="Default Interest Account", tracking=True)
    default_bank_cash_account_id = fields.Many2one(
        'account.account',
        string="Default Bank/Cash Account",
        tracking=True,
        domain=[('account_type', '=', 'asset_cash')]
    )

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(
        string='Active', default=True,
        help="If the active field is set to False, it will allow you to hide the loan type without removing it."
    )

    # Payroll related configurations
    is_enable_payroll_integration = fields.Boolean(string="Payroll Integration", compute='_compute_is_enable_payroll_integration', tracking=True)
    hr_salary_rule_id = fields.Many2one('hr.salary.rule', string="Salary Rule", tracking=True, help="Salary Rule for the loan type")
    hr_payslip_input_type_id = fields.Many2one('hr.payslip.input.type', string="Payslip Input Type", tracking=True, help="Payslip Input Type for the loan type")



    _sql_constraints = [
        ('loan_sequence_prefix_company_unique', 'unique(loan_sequence_prefix, company_id)',
         'The sequence prefix must be unique within the same company.')
    ]

    def _compute_is_enable_payroll_integration(self):
        for record in self:
            record.is_enable_payroll_integration = record.company_id.is_enable_payroll_integration
    
    def _check_minimal_loan_amount(self):
        """Check that minimal loan amount is valid if the boolean field is enabled."""
        for record in self:
            if record.is_minimum_loan_amount and record.minimal_loan_amount <= 0:
                raise exceptions.ValidationError(
                    _("Minimal loan amount must be set when 'Is Minimum Loan Amount' is enabled."))

    def _check_maximal_loan_amount(self):
        """Check that maximal loan amount is valid if the boolean field is enabled."""
        for record in self:
            if record.is_maximum_loan_amount and record.maximal_loan_amount <= 0:
                raise exceptions.ValidationError(
                    _("Maximal loan amount must be set when 'Is Maximum Loan Amount' is enabled."))
            if record.is_minimum_loan_amount and record.is_maximum_loan_amount and \
                    record.maximal_loan_amount < record.minimal_loan_amount:
                raise exceptions.ValidationError(
                    _("Maximal loan amount must not be less than the minimal loan amount."))

    @api.model
    def create(self, vals):
        """Override create to include validations."""
        record = super(EmployeeLoanType, self).create(vals)
        record._check_minimal_loan_amount()
        record._check_maximal_loan_amount()
        return record

    def write(self, vals):
        """Override write to include validations."""
        res = super(EmployeeLoanType, self).write(vals)
        self._check_minimal_loan_amount()
        self._check_maximal_loan_amount()
        return res

    def action_generate_loan_sequence(self):
        """
        Generates a loan sequence using the loan_sequence_prefix and assigns
        it to the loan_sequence_id field of the current record.
        """
        self.ensure_one()
        if self.loan_sequence_id:
            self.loan_sequence_id.unlink()

        sequence_values = {
            'name': f"{self.name}-{self.company_id.company_code}-Sequence",
            'code': f"{self._name}.{self.loan_sequence_prefix.replace(' ', '_')}.{self.company_id.company_code}",
            'prefix': f"{self.loan_sequence_prefix}/%(year)s/",
            'padding': 4,
            'company_id': self.company_id.id,
            'use_date_range': True,
            'number_next': 1,
            'number_increment': 1,
            'date_range_ids': [(0, 0, {'date_from': f'{fields.Date.today().year + i}-01-01',
                                       'date_to': f'{fields.Date.today().year + i}-12-31',
                                       'number_next_actual':1
                                       }) for i in range(5)],

        }
        sequence = self.env['ir.sequence'].create(sequence_values)
        self.loan_sequence_id = sequence

    def action_create_payslip_input_type(self):
        """
        Creates or retrieves a payslip input type specific to the current loan and returns an
        action dictionary for opening its form view.

        This method ensures that there is exactly one payslip input type associated
        with the current loan object. If no such payslip input type exists, it will be
        created automatically based on the loan's details (such as its name and
        sequence prefix). If the payslip input type already exists, it retrieves the
        details to return a corresponding action dictionary.

        Raises
        ------
        ValidationError
            If called on multiple records.

        Returns
        -------
        dict
            A dictionary representing the action to open the payslip input type's
            form view, which specifies the model, view mode, record ID, and target window.
        """
        self.ensure_one()
        if not self.hr_payslip_input_type_id:
            input_type_code = f'EMP_LOAN_{self.loan_sequence_prefix}_{self.company_id.company_code}'
            payslip_input_type = self.env['hr.payslip.input.type'].create({
                'name': self.name,
                'code': input_type_code.replace(" ", "_").lower()
            })
            self.hr_payslip_input_type_id = payslip_input_type.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.input.type',
            'view_mode': 'form',
            'res_id': self.hr_payslip_input_type_id.id,
            'target': 'current',
        }

    def action_create_salary_rule(self):
        """
        Validates and prepares context data to create a new Salary Rule linked to the loan type.
        """
        self.ensure_one()
        self._validate_salary_rule_creation()

        python_compute_code = self._generate_python_compute_code()
        rule_sequence = self._get_salary_rule_sequence()
        context = self._prepare_salary_rule_context(python_compute_code, rule_sequence)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Salary Rule',
            'view_mode': 'form',
            'res_model': 'hr.salary.rule',
            'target': 'new',
            'context': context,
        }

    def _validate_salary_rule_creation(self):
        """
        Validates the creation of salary rules associated with loan types.

        This method ensures that the necessary conditions are met for creating a salary
        rule. It checks the presence of a required pay slip input type and verifies
        that a salary rule is not already linked to the current loan type. If
        any of these conditions fail, an appropriate validation error is raised.

        Raises:
            ValidationError: If hr_payslip_input_type_id is not set.
            ValidationError: If hr_salary_rule_id is already linked.
        """

        if not self.hr_payslip_input_type_id:
            raise exceptions.ValidationError(
                _("Please create the Payslip Input Type before creating a Salary Rule.")
            )

        if self.hr_salary_rule_id:
            raise exceptions.ValidationError(
                _("A Salary Rule is already linked to this loan type.")
            )


    def _generate_python_compute_code(self):
        """Generate the Python compute code for the Salary Rule."""
        return f"result = inputs.{self.hr_payslip_input_type_id.code}.amount * -1 if inputs.{self.hr_payslip_input_type_id.code} else 0"

    def _get_salary_rule_sequence(self):
        """Retrieve the sequence for the Salary Rule, defaulting to 104 if none exist."""
        loan_rules = self.env['hr.salary.rule'].search([('is_loan_rule', '=', True)], limit=1)
        return loan_rules.sequence if loan_rules else 104

    def _prepare_salary_rule_context(self, python_compute_code, rule_sequence):
        """Prepare the context dictionary for creating a Salary Rule."""
        return {
            'default_name': self.name,
            'default_code': self.loan_sequence_prefix,
            'default_sequence': rule_sequence,
            'default_category_id': self.env.ref('hr_payroll.DED').id,
            'default_company_id': self.company_id.id,
            'default_appears_on_payslip': True,
            'default_amount_select': 'code',
            'default_amount_python_compute': python_compute_code,
            'loan_type_id': self.id,
            'default_is_loan_rule': True,
        }
