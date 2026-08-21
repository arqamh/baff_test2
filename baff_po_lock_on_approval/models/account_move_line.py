from odoo import _, api, fields, models
from odoo.exceptions import UserError


LOCKED_FIELDS = ('product_id', 'quantity', 'product_uom_id')
LOCKED_STATES = ('purchase', 'done')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    po_locked = fields.Boolean(
        string='Locked from PO',
        compute='_compute_po_locked', store=True,
        help='True when this bill line is linked to an approved or locked '
             'Purchase Order line — Product, Quantity and UoM are read-only.')

    @api.depends('purchase_line_id', 'purchase_line_id.order_id.state')
    def _compute_po_locked(self):
        for line in self:
            po = line.purchase_line_id.order_id if line.purchase_line_id else False
            line.po_locked = bool(po and po.state in LOCKED_STATES)

    def write(self, vals):
        if self.env.context.get('bypass_po_lock'):
            return super().write(vals)
        touched = [f for f in LOCKED_FIELDS if f in vals]
        if touched:
            locked = self.filtered('po_locked')
            if locked:
                labels = ', '.join(self._fields[f].string or f for f in touched)
                pos = ', '.join(locked.mapped('purchase_line_id.order_id.name'))
                raise UserError(_(
                    "Cannot modify %(fields)s on a vendor bill line linked to "
                    "an approved Purchase Order. These fields are locked to "
                    "preserve the approved PO value. Source PO(s): %(orders)s.",
                    fields=labels, orders=pos))
        return super().write(vals)
