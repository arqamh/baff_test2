from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_order_config_approval_line_ids = fields.One2many('sale.order.config.approval.lines', 'company_id')
    gp_margin_validation = fields.Boolean(string="Allow Gross Profit Margin Validation", default=False)
    credit_limit_validation = fields.Boolean(string="Allow Credit Limit Validation", default=False)
    payment_terms_validation = fields.Boolean(string="Allow Payment Terms Validation", default=False)
    gp_margin_company = fields.Float(string="General Gross Profit Margin(%)")


class SaleOrderConfigApprovalLines(models.Model):
    _name = 'sale.order.config.approval.lines'
    _description = "Sale Order Config Approval Lines"

    company_id = fields.Many2one('res.company', string="Company")
    currency_id = fields.Many2one('res.currency', readonly=True, default=lambda x: x.env.company.currency_id)
    amount_from = fields.Monetary(string="Amount From")
    amount_to = fields.Monetary(string="Amount To")
    user_ids = fields.Many2many('res.users', string="Users")
