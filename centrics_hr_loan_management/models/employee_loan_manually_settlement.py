from odoo import models, fields, api, _


class EmployeeLoanManuallySettlement(models.Model):
    _name = 'employee.loan.manually.settlement'
    _description = 'Employee Loan Manually Settlement'

    name = fields.Char(string="Name", default="New")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    loan_id = fields.Many2one(
        'employee.loan',
        string="Loan",
        domain="[('employee_id', '=', employee_id), ('loan_status', 'in', ['paid', 'in_recovery'])]",
    )
    loan_processed_amount = fields.Float(string="Loan Amount", store=True)
    loan_rate = fields.Float(string="Loan Rate", related="loan_id.loan_type.loan_interest", store=True)
    is_interest_applicable = fields.Boolean(string="Interest Applicable", compute="_compute_interest_flag", store=True)

    due_amount = fields.Float(string="Due Amount", compute="_compute_due_amount", store=True)
    settlement_type = fields.Selection([
        ('full', 'Full'),
        ('partial', 'Partial'),
        ('free_partial', 'Free Partial')
    ], string="Settlement Type", default="full")

    number_of_installments = fields.Integer(string="Number of Installments")
    settlement_amount = fields.Float(string="Settlement Amount", compute="_compute_settlement_amount")
    free_partial_amount = fields.Float(string="Free Partial Settlement Amount")
    interest_amount = fields.Float(string="Interest Amount", compute="_compute_interest_amount", store=True)
    total_settlement_amount = fields.Float(string="Total Settlement Amount", compute="_compute_total_settlement_amount",
                                           store=True)

    settle_installments_from = fields.Selection([
        ('from_end', 'From End'),
        ('from_beginning', 'From Beginning')
    ], string="Settle Installments From", default="from_end")

    settlement_journal_id = fields.Many2one('account.journal', string="Settlement Journal")
    settlement_entry = fields.Many2one('account.move', string="Settlement Entry")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('settled', 'Settled')
    ], string="State", default="draft")

    @api.onchange('loan_id')
    def onchange_loan_id(self):
        if self.loan_id:
            if self.loan_id.processed_amount:
                self.loan_processed_amount = self.loan_id.processed_amount

    @api.depends('loan_id')
    def _compute_due_amount(self):
        for record in self:
            if record.loan_id:
                record.due_amount = sum(
                    line.installment_amount - (line.paid_capital_amount + line.paid_interest_amount)
                    for line in record.loan_id.employee_loan_installment_line_ids
                    if line.status == 'draft'
                )
            else:
                record.due_amount = 0.0

    @api.depends('loan_id')
    def _compute_interest_flag(self):
        for rec in self:
            rec.is_interest_applicable = rec.loan_id and rec.loan_id.loan_type.loan_interest > 0.0

    @api.depends('settlement_amount', 'loan_rate', 'is_interest_applicable')
    def _compute_interest_amount(self):
        for rec in self:
            if rec.is_interest_applicable:
                rec.interest_amount = (rec.settlement_amount * rec.loan_rate) / 100
            else:
                rec.interest_amount = 0.0

    @api.depends('settlement_amount', 'interest_amount')
    def _compute_total_settlement_amount(self):
        for rec in self:
            rec.total_settlement_amount = rec.settlement_amount + rec.interest_amount

    @api.depends('loan_id', 'settlement_type', 'number_of_installments', 'settle_installments_from',
                 'free_partial_amount')
    def _compute_settlement_amount(self):
        for record in self:
            if record.loan_id:
                if record.settlement_type == 'full':
                    record.settlement_amount = record.due_amount
                elif record.settlement_type == 'partial':
                    draft_installments = list(
                        filter(lambda i: i.status == 'draft', record.loan_id.employee_loan_installment_line_ids))
                    if record.settle_installments_from == 'from_end':
                        draft_installments.reverse()
                    selected_installments = draft_installments[:record.number_of_installments]
                    record.settlement_amount = sum(
                        installment.installment_amount for installment in selected_installments)
                elif record.settlement_type == 'free_partial':
                    record.settlement_amount = 0.0
            else:
                record.settlement_amount = 0.0

    def action_mark_settled(self):
        self.ensure_one()

        if self.settlement_type == 'full':
            installments_to_settle = self.loan_id.employee_loan_installment_line_ids.filtered(
                lambda l: l.status == 'draft')
            for inst in installments_to_settle:
                inst.status = 'paid'
                inst.payment_method = 'manual'

            move = self._create_accounting_entry(self.total_settlement_amount)
            self.settlement_entry = move.id

        elif self.settlement_type == 'partial':
            all_installments = self.loan_id.employee_loan_installment_line_ids.filtered(lambda l: l.status == 'draft')
            sorted_installments = all_installments.sorted(key=lambda x: x.date,
                                                          reverse=(self.settle_installments_from == 'from_end'))
            installments_to_settle = sorted_installments[:self.number_of_installments]

            for inst in installments_to_settle:
                inst.status = 'paid'
                inst.payment_method = 'manual'

            move = self._create_accounting_entry(self.total_settlement_amount)
            self.settlement_entry = move.id

        elif self.settlement_type == 'free_partial':
            remaining_payment = self.free_partial_amount
            draft_installments = self.loan_id.employee_loan_installment_line_ids.filtered(lambda l: l.status == 'draft')

            settled_interest_amount  =  0.0
            settled_capital_amount = 0.0
            for inst in draft_installments:
                if remaining_payment <= 0:
                    break

                # Apply interest first
                if self.loan_id.loan_type.loan_interest > 0.0:
                    interest_due = inst.interest_amount - inst.paid_interest_amount
                    if interest_due > 0:
                        interest_payment = min(interest_due, remaining_payment)
                        inst.paid_interest_amount += interest_payment
                        settled_interest_amount += interest_payment
                        remaining_payment -= interest_payment

                # Apply principal next
                principal_due = inst.capital_amount - inst.paid_capital_amount
                if principal_due > 0 and remaining_payment > 0:
                    principal_payment = min(principal_due, remaining_payment)
                    inst.paid_capital_amount += principal_payment
                    settled_capital_amount += principal_payment
                    remaining_payment -= principal_payment

                # Mark as paid if both parts are covered
                if (inst.interest_amount <= inst.paid_interest_amount and
                        inst.capital_amount <= inst.paid_capital_amount):
                    inst.status = 'paid'
                    inst.payment_method = 'manual'

            move = self._create_accounting_entry(self.free_partial_amount, settled_interest_amount, settled_capital_amount)
            self.settlement_entry = move.id

        self.state = 'settled'
        self.name = self.env['ir.sequence'].next_by_code('employee.loan.manually.settlement') or _('New')

    def _create_accounting_entry(self, totally_paid, settled_interest_amount=0.0, settled_capital_amount=0.0):
        if self.loan_id.loan_type.loan_interest > 0.0:
            move = self.env['account.move'].create({
                'journal_id': self.settlement_journal_id.id,
                'date': fields.Date.today(),
                'ref': _('Loan Manual Settlement - %s' % self.employee_id.name),
                'line_ids': [(0, 0, {
                    'account_id': self.settlement_journal_id.default_account_id.id,
                    'partner_id': self.employee_id.address_home_id.id,
                    'name': 'Loan Manual Settlement',
                    'debit': totally_paid,
                }), (0, 0, {
                    'account_id': self.loan_id.loan_type.default_receivable_account_id.id,
                    'partner_id': self.employee_id.address_home_id.id,
                    'name': 'Loan Manual Settlement',
                    'credit': settled_capital_amount,
                }), (0, 0, {
                    'account_id': self.loan_id.loan_type.default_interest_account_id.id,
                    'partner_id': self.employee_id.address_home_id.id,
                    'name': 'Loan Manual Settlement',
                    'credit': settled_interest_amount,
                })]
            })
            move.action_post()
        else :
            move = self.env['account.move'].create({
                'journal_id': self.settlement_journal_id.id,
                'date': fields.Date.today(),
                'ref': _('Loan Manual Settlement - %s' % self.employee_id.name),
                'line_ids': [(0, 0, {
                    'account_id': self.settlement_journal_id.default_account_id.id,
                    'partner_id': self.employee_id.address_home_id.id,
                    'name': 'Loan Manual Settlement',
                    'debit': totally_paid,
                }), (0, 0, {
                    'account_id': self.loan_id.loan_type.default_receivable_account_id.id,
                    'partner_id': self.employee_id.address_home_id.id,
                    'name': 'Loan Manual Settlement',
                    'credit': totally_paid,
                })]
            })
            move.action_post()

        return move
