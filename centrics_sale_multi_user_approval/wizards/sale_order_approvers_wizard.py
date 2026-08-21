from odoo import fields, models, api, _


class PurchaseOrderApproversWizard(models.TransientModel):
    _name = 'sale.order.approvers.wizard'

    msg = fields.Char(string="Message")
    gp_margin = fields.Boolean(string="GP Margin")
    credit_limit = fields.Boolean(string="Credit Limit")
    payment_term = fields.Boolean(string="Payment Term")
    order_id = fields.Many2one('sale.order')
    model_id = fields.Many2one('ir.model')
    name = fields.Char(string="Name", default="Prioritize the users that you need to approve this Purchase order.")
    sale_order_approver_line_ids = fields.One2many('sale.order.approvers.lines.wizard', 'line_id')
    type = fields.Selection([('add', 'Add'), ('update', 'Update')], string="Type", default='add')

    def send_for_approval(self):
        """Send for approval button. Function sets approval list in PO"""
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        if sale_order and self.type == 'add':
            sale_order.write({'sale_order_approval_line_ids': False})
            vals = {}
            vals['sale_order_approval_line_ids'] = []
            for record in self.sale_order_approver_line_ids:
                vals['sale_order_approval_line_ids'].append((0, 0, {
                    'sequence': record.sequence,
                    'user_id': record.user_id.id,
                }))
            sale_order.write(vals)
            sale_order.send_to_next_approver()
        else:
            confirmed_lines = sale_order.sale_order_approval_line_ids.filtered(lambda x: x.state in ['approved', 'rejected']).mapped('sequence')
            last_sequence = confirmed_lines[-1] if confirmed_lines else 0
            vals = {}
            vals['sale_order_approval_line_ids'] = []
            count = 1
            for record in self.sale_order_approver_line_ids:
                vals['sale_order_approval_line_ids'].append((0, 0, {
                    'sequence': count + last_sequence,
                    'user_id': record.user_id.id,
                }))
                count += 1
            sale_order.sale_order_approval_line_ids.filtered(lambda x: x.state not in ['approved', 'rejected']).unlink()
            sale_order.write(vals)
            sale_order.send_to_next_approver()


class SaleOrderApproversLinesWizard(models.TransientModel):
    _name = 'sale.order.approvers.lines.wizard'
    _order = 'sequence'

    line_id = fields.Many2one('sale.order.approvers.wizard')
    so_approve_line_id = fields.Many2one('sale.order.approval.lines')
    sequence = fields.Integer(string="Sequence", default=1)
    user_id = fields.Many2one('res.users', string="Users")
