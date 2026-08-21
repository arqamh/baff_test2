from odoo import fields, models, api, _


class PurchaseOrderApproversWizard(models.TransientModel):
    _name = 'purchase.order.approvers.wizard'
    _description = "purchase.order.approvers.wizard"

    name = fields.Char(string="Name", default="Prioritize the users that you need to approve this Purchase order.")
    purchase_order_approver_line_ids = fields.One2many('purchase.order.approvers.lines.wizard', 'line_id')
    type = fields.Selection([('add', 'Add'), ('update', 'Update')], string="Type", default='add')

    def send_for_approval(self):
        """Send for approval button. Function sets approval list in PO"""
        purchase_order = self.env['purchase.order'].browse(self.env.context.get('active_id'))
        if purchase_order and self.type == 'add':
            purchase_order.write({'purchase_order_approval_line_ids': False})
            vals = {}
            vals['purchase_order_approval_line_ids'] = []
            for record in self.purchase_order_approver_line_ids:
                vals['purchase_order_approval_line_ids'].append((0, 0, {
                    'sequence': record.sequence,
                    'user_id': record.user_id.id,
                }))
            purchase_order.write(vals)
            purchase_order.send_to_next_approver()
        else:
            confirmed_lines = purchase_order.purchase_order_approval_line_ids.filtered(lambda x: x.state in ['approved', 'rejected']).mapped('sequence')
            last_sequence = confirmed_lines[-1] if confirmed_lines else 0
            vals = {}
            vals['purchase_order_approval_line_ids'] = []
            count = 1
            for record in self.purchase_order_approver_line_ids:
                vals['purchase_order_approval_line_ids'].append((0, 0, {
                    'sequence': count + last_sequence,
                    'user_id': record.user_id.id,
                }))
                count += 1
            purchase_order.purchase_order_approval_line_ids.filtered(lambda x: x.state not in ['approved', 'rejected']).unlink()
            purchase_order.write(vals)
            purchase_order.send_to_next_approver()


class PurchaseOrderApproversLinesWizard(models.TransientModel):
    _name = 'purchase.order.approvers.lines.wizard'
    _description = "purchase.order.approvers.lines.wizard"
    _order = 'sequence'

    line_id = fields.Many2one('purchase.order.approvers.wizard')
    po_approve_line_id = fields.Many2one('purchase.order.approval.lines')
    sequence = fields.Integer(string="Sequence", default=1)
    user_id = fields.Many2one('res.users', string="Users")



