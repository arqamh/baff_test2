from odoo import models,fields,api,_
from odoo.exceptions import ValidationError


class AdvanceType(models.Model):
    _name = 'advance.type'
    _description = 'Advance Type'

    @api.constrains('name', 'description', 'calculation_method', 'fixed_amount', 'percentage_of_wage', 'python_code',
                    'currency_id', 'time_period', 'journal_id', 'debit_account_id', 'credit_account_id',
                    'allowance_debit_account_id', 'allowance_credit_account_id')
    def _check_no_edit_if_related_requests_exist(self):
        """
            Validates that fields of an advance type record are not editable if there are related advance requests
            in states 'submitted' or 'approved'.

            This constraint ensures data integrity by preventing modifications to advance types that are already
            linked to processed advance requests in specific states.

            Constraints:
                'name', 'description', 'calculation_method', 'fixed_amount', 'percentage_of_wage', 'python_code',
                'currency_id', 'time_period', 'journal_id', 'debit_account_id', 'credit_account_id',
                'allowance_debit_account_id', 'allowance_credit_account_id'

            Parameters:
                None

            Raises:
                ValidationError: If any related advance requests in state 'submitted' or 'approved' are found for the
                advance type being edited.
        """
        for record in self:
            related_requests = self.env['hr.advance.request'].search(
                [('type_id', '=', record.id), ('state', 'in', ['submitted', 'approved'])])
            if related_requests:
                raise ValidationError(
                    _("You cannot edit an advance type that is linked to processed advance requests in 'submitted' or 'approved' state."))

    @api.ondelete(at_uninstall=False)
    def _check_no_delete_if_related_requests_exist(self):
        """
            Ensures that the record cannot be deleted if there are related advance requests
            in a 'submitted' or 'approved' state. This constraint is applied to prevent
            unintentional removal of advance types that are referenced by active requests.
        """
        for record in self:
            related_requests = self.env['hr.advance.request'].search(
                [('type_id', '=', record.id), ('state', 'in', ['submitted', 'approved'])])
            if related_requests:
                raise ValidationError(
                    _("You cannot delete an advance type that is linked to processed advance requests in 'submitted' or 'approved' state."))

    name = fields.Char(string="Advance Type")
    description = fields.Text(string="Description")
    advance_sequence_prefix = fields.Char(string="Sequence Prefix", required=True)
    advance_sequence_id = fields.Many2one('ir.sequence', string="Advance Sequence")
    calculation_method = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Wage'),
        ('from_contract', 'From Contract'),
        ('python', 'Python Code'),
    ], default='fixed')
    fixed_amount = fields.Monetary(string="Fixed Amount")
    percentage_of_wage = fields.Float(string="Percentage (%)")
    python_code = fields.Text(string="Python Code")
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)

    time_period = fields.Integer(string="Time Period(Months)", help = "Limit Validated for the Time Period in Months", default=1)

    journal_id = fields.Many2one('account.journal', string="Journal")
    debit_account_id = fields.Many2one('account.account', string="Debit Account")
    credit_account_id = fields.Many2one('account.account', string="Credit Account")

    allowance_debit_account_id = fields.Many2one('account.account', string="Allowance Debit Account")
    allowance_credit_account_id = fields.Many2one('account.account', string="Allowance Credit Account")

    # Payroll Configurations# Payroll related configurations
    enable_payroll_integration = fields.Boolean(string="Payroll Integration", compute='_compute_enable_payroll_integration', tracking=True)
    hr_salary_rule_id = fields.Many2one('hr.salary.rule', string="Salary Rule", tracking=True, help="Salary Rule for the loan type")
    hr_payslip_input_type_id = fields.Many2one('hr.payslip.input.type', string="Payslip Input Type", tracking=True, help="Payslip Input Type for the loan type")
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    def _compute_enable_payroll_integration(self):
        for record in self:
            record.enable_payroll_integration = self.env.company.enable_payroll_integration

    def action_generate_advance_sequence(self):
        self.ensure_one()
        if self.advance_sequence_id:
            self.advance_sequence_id.unlink()

        sequence_values = {
            'name': f"{self.name}-{self.company_id.company_code}-Sequence",
            'code': f"{self._name}.{self.advance_sequence_prefix.replace(' ', '_')}.{self.company_id.company_code}",
            'prefix': f"{self.advance_sequence_prefix}/%(year)s/",
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
        self.advance_sequence_id = sequence

    def action_create_hr_payslip_input_type(self):
        self.ensure_one()
        if not self.hr_payslip_input_type_id:
            payslip_input_type = self.env['hr.payslip.input.type'].create({
                'name': self.name,
                'code': f'EMP_ADV_{self.advance_sequence_prefix.replace(" ", "_")}_{self.company_id.company_code}'
            })
            self.hr_payslip_input_type_id = payslip_input_type.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.input.type',
            'view_mode': 'form',
            'res_id': self.hr_payslip_input_type_id.id,
            'target': 'current',
        }

    def _validate_salary_rule_creation(self):
        """Validate that Payslip Input Type exists before creating a Salary Rule."""
        if not self.hr_payslip_input_type_id:
            raise ValidationError(
                _("Please create the Payslip Input Type before creating a Salary Rule.")
            )

    def _generate_python_compute_code(self):
        """Generate the Python compute code for the Salary Rule."""
        return f"result = inputs.{self.hr_payslip_input_type_id.code}.amount * -1 if inputs.{self.hr_payslip_input_type_id.code}.amount < 0 "

    def _get_salary_rule_sequence(self):
        """Retrieve the sequence for the Salary Rule, defaulting to 104 if none exist."""
        advance_rules = self.env['hr.salary.rule'].search([('is_advance_rule', '=', True)], limit=1)
        return advance_rules.sequence if advance_rules else 120

    def _prepare_salary_rule_context(self, python_compute_code, rule_sequence):
        return {
            'default_name': self.name,
            'default_code': self.advance_sequence_prefix,
            'default_sequence': rule_sequence,
            'default_category_id': self.env.ref('hr_payroll.DED').id,
            'default_company_id': self.company_id.id,
            'default_appears_on_payslip': True,
            'default_amount_select': 'code',
            'default_amount_python_compute': python_compute_code,
            'advance_type_id': self.id,
            'default_is_advance_rule': True,
        }


    def action_create_hr_salary_rule(self):
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

