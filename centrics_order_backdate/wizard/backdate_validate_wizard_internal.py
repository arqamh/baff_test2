
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class BackdateValidateWizardInternal(models.TransientModel):
    _name = 'backdate.validate.wizard.internal'
    _description = 'Backdate Validate Internal Wizard'

    transfer_date = fields.Datetime('BackDate')
    picking_ids = fields.Many2many('stock.picking')

    def confirm_backdate(self):
        """Confirm wizard
        Update related deliveries with new backdate
        """
        if not isinstance(self.transfer_date, datetime):
            raise UserError(_('Invalid transfer date.'))
        if self.transfer_date.date() > datetime.now().date():
            raise UserError(_('Please Enter Correct Back Date'))
        picking_ids = None

        active_models = self._context.get('active_model')
        if active_models == 'stock.picking':
            picking_ids = self.picking_ids if self.picking_ids else self.env['stock.picking'].browse(self._context.get('active_id'))

        elif active_models == 'stock.picking.type':
            stock_type_id = self.env['stock.picking.type'].browse(self._context.get('active_id'))
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_ids = self.env['stock.picking'].search([('picking_type_id', '=', stock_type_id.id)], order='id desc', limit=1)

        elif active_models == 'purchase.order':
            custom_purchase_ids = self.env['purchase.order'].browse(self._context.get('active_id'))
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_ids = self.env['stock.picking'].search([('purchase_id', '=', custom_purchase_ids.id)])

        elif active_models == 'sale.order':
            sale_order_ids = self.env['sale.order'].browse(self._context.get('active_ids'))
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_list = [sale_id.picking_ids.ids for sale_id in sale_order_ids][0]
                picking_ids = self.env['stock.picking'].browse(picking_list)

        elif active_models == 'material.purchase.requisition':
            material_requisition = self.env['material.purchase.requisition'].browse(self._context.get('active_id'))
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_ids = self.env['stock.picking'].search([('custom_requisition_id', '=', material_requisition.id)])

        if picking_ids:
            for picking in picking_ids:
                for move_line in picking.move_ids:
                    move_line.write({
                        'date': self.transfer_date,
                        'move_date': self.transfer_date,
                        'date_deadline': self.transfer_date
                    })

                    for valuation in move_line.stock_valuation_layer_ids:
                        self.env.cr.execute(
                            """UPDATE stock_valuation_layer SET create_date=%s, product_id=%s,stock_move_id=%s,company_id=%s WHERE id=%s""",
                            (self.transfer_date, valuation.product_id.id, valuation.stock_move_id.id, valuation.company_id.id, valuation.id))

                    for line in move_line.mapped('move_line_ids'):
                        line.write({
                            'date': self.transfer_date,
                        })

            return picking_ids.with_context(force_period_date=self.transfer_date).button_validate()
        else:
            raise ValidationError("Please Contact Administrator for this record -%s" % active_models)


    def skip_backdate(self):
        """Skip Backdate"""
        active_models = self._context.get('active_model')
        picking_ids = None
        if active_models == 'stock.picking':
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_ids = self.env['stock.picking'].browse(self._context.get('active_id'))

        elif active_models == 'stock.picking.type':
            stock_type_id = self.env['stock.picking.type'].browse(self._context.get('active_id'))
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_ids = self.env['stock.picking'].search([('picking_type_id', '=', stock_type_id.id)],order='id desc', limit=1)

        elif active_models == 'purchase.order':
            custom_purchase_ids = self.env['purchase.order'].browse(self._context.get('active_id'))
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_ids = self.env['stock.picking'].search([('purchase_id', '=', custom_purchase_ids.id)])

        elif active_models == 'sale.order':
            sale_order_ids = self.env['sale.order'].browse(self._context.get('active_ids'))
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_list = [sale_id.picking_ids.ids for sale_id in sale_order_ids][0]
                picking_ids = self.env['stock.picking'].browse(picking_list)

        elif active_models == 'material.purchase.requisition':
            material_requisition = self.env['material.purchase.requisition'].browse(self._context.get('active_id'))
            if self.picking_ids:
                picking_ids = self.picking_ids
            else:
                picking_ids = self.env['stock.picking'].search([('custom_requisition_id', '=', material_requisition.id)])

        if picking_ids:
            return picking_ids.with_context(Skip=True).button_validate()
        else:
            raise ValidationError("Please Contact Administrator for this record -%s" % active_models)

