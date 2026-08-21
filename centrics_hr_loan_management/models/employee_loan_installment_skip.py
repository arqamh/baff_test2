from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions


class EmployeeLoanInstallmentSkip(models.Model):
    _name = "employee.loan.installment.skip"
    _description = "Employee Loan Installment Skip"
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", tracking=True, readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', help="Employee", required=True, tracking=True, index=True)
    employee_loan_id = fields.Many2one(
        'employee.loan',
        help="Employee Loan",
        required=True,
        tracking=True,
        index=True
    )
    installment_id = fields.Many2one(
        'employee.loan.installment.line',
        string="Installment",
        required=True,
        ondelete='cascade',
        tracking=True)
    skip_reason = fields.Text(string="Reason", required=True, tracking=True,
                              help="Reason for skipping the loan installment.")
    skip_date = fields.Date(string="Skipped On", default=fields.Date.context_today, tracking=True)
    skip_type = fields.Selection([
        ('add_at_end', 'Add at End'),
        ('duplicate_next', 'Duplicate Next Month')],
        string="Skip Method",
        required=True,
        tracking=True)
    created_by = fields.Many2one(
        'res.users',
        string="Created By",
        default=lambda self: self.env.user,
        tracking=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved')],
        string="Status",
        required=True,
        default='draft',
        tracking=True,
        help="Current approval status of the skipped installment record.")
    approved_by = fields.Many2one(
        'res.users',
        string="Approved By",
        readonly=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
        store=True,
        tracking=True
    )

    @api.model
    def create(self, vals):
        """
        Override the create method to assign a sequence to the name field.
        """
        if vals.get('name', 'New') == 'New':
            seq_code = 'employee.loan.installment.skip.sequence'
            seq_name = 'Employee Loan Installment Skip Sequence'

            # Create sequence if it doesn't exist
            sequence_obj = self.env['ir.sequence'].sudo()
            sequence = sequence_obj.search([('code', '=', seq_code)], limit=1)
            if not sequence:
                sequence = sequence_obj.create({
                    'name': seq_name,
                    'code': seq_code,
                    'prefix': 'ELSK/%(year)s/',
                    'padding': 5,
                    'number_next': 1,
                    'number_increment': 1,
                })

            # Assign the next sequence number to the name field
            vals['name'] = sequence.next_by_id()

        return super(EmployeeLoanInstallmentSkip, self).create(vals)

    def action_submit_for_approval(self):
        # """
        # Submit the loan installment skip record for approval.
        # If auto-approval is enabled in configurations, directly move to approved status.
        # """
        # self.ensure_one()
        # config_model = self.env['res.config.settings']
        # auto_approval = config_model.sudo().get_values().get('is_skip_installment_approval', False)
        #
        # for record in self:
        #     if auto_approval:
        #         record.status = 'approved'
        #         record.approved_by = self.env.user
        #     else:
        #         record.status = 'pending'
        pass

    def action_approve(self):
        # self.ensure_one()
        # if self.installment_id.status != 'draft':
        #     raise exceptions.UserError(_("Only draft installments can be skipped."))
        #
        # loan = self.employee_loan_id
        # if loan.calculation_type != 'equated_balance':
        #     raise exceptions.UserError(_("Skipping currently only supports 'Equated Balance' type loans."))
        #
        # # Mark current line skipped and log
        # self.installment_id.status = 'skipped'
        #
        # # Collect all non-paid, non-skipped lines
        # future_lines = loan.employee_loan_installment_line_ids.filtered(
        #     lambda l: l.status == 'draft').sorted(key=lambda l: (l.year, int(l.month)))
        #
        # if not future_lines:
        #     raise exceptions.UserError(_("No future installments found to rebalance."))
        #
        # # Append a dummy one for "add_at_end"
        # if self.skip_type == 'add_at_end':
        #     last_line = future_lines[-1]
        #     last_date = datetime(last_line.year, int(last_line.month), 1)
        #     new_date = last_date + relativedelta(months=1)
        # else:  # duplicate_next
        #     current_date = datetime(self.year, int(self.month), 1)
        #     new_date = current_date + relativedelta(months=1)
        #
        # # Add one more period
        # total_new_periods = len(future_lines) + 1
        # remaining_balance = sum(l.capital_amount for l in future_lines) + self.installment_id.capital_amount
        # annual_interest = loan.interest_rate
        # monthly_interest_rate = (annual_interest / 100) / 12
        #
        # # Recalculate equal installment value
        # if annual_interest > 0:
        #     installment_value = remaining_balance * monthly_interest_rate / (
        #                 1 - (1 + monthly_interest_rate) ** (-total_new_periods))
        # else:
        #     installment_value = remaining_balance / total_new_periods
        #
        # # Rebuild schedule
        # all_new_dates = []
        # start_date = datetime(future_lines[0].year, int(future_lines[0].month), 1)
        # for i in range(total_new_periods):
        #     if i == len(future_lines):  # new one (at end or next month)
        #         all_new_dates.append(new_date)
        #     else:
        #         all_new_dates.append(start_date + relativedelta(months=i))
        #
        # running_balance = remaining_balance
        # for idx in range(total_new_periods):
        #     if idx == len(future_lines):
        #         line = self.env['employee.loan.installment.line'].create({
        #             'employee_loan_id': loan.id,
        #             'employee_id': loan.employee_id.id,
        #             'status': 'draft',
        #         })
        #     else:
        #         line = future_lines[idx]
        #
        #     interest = running_balance * monthly_interest_rate if annual_interest > 0 else 0
        #     capital = installment_value - interest
        #     running_balance -= capital
        #
        #     ref_number = "LO/" + str(loan.loan_type.loan_sequence_prefix) + "/" + str(
        #         len(loan.employee_loan_installment_line_ids) + idx + 1).zfill(4)
        #
        #     line.write({
        #         'installment_ref_number': ref_number,
        #         'year': all_new_dates[idx].year,
        #         'month': str(all_new_dates[idx].month),
        #         'capital_amount': capital,
        #         'interest_amount': interest,
        #         'installment_amount': installment_value,
        #         'running_balance': running_balance,
        #     })

        self.status = 'approved'
        self.approved_by = self.env.user

    
    
