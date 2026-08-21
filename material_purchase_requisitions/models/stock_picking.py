from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_requisition_id = fields.Many2one('material.purchase.requisition', string='Purchase Requisition',
                                            readonly=True, copy=True)

    def button_validate(self):
        """Override to redirect to backorder after creation"""
        # Store the picking ID before validation
        picking_before = self

        # Call the parent method
        res = super(StockPicking, self).button_validate()

        # Check if a backorder was created
        backorder = self.env['stock.picking'].search([
            ('backorder_id', '=', picking_before.id),
            ('state', '!=', 'cancel')
        ], limit=1, order='id desc')

        # If a backorder was created and res is True (validation successful without wizard)
        if backorder and isinstance(res, bool) and res:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': backorder.id,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
            }

        # If res is already an action dict (wizard was shown), return it as-is
        return res


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        """Override to redirect to backorder after creation
        OPTIMIZED: Batch query for backorders instead of search per picking"""
        # Get the pickings before processing
        pickings = self.pick_ids

        # Call parent method to create backorder
        res = super(StockBackorderConfirmation, self).process()

        # BATCH QUERY: Find all backorders for these pickings in single query
        if pickings:
            backorders = self.env['stock.picking'].search([
                ('backorder_id', 'in', pickings.ids),
                ('state', '!=', 'cancel')
            ], order='id desc')

            if backorders:
                # Return action for the first (most recent) backorder
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'stock.picking',
                    'res_id': backorders[0].id,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'current',
                }

        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    custom_requisition_line_id = fields.Many2one('material.purchase.requisition.line', string='Requisitions Line',
                                                 copy=True)


