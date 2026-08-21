from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError, UserError


class ProcurementPlan(models.Model):
    _name = 'procurement.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Procurement Plan"
    _order = 'scheduled_date asc, product_id asc'

    name = fields.Char()
    product_id = fields.Many2one('product.product', required=True, tracking=True)
    product_code = fields.Char(string='Material Code', related='product_id.default_code', store=False)
    product_tml_id = fields.Many2one('product.template')
    product_uom = fields.Many2one('uom.uom', required=True)
    mrp_id = fields.Many2one('mrp.production', ondelete="cascade")
    source = fields.Char(tracking=True)
    scheduled_date = fields.Date(tracking=True)
    required_qty = fields.Float(default=0.00)
    on_hand_qty = fields.Float(compute="compute_to_order_qty")
    forecasted_qty = fields.Float(compute="compute_to_order_qty")
    to_order_qty = fields.Float(string="To Order Qty", default=0)
    actual_to_order_qty = fields.Float(compute="compute_to_order_qty")
    remaining_to_order = fields.Float(default=0.00, compute="compute_remaining_to_order")
    partner_id = fields.Many2one('res.partner', string="Vendor",  tracking=True)
    partner_ids = fields.Many2many('res.partner', string="Vendors")
    lead_time = fields.Float(default=0.00, compute='get_vendor_lead_time_details')
    order_last_date = fields.Date(string="Procurement Start Date", compute='estimate_last_order_date')
    ordered_qty = fields.Float(compute="compute_ordered_received_qty")
    received_qty = fields.Float(compute="compute_ordered_received_qty")
    pending_qty = fields.Float(string='Pending Qty', compute='_compute_pending_qty')
    state_technical = fields.Boolean(compute="compute_delivery_status", help='Technical field for compute state')
    state = fields.Selection([('draft', 'Draft'),
                              ('rfq', 'RFQ'),
                              ('po', 'Purchase Order'),
                              ('progress', 'In Progress'),
                              ('cancel', 'Cancel'),
                              ('completed', 'Completed')
                              ] , tracking=True)
    delivery_status = fields.Selection([('pending', 'Pending'), ('partial', 'Partially Received'),
                                        ('completed', 'Completed')], tracking=True)
    new_status = fields.Selection([('po_created', 'PO Created'), ('rfq_created', 'RFQ Created'),
                                   ('partially_processed', 'Partially Processed'), ('pending_status', 'Pending'),
                                   ('fully_processed', 'Fully Processed')], string="Status",
                                  compute="_compute_new_status", store=True)
    purchase_order_ids = fields.Many2many('purchase.order', compute="compute_purchase_order", store='True')
    purchase_order_line_ids = fields.Many2many('purchase.order.line', 'purchase_line_procurement_rel', 'po_line_id', 'proc_id')
    component_id = fields.Many2one('stock.move', help="MRP Component id")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    order_color_by_date = fields.Selection([
                                ('warning', 'Warning'),
                                ('red', 'Red'),
                                ('blue', 'Blue'),
                                ('green', 'Green'),
                                ], compute="compute_order_color_by_date", help="")
    is_pending = fields.Boolean('Pending', default=True)
    requisition_id = fields.Many2one('material.purchase.requisition', string="Requisition")

    @api.depends('scheduled_date', 'product_id')
    def compute_to_order_qty(self):
        """Compute method for get to order qty
            get forecasted qty and on hand aty based on schedule date
        """
        for record in self:
            scheduled_date = record.scheduled_date
            scheduled_date = fields.Date.to_string(scheduled_date) + " 23:59:59"     # add time to date
            scheduled_date = fields.Datetime.from_string(scheduled_date)

            product_qty = record.product_id._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), scheduled_date)
            # {'free_qty': 4.0, 'incoming_qty': 0.0, 'outgoing_qty': 6.0, 'qty_available': 10.0, 'virtual_available': 4.0}
            on_hand_qty = product_qty[record.product_id.id]['qty_available']
            forecasted_qty = product_qty[record.product_id.id]['virtual_available']
            other_records_same_product = self.search([('id', '!=', record.id), ('state', '!=', 'completed'), ('product_id', '=', record.product_id.id)])
            other_forecast = sum(other_records_same_product.mapped('forecasted_qty'))
            record.on_hand_qty = on_hand_qty
            record.forecasted_qty = forecasted_qty
            other_forecast = record.required_qty + forecasted_qty
            actual_to_order_qty = (record.required_qty - other_forecast) if other_forecast >= 0.00 else abs(forecasted_qty - other_forecast)
            record.actual_to_order_qty = actual_to_order_qty if actual_to_order_qty >= 0 else 0
            # if not record.to_order_qty:
            #     record.to_order_qty = record.actual_to_order_qty
            if not record.actual_to_order_qty:
                record.is_pending = False
            else:
                record.is_pending = True

    def compute_purchase_order(self):
        """Get related purchase orders"""
        for record in self:
            orders = False
            purchase = self.env['purchase.order.line'].search([('procurement_plan_ids', 'in', record.id)])
            if purchase:
                record.purchase_order_line_ids = [(6, 0, purchase.ids)]
                orders = purchase.mapped('order_id').ids
            record.purchase_order_ids = orders

    def compute_remaining_to_order(self):
        """compute method to get remaining qty to order
        """
        for record in self:
            record.remaining_to_order = record.to_order_qty - record.ordered_qty

    def compute_ordered_received_qty(self):
        """
            Calculate Order and received QTY
            Get Both qty from related purchase order line
            qty only calculate when purchase order in order state.
            Updating the state accordingly.
        """
        for record in self:
            record.ordered_qty = sum(record.purchase_order_line_ids.filtered(lambda line: line.order_id.state =='purchase').mapped('product_qty')) or 0.00
            record.received_qty = sum(record.purchase_order_line_ids.filtered(lambda line: line.order_id.state =='purchase').mapped('qty_received')) or 0.00
            record._compute_new_status()

    @api.depends('ordered_qty', 'received_qty')
    def _compute_pending_qty(self):
        for record in self:
            record.pending_qty = max((record.ordered_qty or 0.0) - (record.received_qty or 0.0), 0.0)

    def compute_order_color_by_date(self):
        """Technical method for colord in tree view
        """
        for record in self:
            current_date = fields.Date.today()
            color_configurations = self.sudo().env.company.procurement_plan_colors
            order_color_by_date = False
            if color_configurations:
                # ('on_date', 'On Date'), ('date_before_date', 'Date Before Date'), ('has_passed_date', 'Passed Date')
                on_date = color_configurations.filtered(lambda line: line.condition_type == 'on_date')
                date_before_date = color_configurations.filtered(lambda line: line.condition_type == 'date_before_date')
                has_passed_date = color_configurations.filtered(lambda line: line.condition_type == 'has_passed_date')
                partial_delivery = color_configurations.filtered(lambda line: line.condition_type == 'partial_delivery')

                if date_before_date and (record.scheduled_date - timedelta(days=date_before_date.no_of_dates)) < current_date < record.scheduled_date and record.state == 'draft':
                    # if scheduled date is between selected date and current date and without any update 'draft'
                    order_color_by_date = date_before_date.condition_colors

                elif on_date and current_date == record.scheduled_date and record.state == 'draft':
                    order_color_by_date = on_date.condition_colors

                elif has_passed_date and current_date > record.scheduled_date and record.state == 'draft':
                    order_color_by_date = has_passed_date.condition_colors

                elif has_passed_date and current_date > record.scheduled_date and record.ordered_qty == 0.00:
                    order_color_by_date = has_passed_date.condition_colors

                elif partial_delivery and record.delivery_status == 'partial':
                    order_color_by_date = partial_delivery.condition_colors

            record.order_color_by_date = order_color_by_date


    @api.depends('purchase_order_ids.state', 'received_qty')
    def _compute_new_status(self):
        """Compute New status based on state of purchase order"""

        for record in self:
            states = record.purchase_order_ids.mapped('state')

            if 'cancel' in states:
                record.new_status = 'pending_status'

            elif 'draft' in states or 'sent' in states or 'to approve' in states:
                record.new_status = 'rfq_created'

            elif 'purchase' in states or 'done' in states:
                record.new_status = 'po_created'
                if record.received_qty == 0:
                    record.new_status = 'po_created'
                elif record.ordered_qty > record.received_qty > 0:
                    record.new_status = 'partially_processed'
                else:
                    record.new_status = 'fully_processed'
            else:
                record.new_status = 'pending_status'


    @api.depends('scheduled_date', 'purchase_order_line_ids', 'purchase_order_line_ids.qty_received',
                 'purchase_order_line_ids.order_id.state')
    def compute_delivery_status(self):
        """Compute Delivery status from purchase order"""
        for record in self:
            state = 'draft'
            delivery_status = 'pending'
            is_pending = True

            # Remove or modify this block to avoid prematurely marking as completed
            # if not record.actual_to_order_qty:
            #     is_pending = False
            #     state = 'completed'

            if any(record.purchase_order_line_ids.mapped('order_id').filtered(lambda order: order.state == 'purchase')):
                # A purchase order exists so we mark the state as 'po'
                state = 'po'
                # Change condition: Only mark as completed if there was an order (ordered_qty > 0) and it has been fully received
                if record.ordered_qty > 0 and record.ordered_qty == record.received_qty:
                    state = 'completed'
                    delivery_status = 'completed'
                    is_pending = False
                elif record.received_qty > 0:
                    delivery_status = 'partial'
            elif any(record.purchase_order_line_ids.mapped('order_id').filtered(
                    lambda order: order.state in ('draft', 'sent'))):
                # If there's a quotation
                state = 'rfq'

            record.state = state
            record.delivery_status = delivery_status
            record.state_technical = True
            record.is_pending = is_pending

    @api.model
    def create(self, values):
        """Override Create method and add sequence to the plan
        """
        # if values.get('name') == 'New' or not values.get('name', False):
        #     values['name'] = self.env['ir.sequence'].sudo().next_by_code('procurement.plan')
        if values.get('product_id'):
            product = self.env['product.product'].browse([values.get('product_id')])
            # Get Vendor list from product template
            values['partner_ids'] = [(6, 0, product.seller_ids.mapped('partner_id').ids)] if product else [(6, 0, [])]
            values['lead_time'] = product.seller_ids[0].delay if product and product.seller_ids else 0.00

        responses = super().create(values)
        for response in responses:
            response.estimate_last_order_date()
            response.compute_delivery_status()
        return responses

    @api.onchange('partner_id')
    def get_supplier_details(self):
        """Get top supplier from product template"""
        if self.product_id and self.product_id.seller_ids and not self.partner_id:
            self.partner_id = self.product_id.seller_ids[0].partner_id
            self.partner_ids = [(6, 0,  self.product_id.seller_ids.mapped('partner_id').ids)]
        elif not self.partner_id:
            self.partner_id = False
            self.partner_ids = [(6, 0, [])]

    def get_vendor_lead_time_details(self):
        """Calculate lead time from vendor's configurations"""
        for record in self:
            lead_time = 0
            if record.partner_id and record.product_id:
                product_supplier = record.product_id.seller_ids.filtered(lambda line: line.partner_id.id == record.partner_id.id)
                if product_supplier:
                    lead_time += product_supplier[0].delay
            company_lead_time = record.company_id._get_security_by_rule_action()
            days_to_purchase = record.company_id.days_to_purchase
            if company_lead_time.get('buy'):
                lead_time += company_lead_time.get('buy')
            if days_to_purchase:
                lead_time += days_to_purchase

            record.lead_time = lead_time

    def estimate_last_order_date(self):
        """Calculate last delivery date
            last_order_date = scheduled_date - vendor's lead time - procurement security lead time
            Return:
            Assign calculated date to the last_order date
        """
        for record in self:
            last_order_date = record.scheduled_date - timedelta(days=record.lead_time or 0.00)
            record.order_last_date = last_order_date

    # def create_purchase_order(self):
    #     """action create RFQ for selected procurement line
    #     """
    #     if any(self.filtered(lambda record: record.state == 'completed')):
    #         raise ValidationError("There is/are Completed Procurement plan")
    #
    #     plan_lines = []
    #     for line in self:
    #         if not line.name:
    #             raise UserError(_("You cannot create RFQ without a Purchase Requisition."))
    #         vals = (0, 0, {
    #             'procurement_id': line.id,
    #             'order_qty': line.get_order_qty_for_rfq()
    #         })
    #         plan_lines.append(vals)
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'target': 'new',
    #         'name': _('Merge Procurement Plan'),
    #         'view_mode': 'form',
    #         'res_model': 'merge.procurementplan.wizard',
    #         'context': {
    #             'default_vendor_ids': self.partner_id.ids if self.partner_id else False,
    #             'procurement_plan_ids':plan_lines,
    #             'default_is_single_order': self.env.context.get('is_single_order', False),
    #
    #         },
    #     }
    def create_purchase_order(self):
        """Create RFQ for selected records
            if user select multiple vendors this will create multiple orders for
        """
        for record in self:
            if not record.partner_id:
                raise ValidationError("Select vendor(s) for create RFQ")
            if not record.name:
                raise ValidationError("Please ensure a purchase requisition is created before generating the request for quotation.")
        vendors = self.mapped('partner_id')
        for vendor in vendors:
            procurements = self.filtered(lambda x: x.partner_id.id == vendor.id)
            if procurements:
                purchase = {
                    'currency_id': self.env.user.company_id.currency_id.id,
                    'partner_id': vendor.id,
                    'date_order': fields.Date.today(),
                    'origin': ', '.join(list(dict.fromkeys(procurements.mapped('name')))),
                    'order_line': []
                }
                products = procurements.mapped('product_id')
                for product in products:
                    procurement = procurements.filtered(lambda x: x.product_id.id == product.id)
                    purchase['order_line'].append((0, 0, {
                        'procurement_plan_ids': [(4, line.id) for line in procurement],
                        'product_id': product.id,
                        'name': self.get_vendor_product_details(product, vendor),  # name should contain the formatted product name including product code
                        'product_uom': product.uom_id.id,
                        'price_unit': product.standard_price,
                        'product_qty': sum(procurement.mapped('remaining_to_order'))
                    }))
                order = self.env['purchase.order'].create(purchase)

            [record.compute_purchase_order() for record in self]

    @staticmethod
    def get_vendor_product_details(product, vendor):
        """
        Fetch the vendor-specific product name and product code.
        Format: "[Vendor Code] Vendor Product Name" (if code exists)
        :param product: The product record
        :param vendor: The vendor record (res.partner)
        :return: Formatted name including Vendor Product Code (if available)
        """
        seller = product._select_seller(
            partner_id=vendor,
            quantity=1,  # Default to 1 since procurement plans often define order quantity separately
            date=fields.Date.today(),  # Assume procurement date as today
            uom_id=product.uom_id
        )

        product_name = seller.product_name if seller and seller.product_name else product.display_name
        product_code = seller.product_code if seller and seller.product_code else ''

        if product_code:
            return f"[{product_code}] {product_name}"
        return product_name

        # purchase_order_obj = self.env['purchase.order']
        # for vendor in self.vendor_ids:
        #     if self.merge_procurement_plans:
        #         # if merge all lines to single order
        #         order_vals = self.return_purchase_order_vals(vendor)
        #         order_lines_by_product = {}
        #         for line in self.procurement_plan_ids:
        #             product_id, vals = self.return_purchase_order_line_vals(line)
        #             if product_id not in order_lines_by_product.keys():
        #                 order_lines_by_product[product_id] = vals
        #             else:
        #                 order_lines_by_product[product_id]['product_qty'] += vals['product_qty']
        #                 order_lines_by_product[product_id]['procurement_plan_ids'][0][2].extend(vals['procurement_plan_ids'][0][2])
        #                 order_lines_by_product[product_id]['date_planned'] = vals['date_planned'] if order_lines_by_product[product_id]['date_planned'] > vals['date_planned'] else order_lines_by_product[product_id]['date_planned']
        #             # order_vals['origin'] += line.procurement_id.source + ', '
        #         order_lines_vals = [(0, 0, val) for val in order_lines_by_product.values()]
        #         order_vals['order_line'].extend(order_lines_vals)
        #         purchase_order_obj.create(order_vals)
        #
        #     else:
        #         for line in self.procurement_plan_ids:
        #             order_vals = self.return_purchase_order_vals(vendor)
        #
        #             order_lines_by_product = {}
        #             product_id, vals = self.return_purchase_order_line_vals(line)
        #             if product_id not in order_lines_by_product.keys():
        #                 order_lines_by_product[product_id] = vals
        #             else:
        #                 order_lines_by_product[product_id]['product_qty'] += vals['product_qty']
        #                 order_lines_by_product[product_id]['procurement_plan_ids'][0][2].extend(vals['procurement_plan_ids'][0][2])
        #                 order_lines_by_product[product_id]['date_planned'] = vals['date_planned'] if order_lines_by_product[product_id]['date_planned'] > vals['date_planned'] else order_lines_by_product[product_id]['date_planned']
        #
        #             order_lines_vals = [(0, 0, val) for val in order_lines_by_product.values()]
        #             order_vals['order_line'].extend(order_lines_vals)
        #             order_vals['origin'] += 'Procurement Plan - ' + line.procurement_id.name
        #             purchase_order_obj.create(order_vals)

    # def return_purchase_order_vals(self, vendor):
    #     """Return values for 'purchase.order' """
    #     order_vals = {
    #             'partner_id': vendor.id,
    #             'origin': 'Procurement Plan - ',
    #             'order_line': [],
    #         }
    #     return order_vals
    #
    # def return_purchase_order_line_vals(self, procurement_plan):
    #     """Return values for 'purchase.order.line' """
    #     line_vals = (procurement_plan.product_id.id, {
    #         'procurement_plan_ids': [(6,0, [procurement_plan.procurement_id.id])],
    #         'product_id': procurement_plan.product_id.id,
    #         'product_qty': procurement_plan.order_qty,
    #         'product_uom': procurement_plan.product_uom.id,
    #         'date_planned': procurement_plan.scheduled_date,
    #     })
    #     return line_vals

    def open_related_purchase_order(self):
        """action create RFQ for selected procurement line"""

        return {
            'type': 'ir.actions.act_window',
            'target': 'current',
            'name': _('%s Purchase Order(s)' % (self.name +' / ') if self.name else ''),
            'view_mode': 'list,form',
            'res_model': 'purchase.order',
            'domain': [('id', 'in', self.purchase_order_line_ids.mapped('order_id').ids)]
        }

    def get_order_qty_for_rfq(self):
        """Return Product Required qty"""
        return self.remaining_to_order

    def action_cancel(self):
        """Override cancel button to cancel procument plan"""
        for plans in self:
            if plans.purchase_order_line_ids:
                for line in plans.purchase_order_line_ids:
                    if line.state not in ['draft', 'cancel']:
                        raise UserError(_("RFQ(s) related to the %s line", plans.product_id.display_name))
            plans.write({
                'state': 'cancel'
            })

    def create_purchase_requisition(self):
        name = self.env['ir.sequence'].next_by_code('procurement.plan')
        for record in self:
            if record.to_order_qty:
                if record.name:
                    raise UserError(_("There is a existing Purchase Requisition for this record."))
                if record.to_order_qty < record.actual_to_order_qty:
                    new_rec = record.copy()
                    record.required_qty = record.to_order_qty
                    new_rec.required_qty = record.actual_to_order_qty - record.to_order_qty
                    new_rec.to_order_qty = record.actual_to_order_qty - record.to_order_qty
                if name:
                    record.name = name
            else:
                raise UserError(_("Please add quantity to purchase."))

    def action_resync_suppliers(self):
        """
        Ensures the current record is single and updates the partner-related fields
        based on the product's supplier information. If the product has associated
        suppliers, it syncs the partner list and sets the primary partner.

        Args:
            None

        Returns:
            None
        """
        self.ensure_one()
        if self.product_id and self.product_id.seller_ids:
            self.partner_ids = [(6, 0, self.product_id.seller_ids.mapped('partner_id').ids)]
            self.partner_id = self.product_id.seller_ids[0].partner_id