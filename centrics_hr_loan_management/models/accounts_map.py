from odoo import models, fields, api, _


class AccountsMap(models.Model):
    _name = 'accounts.map'
    _description = 'Accounts Map'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", tracking=True, readonly=True, default='New')
    action = fields.Selection([('loan_payment', 'Loan Payment'), ('loan_repayment', 'Loan Repayment')], tracking=True)
    journal_id = fields.Many2one('account.journal', string="Journal", tracking=True)
    bank_cash_account_id = fields.Many2one('account.account', string="Bank/Cash Account", tracking=True)
    recoverable_account_id = fields.Many2one('account.account', string="Recoverable Account", tracking=True)
    payable_account_id = fields.Many2one('account.account', string="Payable Account", tracking=True)
    interest_account_id = fields.Many2one('account.account', string="Interest Account", tracking=True)
    is_global = fields.Boolean(string="Global", compute="_compute_is_global", store=True, tracking=True)
    loan_type_ids = fields.Many2many('employee.loan.type', string="Loan Types")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, store=True,
                                 tracking=True)



    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('accounts.map') or 'New'
        return super(AccountsMap, self).create(vals)

    @api.depends('loan_type_ids')
    def _compute_is_global(self):
        for record in self:
            record.is_global = not bool(record.loan_type_ids)
