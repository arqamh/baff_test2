from odoo import _, models
from odoo.exceptions import UserError


LOCKED_FIELDS = ('product_id', 'product_qty', 'product_uom')
LOCKED_STATES = ('purchase', 'done')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def write(self, vals):
        if self.env.context.get('bypass_po_lock'):
            return super().write(vals)
        touched = [f for f in LOCKED_FIELDS if f in vals]
        if touched:
            locked = self.filtered(lambda l: l.order_id.state in LOCKED_STATES)
            if locked:
                labels = ', '.join(self._fields[f].string or f for f in touched)
                names = ', '.join(locked.mapped('order_id.name'))
                raise UserError(_(
                    "Cannot modify %(fields)s on an approved purchase order. "
                    "The Product, Quantity and Unit of Measure are locked once "
                    "the PO is approved. Affected order(s): %(orders)s.",
                    fields=labels, orders=names))
        return super().write(vals)
