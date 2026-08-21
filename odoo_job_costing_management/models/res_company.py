from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    factory_admin_overhead = fields.Float(string='Factory and Admin Overhead', default=0.05)
    profit_margin = fields.Float(string='Profit Margin', default=0.3)
    automatic_approval_lines = fields.One2many('automatic.approval.lines', 'company_id',
                                               string="Automatic Approval Consider")
    job_cost_prefix = fields.Char(string='Sequence Prefix')
    job_cost_revise_suffix = fields.Char(string='Revise Sequence Suffix')
    vendor_price_margin = fields.Float(string="Vendor Price Margin")


class AutomaticApprovalLines(models.Model):
    _name = 'automatic.approval.lines'
    _description = 'Automatically sent for approval considering'

    company_id = fields.Many2one('res.company', string="Company")
    currency_id = fields.Many2one('res.currency', readonly=True, default=lambda x: x.env.company.currency_id)
    condition = fields.Selection([('below', 'Below'), ('between', 'Between'), ('above', 'Above')], string="Condition", default='between')
    user_ids = fields.Many2many('res.users', string="Users")
    from_amount = fields.Float(string="From Amount")
    to_limit = fields.Float(string="Amount Limit")
    is_review = fields.Boolean(string="Review", default=False)
