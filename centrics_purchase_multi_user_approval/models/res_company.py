from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_order_config_approval_line_ids = fields.One2many('purchase.order.config.approval.lines', 'company_id')


class PurchaseOrderConfigApprovalLines(models.Model):
    _name = 'purchase.order.config.approval.lines'
    _description = "Purchase Order Config Approval Lines"

    company_id = fields.Many2one('res.company', string="Company")
    currency_id = fields.Many2one('res.currency', readonly=True, default=lambda x: x.env.company.currency_id)
    amount_from = fields.Monetary(string="Amount From")
    amount_to = fields.Monetary(string="Amount To")
    user_ids = fields.Many2many('res.users', string="Users")