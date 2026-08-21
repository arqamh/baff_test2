from odoo import fields, api, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    have_credit_limit = fields.Boolean(string="Credit Limit Available")
    remaining_credit_limit = fields.Monetary("Remaining Credit Limit", readonly=True, compute='_remaining_credit_limit')

    def _remaining_credit_limit(self):
        """
        Compute the remaining credit limit.
        """
        for partner in self:
            invoice_sum = sum(invoice.amount_residual_signed for invoice in self.env['account.move'].search(
                [('state', '=', 'posted'), ('partner_id', '=', self.id), ('payment_state', '!=', 'paid'),
                 ('move_type', '=', 'out_invoice')]))
            partner.update({
                'remaining_credit_limit': self.credit_limit - invoice_sum
            })

    @api.onchange('credit_limit')
    def credit_limit_validation(self):
        """check initial credit limit of the customer & if it credit limit is
        greater than 0 allow over credit limit become true"""
        if self.credit_limit > 0:
            invoice_sum = sum(invoice.amount_residual_signed for invoice in self.env['account.move'].search(
                [('state', '=', 'posted'), ('partner_id', '=', self.id), ('payment_state', '!=', 'paid'),
                 ('move_type', '=', 'out_invoice')]))
            self.remaining_credit_limit = self.credit_limit - invoice_sum
