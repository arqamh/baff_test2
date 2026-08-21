from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    state = fields.Selection(selection_add=[
        ('waiting_approval', 'Waiting For Approval'),
        ('reject', 'Rejected'),
        ('posted', ),
    ], ondelete={'waiting_approval': 'set default', 'reject': 'set default'})
    is_available_payments = fields.Boolean(compute="_compute_is_available_payments")

    payment_cheque_no = fields.Char(related="payment_id.cheque_no")

    def action_register_receipt(self):
        ''' Open the modified account.payment.multi wizard to pay the selected journal entries.
        :return: An action opening the account.payment.multi wizard.
        '''
        invoices = self.env["account.move"].browse(self.ids)
        if len(invoices.mapped('partner_id')) > 1:
            raise UserError("You cannot register payment for multiple partners.")
        if invoices.filtered(lambda x: x.state == "paid"):
            raise UserError("You cannot register payment for paid invoices.")

        if invoices[0].move_type in ['out_invoice']:
            payment_type = 'inbound'
            partner_type = 'customer'
        elif invoices[0].move_type in ['in_invoice']:
            payment_type = 'outbound'
            partner_type = 'supplier'
        else:
            raise UserError("Something Went Wrong!!!")
        invoices_dict = self._default_invoice_lines(invoices)
        receipt_vals = {
            'partner_id': invoices[0].partner_id.id,
            'lock': True,
            'invoice_ids': invoices_dict,
            'payment_type': payment_type,
            'partner_type': partner_type,
            'company_id': invoices[0].company_id.id,
        }
        receipt = self.env['account.receipt.payment'].create(receipt_vals)
        return {
            'name': _('Register Payment'),
            'res_model': 'account.receipt.payment',
            'view_mode': 'form',
            'res_id': receipt.id,
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'default_partner_id': invoices.mapped('partner_id').id,
                'form_view_initial_mode': 'edit',
                'force_detailed_view': 'true'
            },
            'target': 'current',
            'type': 'ir.actions.act_window',
            'nodestroy': True
        }

    def _default_invoice_lines(self, invoices):
        """need to return payment lines by adding given credit payment data"""
        payment_lines = []
        for invoice in invoices:
            payment_lines.append((0, 0, {
                'invoice_id': invoice.id,
                'invoice_date': invoice.invoice_date,
                'invoice_age': (datetime.now().date() - invoice.invoice_date).days,
                'invoice_total': invoice.amount_total,
                'invoice_actual_due': invoice.amount_residual,
                'invoice_current_due': invoice.amount_residual,
                'invoice_paying_amount': invoice.amount_residual,
                'currency_id': invoice.currency_id.id,
            }))
        return payment_lines

    def _compute_is_available_payments(self):
        """Get no of payments for waiting approval """
        for invoice in self:
            payments_obj = self.env['account.payment'].search([('bill_ids', 'in', invoice.id), ('state', '=', 'waiting_approval')])
            if payments_obj:
                invoice.is_available_payments = True
            else:
                invoice.is_available_payments = False

    def action_view_payments_with_waiting_approval(self):
        """Open payments """
        payments = self.env['account.payment'].search(
            [('bill_ids', 'in', self.id), ('state', '=', 'waiting_approval')])
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payments.ids)],
            'context': {'create': False},
        }
        return action

class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    payment_cheque_no = fields.Char(related="payment_id.cheque_no")

class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def _prepare_js_reconciliation_widget_move_line(self, statement_line, line, recs_count=0):
        """Override method and add cheque no to the reconcile line"""
        res = super()._prepare_js_reconciliation_widget_move_line(statement_line, line, recs_count)
        if line.payment_cheque_no:
            res['ref'] += ' Cheque No - %s' % line.payment_cheque_no
        return res

    def _str_domain_for_mv_line(self, search_str):
        """Override method and add cheque no to the reconcile Search options"""
        res = super()._str_domain_for_mv_line(search_str)
        cheque_no = ['|', ('move_id.payment_cheque_no', 'ilike', search_str)]
        res = cheque_no + res
        return res

