from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model_create_multi
    def create(self, vals_list):
        quants = self.env['stock.quant']
        is_inventory_mode = self._is_inventory_mode()
        allowed_fields = self._get_inventory_fields_create()

        for vals in vals_list:
            # Pull custom bypass flag from context
            force_bypass = self.env.context.get('force_create_quant', False)

            if is_inventory_mode and any(f in vals for f in ['inventory_quantity', 'inventory_quantity_auto_apply']):
                if any(field for field in vals if field not in allowed_fields):
                    if not force_bypass:
                        raise UserError(_("Quant's creation is restricted, you can't do this operation."))

                auto_apply_qty = vals.pop('inventory_quantity_auto_apply', False) or vals.pop('inventory_quantity', 0)

                product = self.env['product.product'].browse(vals['product_id'])
                location = self.env['stock.location'].browse(vals['location_id'])
                lot_id = self.env['stock.lot'].browse(vals.get('lot_id'))
                package_id = self.env['stock.quant.package'].browse(vals.get('package_id'))
                owner_id = self.env['res.partner'].browse(vals.get('owner_id'))

                quant = self._gather(product, location, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
                if lot_id:
                    quant = quant.filtered(lambda q: q.lot_id)
                if quant:
                    quant = quant[0].sudo()
                else:
                    quant = self.with_context(force_create_quant=True).sudo().create(vals)

                if auto_apply_qty:
                    quant.write({'inventory_quantity_auto_apply': auto_apply_qty})
                else:
                    quant.inventory_quantity = auto_apply_qty
                    quant.user_id = vals.get('user_id', self.env.user.id)
                    quant.inventory_date = fields.Date.today()

                quants |= quant
            else:
                quant = super().create(vals)
                quants |= quant

                if self._is_inventory_mode():
                    quant._check_company()

        return quants
