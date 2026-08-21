from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo import Command


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    boat_type_id = fields.Many2one(comodel_name='boat.type', string="Boat Type")
    boat_type_ids = fields.Many2many(comodel_name='boat.type', string="Boat Types")
    is_this_standard_bom = fields.Boolean(string="Is this Standard BOM")
    bom_type = fields.Selection([('base_bom', 'Base BOM'), ('option_bom', 'Option BOM')], string="BOM Type")
    last_purchase_price = fields.Float(string="Last Purchase Price", compute='_compute_last_purchase_price_date')
    last_purchase_date = fields.Date(string="Last Purchase Date", compute='_compute_last_purchase_price_date')
    designation_2 = fields.Char(string="Designation 2")
    designation_3 = fields.Char(string="Designation 3")
    clipper_no = fields.Char(string="Clipper No")
    length_overall = fields.Char(string="Length Overall")
    maximum_beam = fields.Char(string="Maximum Beam")
    draft = fields.Char(string="Draft")
    standard_engine = fields.Char(string="Standard Engine")
    selected_capacity = fields.Char(string="Selected Capacity")
    maximum_capacity = fields.Char(string="Maximum Allowed Capacity")
    color = fields.Char(string="Color")
    force_quantity_updated = fields.Boolean(string="Force Quantity Update", default=False)

    @api.onchange('bom_type')
    def _onchange_bom_type(self):
        """
            Update boat_type_id and boat_type_ids fields based on the selected value of bom_type.
            If bom_type is 'base_bom', set boat_type_ids to empty list.
            If bom_type is 'option_bom', set boat_type_id to False.
        """
        # Clear boat_type_ids when base_bom is selected
        if self.bom_type == 'base_bom':
            self.boat_type_ids = [(6, 0, [])]
        # Clear boat_type_id when option_bom is selected
        elif self.bom_type == 'option_bom':
            self.boat_type_id = False

    @api.onchange('boat_type_id', 'bom_type')
    def _onchange_boat_type_id(self):
        """Get value from boat type and assign to boat types and assign to boat types"""
        if self.bom_type == 'base_bom' and self.boat_type_id:
            existing_template = self.env['product.template'].search([('bom_type', '=', 'base_bom'), ('boat_type_id', '=', self.boat_type_id.id), ('id', '!=', self._origin.id)], limit=1)
            # Restrict single bom type
            if existing_template:
                raise ValidationError("There is a another product for this Boat Type - %s" % existing_template.name)
        else:
            if self.boat_type_id:
                # Get value from boat type and assign to boat types
                self.boat_type_ids = [(4, self.boat_type_id.id)]

    def _compute_last_purchase_price_date(self):
        # search the products in purchase orders through the product id and state of the product
        for rec in self:
            last_purchase_price = 0
            last_purchase_date = False
            purchase_price_date = self.env['purchase.order.line'].search([('product_id', '=', rec.product_variant_id.id),
                                                                          ('order_id.state', '=', 'purchase')],
                                                                         limit=1, order='id desc')
            if purchase_price_date:
                last_purchase_price = purchase_price_date.price_unit
                last_purchase_date = purchase_price_date.date_approve

                if rec.seller_ids:
                    vendor = self.seller_ids.filtered(lambda x: x.partner_id.id == purchase_price_date.partner_id.id and x.product_tmpl_id.id == purchase_price_date.product_id.product_tmpl_id.id)
                    if vendor:
                        vendor.price = purchase_price_date.price_unit
            rec.last_purchase_price = last_purchase_price
            rec.last_purchase_date = last_purchase_date

    def update_on_hand_stock_quantity(self, date):
        """
        Function to trigger as a server action to adjust stock quants based on movements up to a cutoff date.
        :param date: The cutoff date for initial move filtering
        """
        # The cutoff date for calculating the initial stock moves
        cutoff_date = date
        cutoff_datetime = datetime.strptime(cutoff_date, "%Y-%m-%d %H:%M:%S")
        # Current timestamp for comparing against more recent stock moves
        current_date = datetime.now()
        # Get the IDs of the records on which this action is called
        product_ids = self.mapped('product_variant_id').ids
        # Browse those product records
        products = self.env['product.product'].browse(product_ids)

        # Search all stock move lines for the given products up to the cutoff date
        move_lines = self.env['stock.move.line'].search([
            ('product_id', 'in', product_ids),
            ('date', '<=', cutoff_date),
            ('state', '=', 'done')
        ])

        # Search all stock move lines for the same products up to now
        updated_move_lines = self.env['stock.move.line'].search([
            ('product_id', 'in', product_ids),
            ('date', '<=', current_date),
            ('state', '=', 'done')
        ])

        # Find all internal locations where inventory is tracked
        internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        # Prepare a list to hold created inventory adjustments (if needed)
        created_inventories = []

        # Loop through each internal location to calculate and apply adjustments

        inventory_lines = []  # (Unused in this snippet, but could hold per-product lines)

        # Process each selected product
        for product in products:
            valuation_entries = []
            for location in internal_locations:
                if not product.force_quantity_updated:
                    # Filter moves for this product up to the cutoff date
                    product_moves = move_lines.filtered(lambda m: m.product_id.id == product.id)
                    # Filter moves for this product up to the current date
                    final_product_moves = updated_move_lines.filtered(lambda m: m.product_id.id == product.id)

                    # Within these moves, find those moving into this location
                    in_location = product_moves.filtered(lambda m: m.location_dest_id.id == location.id)
                    # And those moving out of this location
                    out_location = product_moves.filtered(lambda m: m.location_id.id == location.id)

                    # Only proceed if there were any moves in or out
                    if in_location or out_location:
                        # Sum quantities moved in and moved out up to cutoff date
                        qty_in = sum(in_location.mapped('qty_done'))
                        qty_out = sum(out_location.mapped('qty_done'))
                        net_qty = qty_in - qty_out
                        # Sum cost moved in and moved out up to cutoff date
                        total_cost_in = sum(in_location.mapped('product_stock_quant_ids').mapped('value'))
                        total_cost_out = sum(out_location.mapped('product_stock_quant_ids').mapped('value'))
                        net_total_cost = total_cost_in - total_cost_out
                        # Sum cost moved in and moved out up to cutoff date in the valuation
                        valuation_in_cost = sum(in_location.mapped('move_id').mapped('stock_valuation_layer_ids').filtered(
                            lambda x: x.create_date <= cutoff_datetime).mapped('value'))
                        valuation_out_cost = sum(out_location.mapped('move_id').mapped('stock_valuation_layer_ids').filtered(
                            lambda x: x.create_date <= cutoff_datetime).mapped('value'))
                        net_valuation_cost = valuation_in_cost + valuation_out_cost

                        # Sum quantities moved in and out up to the current date
                        final_qty_in = sum(
                            final_product_moves.filtered(lambda m: m.location_dest_id.id == location.id).mapped('qty_done'))
                        final_qty_out = sum(
                            final_product_moves.filtered(lambda m: m.location_id.id == location.id).mapped('qty_done'))
                        final_net_qty = final_qty_in - final_qty_out
                        # Sum cost moved in and out up to the current date
                        final_cost_in = sum(final_product_moves.filtered(lambda m: m.location_dest_id.id == location.id).mapped(
                            'product_stock_quant_ids').filtered(lambda x: x.create_date <= current_date).mapped('value'))
                        final_cost_out = sum(final_product_moves.filtered(lambda m: m.location_id.id == location.id).mapped(
                            'product_stock_quant_ids').filtered(lambda x: x.create_date <= current_date).mapped('value'))
                        net_final_cost = final_cost_in - final_cost_out

                        # Effective quantity change since the cutoff date
                        effective_quantity = final_net_qty - net_qty
                        effective_cost = net_final_cost - net_total_cost

                        # Search for an existing quant record for this product/location
                        adjustment_id = self.env['stock.quant'].search([
                            ('location_id', '=', location.id),
                            ('product_id', '=', product.id),
                        ])

                        if adjustment_id:
                            # If quant exists, update its inventory quantity
                            adjustment_id.inventory_quantity = effective_quantity
                            adjustment_id.value = effective_cost
                        else:
                            # Otherwise, create a new quant with the computed quantity
                            adjustment_id = self.env['stock.quant'].with_context(force_create_quant=True).sudo().create({
                                'location_id': location.id,
                                'product_id': product.id,
                                'product_uom_id': product.uom_id.id,
                                'inventory_quantity': effective_quantity,
                                'value': effective_cost
                            })
                            # Keep track of newly created inventory adjustments
                            created_inventories.append(adjustment_id)

                        # Apply the inventory adjustment to reflect the new quant value
                        adjustment_id.action_apply_inventory()
                        valuation_enty = self.env['stock.valuation.layer'].search([('product_id', '=', adjustment_id.product_id.id)]).filtered(lambda x: x.create_date.date() == datetime.now().date())
                        if valuation_enty:
                            if len(valuation_enty) > 1:
                                valuation_enty = valuation_enty[-1]
                            if valuation_enty not in valuation_entries:
                                valuation_entries += valuation_enty
            product.description_picking = "Stock Updated"
            product.force_quantity_updated = True
            old_valuations = self.env['stock.valuation.layer'].search([
                ('product_id', '=', product.id),
                ('create_date', '<=', cutoff_date)
            ])
            if old_valuations:
                total_value = sum(old_valuations.mapped('value'))
                total_quantity = 0
                for valuation_entry in valuation_entries:
                    total_quantity += valuation_entry.quantity
                average_cost = 0
                if total_quantity == 0:
                    if total_value >= 0:
                        average_cost = total_value * -1
                    else:
                        average_cost = abs(total_value)
                else:
                    average_cost = abs(total_value) / abs(total_quantity)
                for valuation_entry in valuation_entries:
                    total_cost = average_cost * valuation_entry.quantity if not total_quantity == 0 else average_cost
                    valuation_entry.write({
                        'description': "Quantity Updated via Script",
                        'unit_cost': average_cost,
                        'value': total_cost
                    })
                    journal_entry = valuation_entry.account_move_id
                    if journal_entry:
                        journal_entry.button_draft()
                        all_line_vals = []
                        for line in journal_entry.invoice_line_ids:
                            all_line_vals += line.copy_data()
                        journal_entry.write({'invoice_line_ids': [Command.clear()]})
                        adjusted_vals = []
                        company_currency = journal_entry.company_currency_id

                        valuation_account = product.categ_id.property_stock_valuation_account_id
                        valuation_journal_entry = next((val for val in all_line_vals if val["account_id"] == valuation_account.id), None)
                        interim_journal_entry = next((val for val in all_line_vals if val["account_id"] != valuation_account.id), None)
                        if valuation_entry.value < 0:
                            valuation_journal_entry['balance'] = total_cost
                            valuation_journal_entry['amount_currency'] = total_cost
                            interim_journal_entry['balance'] = abs(total_cost)
                            interim_journal_entry['amount_currency'] = abs(total_cost)
                        else:
                            valuation_journal_entry['balance'] = total_cost
                            valuation_journal_entry['amount_currency'] = total_cost
                            interim_journal_entry['balance'] = total_cost * -1
                            interim_journal_entry['amount_currency'] = total_cost * -1
                        adjusted_vals.append(valuation_journal_entry)
                        adjusted_vals.append(interim_journal_entry)
                        journal_entry.write({'line_ids': [Command.create(v) for v in adjusted_vals]})
                        if journal_entry.is_invoice(include_receipts=True):
                            journal_entry._recompute_dynamic_lines(recompute_all_taxes=True)
                        journal_entry.action_post()
