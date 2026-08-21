from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class MaterialPurchaseRequisitionLine(models.Model):
    _name = "material.purchase.requisition.line"
    _description = 'Material Purchase Requisition Lines'

    requisition_id = fields.Many2one('material.purchase.requisition', string='Requisitions')
    product_code = fields.Char(string='Material Code', related="product_id.default_code")
    product_id = fields.Many2one('product.product', string='Material Name', required=True)
    description = fields.Char(string='Description', required=True)
    qty = fields.Float(string='Quantity', default=1, required=True)
    remaining_qty = fields.Float(string='Requested Qty', copy=False)
    extra_qty = fields.Float(string='Extra Qty', copy=False)
    uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    related_vendor_ids = fields.Many2many('res.partner', 'prequisition_line_partner_rel', 'partner_id', 'req_id', compute="compute_related_vendor_ids")
    partner_id = fields.Many2many('res.partner', string='Vendors')
    requisition_type = fields.Selection(selection=[('internal', 'Internal Picking'), ('purchase', 'Purchase Order'), ],
                                        string='Requisition Action', default='internal', required=True)
    dest_location_id = fields.Many2one('stock.location', string='Destination Location', required=False,
                                       compute="_compute_destination_location", store=True, copy=True)
    location_id = fields.Many2one('stock.location', string='Source Location', compute="_compute_source_location",
                                  store=True, copy=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', copy=True)
    stock_move_ids = fields.One2many(
        'stock.move', 'custom_requisition_line_id', string='Linked Stock Moves',
        help='All stock moves linked to this requisition line, including backorders and returns. '
             'Used for dependency tracking on ordered/received quantities.')
    state = fields.Selection(string="Line State", related='requisition_id.state')
    sent_procurement = fields.Boolean(string="Sent to Procurement", default=False)
    po_requisition_id = fields.Many2one('material.purchase.requisition.line', string='PO Requisition')
    pr_state = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partially Received'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled')
    ], string='Status', copy=False)
    received_qty = fields.Float(string='Received Qty', compute='_compute_pr_qty')
    ordered_qty = fields.Float(string='Ordered Qty', compute='_compute_pr_qty')
    requisition_created = fields.Boolean(string="Requisition Created", default=False)
    qty_available = fields.Float(related='product_id.qty_available', string='Quantity On Hand')
    virtual_available = fields.Float(related='product_id.virtual_available', string='Forecasted Quantity')
    qty_available_location = fields.Float(string='Qty at Source Location', compute='_compute_qty_available_location')
    is_picking_created = fields.Boolean(string='Is Picking Created', compute='_compute_is_picking_po_created')
    is_purchase_created = fields.Boolean(string='Is Picking Created', compute='_compute_is_picking_po_created')


    @api.depends('requisition_id.custom_picking_type_id')
    def _compute_source_location(self):
        """ Compute source location of the line based on the picking type of the requisition."""
        for rec in self:
            rec.location_id = rec.requisition_id.custom_picking_type_id.default_location_src_id.id

    @api.depends('requisition_id.custom_picking_type_id')
    def _compute_destination_location(self):
        """ Compute destination location of the line based on the picking type of the requisition."""
        for rec in self:
            rec.dest_location_id = rec.requisition_id.custom_picking_type_id.default_location_dest_id.id

    @api.depends('product_id', 'location_id')
    def _compute_qty_available_location(self):
        """OPTIMIZED: Raw SQL instead of ORM stock.quant search"""
        # Initialize defaults
        for rec in self:
            rec.qty_available_location = 0.0

        # Filter records that have both product and location
        records_with_data = self.filtered(lambda r: r.product_id and r.location_id)
        if not records_with_data:
            return

        # Collect unique product/location IDs
        product_ids = list(set(records_with_data.mapped('product_id').ids))
        location_ids = list(set(records_with_data.mapped('location_id').ids))

        # Raw SQL: single query with GROUP BY
        self.env.cr.execute("""
            SELECT product_id, location_id, SUM(quantity)
            FROM stock_quant
            WHERE product_id IN %s AND location_id IN %s
            GROUP BY product_id, location_id
        """, (tuple(product_ids), tuple(location_ids)))
        qty_by_key = {(row[0], row[1]): row[2] for row in self.env.cr.fetchall()}

        # Apply values using O(1) lookups
        for rec in records_with_data:
            key = (rec.product_id.id, rec.location_id.id)
            rec.qty_available_location = qty_by_key.get(key, 0.0)

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.display_name
            rec.uom = rec.product_id.uom_id.id

    @api.depends('product_id')
    def compute_related_vendor_ids(self):
        """OPTIMIZED: Batch fetch supplier info instead of N+1 seller_ids access"""
        # Initialize defaults
        for rec in self:
            rec.related_vendor_ids = [(5,)]

        records_with_product = self.filtered(lambda r: r.product_id)
        if not records_with_product:
            return

        # Collect all product template and product IDs
        product_tmpl_ids = records_with_product.mapped('product_id.product_tmpl_id').ids
        product_ids = records_with_product.mapped('product_id').ids

        # Single batch query for all supplier info
        all_suppliers = self.env['product.supplierinfo'].search([
            '|',
            '&', ('product_tmpl_id', 'in', product_tmpl_ids), ('product_id', '=', False),
            ('product_id', 'in', product_ids),
        ])

        # Group partner_ids by (product_tmpl_id, product_id) for O(1) lookup
        vendors_by_tmpl = {}  # product_tmpl_id → set of partner_ids
        vendors_by_product = {}  # product_id → set of partner_ids
        for supplier in all_suppliers:
            if supplier.product_id:
                vendors_by_product.setdefault(supplier.product_id.id, set()).add(supplier.partner_id.id)
            else:
                vendors_by_tmpl.setdefault(supplier.product_tmpl_id.id, set()).add(supplier.partner_id.id)

        for rec in records_with_product:
            vendor_ids = set()
            # Template-level sellers
            tmpl_id = rec.product_id.product_tmpl_id.id
            if tmpl_id in vendors_by_tmpl:
                vendor_ids.update(vendors_by_tmpl[tmpl_id])
            # Variant-level sellers
            prod_id = rec.product_id.id
            if prod_id in vendors_by_product:
                vendor_ids.update(vendors_by_product[prod_id])
            if vendor_ids:
                rec.related_vendor_ids = [(6, 0, list(vendor_ids))]

    def send_to_pr(self):
        """OPTIMIZED: Batch fetch procurement plans instead of search per record"""
        # Filter purchase-type records
        purchase_records = self.filtered(lambda r: r.requisition_type == 'purchase')
        if not purchase_records:
            return

        # Collect lookup keys for batch query
        product_ids = set()
        sources = set()
        for record in purchase_records:
            if record.product_id:
                product_ids.add(record.product_id.id)
            if record.requisition_id and record.requisition_id.job_costing_id:
                sources.add(record.requisition_id.job_costing_id.display_name)

        # BATCH QUERY: Fetch all potentially matching procurement plans
        domain = [('product_id', 'in', list(product_ids))]
        if sources:
            domain.append(('source', 'in', list(sources)))
        all_procurement_plans = self.env['procurement.plan'].search(domain)

        # Group by (scheduled_date, source, product_id) for O(1) lookup
        plans_by_key = {}
        for plan in all_procurement_plans:
            key = (plan.scheduled_date, plan.source, plan.product_id.id)
            if key not in plans_by_key:
                plans_by_key[key] = plan

        # Process records using pre-fetched data
        procurement_obj = self.env['procurement.plan']
        for record in purchase_records:
            # Build lookup key
            scheduled_date = record.scheduled_date.date() if hasattr(record.scheduled_date, 'date') else record.scheduled_date
            source = record.requisition_id.job_costing_id.display_name if record.requisition_id and record.requisition_id.job_costing_id else False
            key = (scheduled_date, source, record.product_id.id)

            procurement_line = plans_by_key.get(key)
            if procurement_line:
                procurement_line.requisition_id = record.requisition_id.id
                if procurement_line.actual_to_order_qty < record.qty:
                    procurement_line.required_qty = record.qty
                    procurement_line.to_order_qty += record.extra_qty
                record.send_to_procurement_email()
                record.sent_procurement = True
            else:
                source_name = record.requisition_id.name
                vals = {
                    'product_id': record.product_id.id,
                    'product_tml_id': record.product_id.product_tmpl_id.id if record.product_id.product_tmpl_id else False,
                    'mrp_id': False,
                    'source': source_name,
                    'product_uom': record.uom.id,
                    'required_qty': (record.qty + record.extra_qty),
                    'component_id': False,
                    'scheduled_date': record.scheduled_date,
                    'company_id': record.requisition_id.company_id.id,
                    'partner_ids': record.partner_id.ids,
                    'requisition_id': record.requisition_id.id,
                }
                procurement_line = procurement_obj.create(vals)
                if procurement_line:
                    record.send_to_procurement_email()
                    record.sent_procurement = True

    @api.model
    def send_to_procurement_email(self):
        """OPTIMIZED: Cache env.ref and get_param outside loop"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        users = self.env.ref('material_purchase_requisitions.group_purchase_requisition_email').users
        email_to = ', '.join([user.email for user in users if user.email])
        email_from = self.env.user.email
        template_id = self.env.ref('material_purchase_requisitions.purchase_requisition_line_email_notification')

        for line in self:
            req = line.requisition_id
            url = base_url + '/web?login/#id=' + str(req.id) + '&view_type=form&model=material.purchase.requisition'

            # Build line details for the table
            line_details = []
            for idx, rl in enumerate(req.requisition_line_ids | req.purchase_line_ids, 1):
                line_details.append({
                    'serial': idx,
                    'code': rl.product_code or '-',
                    'product': rl.product_id.name or 'N/A',
                    'description': rl.description or '-',
                    'qty': f"{rl.qty:,.2f}",
                    'uom': rl.uom.name if rl.uom else 'N/A',
                })

            context = {
                'subject': f"Purchase Requisition - {req.name}",
                'heading': "Purchase Requisition",
                'receiver': "User",
                'mr_name': req.name or 'N/A',
                'mr_employee': req.employee_id.name if req.employee_id else 'N/A',
                'mr_department': req.department_id.name if req.department_id else 'N/A',
                'mr_date': str(req.request_date) if req.request_date else 'N/A',
                'mr_project': req.mp_project_id.name if hasattr(req, 'mp_project_id') and req.mp_project_id else False,
                'mr_analytic': req.analytic_account_id.name if req.analytic_account_id else False,
                'mr_mo': req.mrp_id.name if req.mrp_id else False,
                'email_from': email_from,
                'email_to': email_to,
                'custom_url': url,
                'line_details': line_details,
            }
            template_id.with_context(context).send_mail(line.id, force_send=True)

    @api.depends(
        'requisition_type', 'qty',
        # Internal type: stock moves linked via custom_requisition_line_id (incl. backorders & returns)
        'stock_move_ids.state',
        'stock_move_ids.quantity_done',
        'stock_move_ids.product_qty',
        'stock_move_ids.origin_returned_move_id',
        # Purchase type: POs created from the parent requisition
        'requisition_id.purchase_order_ids.state',
        'requisition_id.purchase_order_ids.order_line.product_qty',
        'requisition_id.purchase_order_ids.order_line.qty_received',
    )
    def _compute_pr_qty(self):
        """OPTIMIZED: Raw SQL instead of ORM N+1 computed fields (ordered_qty/received_qty on procurement.plan).

        Handles picking cancel / return correctly:
          - Internal: excludes return moves (origin_returned_move_id IS NOT NULL) from ordered_qty,
            and subtracts done return-move quantities from received_qty. Cancelled moves are skipped.
          - Purchase: relies on purchase.order.line.qty_received, which Odoo recomputes when a
            receipt picking is cancelled or returned (to_refund). PO state 'done' is also included
            so locked POs do not zero out the totals.
        """
        # Initialize all records with defaults
        for record in self:
            record.received_qty = 0
            record.ordered_qty = 0
            record.pr_state = False

        if not self.ids:
            return

        # Separate records by type for batch processing
        purchase_records = self.filtered(lambda r: r.requisition_type == 'purchase')
        internal_records = self.filtered(lambda r: r.requisition_type == 'internal')

        # SQL for purchase type: procurement.plan → M2M → purchase.order.line → purchase.order
        # M2M columns are SWAPPED: po_line_id = procurement_plan.id, proc_id = purchase_order_line.id
        if purchase_records:
            requisition_ids = purchase_records.mapped('requisition_id').ids
            if requisition_ids:
                self.env.cr.execute("""
                    SELECT pp.requisition_id,
                           COALESCE(SUM(pol.product_qty) FILTER (WHERE po.state IN ('purchase', 'done')), 0) AS ordered_qty,
                           COALESCE(SUM(pol.qty_received) FILTER (WHERE po.state IN ('purchase', 'done')), 0) AS received_qty
                    FROM procurement_plan pp
                    JOIN purchase_line_procurement_rel plpr ON plpr.po_line_id = pp.id
                    JOIN purchase_order_line pol ON pol.id = plpr.proc_id
                    JOIN purchase_order po ON po.id = pol.order_id
                    WHERE pp.requisition_id IN %s
                    GROUP BY pp.requisition_id
                """, (tuple(requisition_ids),))
                qty_by_requisition = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}

                for record in purchase_records:
                    data = qty_by_requisition.get(record.requisition_id.id)
                    if data:
                        ordered_qty, received_qty = data
                        record.ordered_qty = ordered_qty
                        record.received_qty = received_qty
                        if received_qty == 0:
                            record.pr_state = 'pending'
                        elif record.qty <= received_qty:
                            record.pr_state = 'done'
                        elif ordered_qty > received_qty:
                            record.pr_state = 'partial'
                        else:
                            record.pr_state = 'pending'

        # SQL for internal type: stock.move grouped by custom_requisition_line_id.
        # Forward moves (origin_returned_move_id IS NULL) contribute to ordered_qty and received_qty.
        # Return moves (origin_returned_move_id IS NOT NULL) do not affect ordered_qty and SUBTRACT
        # their quantity_done from received_qty once they are 'done'. Cancelled moves are skipped.
        if internal_records:
            internal_ids = internal_records.ids
            if internal_ids:
                self.env.cr.execute("""
                    SELECT custom_requisition_line_id,
                           COALESCE(SUM(
                               CASE
                                   WHEN origin_returned_move_id IS NULL THEN quantity_done
                                   WHEN state = 'done' THEN -quantity_done
                                   ELSE 0
                               END
                           ), 0) AS received_qty,
                           COALESCE(SUM(product_qty) FILTER (WHERE origin_returned_move_id IS NULL), 0) AS ordered_qty
                    FROM stock_move
                    WHERE custom_requisition_line_id IN %s AND state != 'cancel'
                    GROUP BY custom_requisition_line_id
                """, (tuple(internal_ids),))
                qty_by_line = {row[0]: (row[1], row[2]) for row in self.env.cr.fetchall()}

                for record in internal_records:
                    data = qty_by_line.get(record.id)
                    if data:
                        received_qty, ordered_qty = data
                        record.received_qty = received_qty
                        record.ordered_qty = ordered_qty
                        if received_qty == 0:
                            record.pr_state = 'pending'
                        elif record.qty <= received_qty:
                            record.pr_state = 'done'
                        elif ordered_qty > received_qty:
                            record.pr_state = 'partial'
                        else:
                            record.pr_state = 'pending'

    def create_picking_po(self):
        for record in self:
            requisition_vals = {
                'requisition_type': 'internal',
                'requisition_id': record.requisition_id.id,
                'product_id': record.product_id.id,
                'description': record.description,
                'qty': record.qty,
                'uom': record.uom.id,
                'pr_state': False,
                'po_requisition_id': record.id
            }
            if record.pr_state == 'done':
                record.requisition_created = True
            else:
                record.requisition_created = False
            requisition_line = self.create(requisition_vals)

    def create_picking(self):
        self.requisition_id.request_stock(self)

    @api.onchange('remaining_qty')
    def _onchange_remaining_qty(self):
        if self.remaining_qty >= 0:
            self.qty = self.remaining_qty

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.product_id.action_product_forecast_report()
        action['context'] = {
            'active_id': self.product_id.id,
            'active_model': 'product.product',
        }
        return action

    def action_view_picking(self):
        """OPTIMIZED: Use proper domain instead of search([]).filtered()"""
        # Direct search with domain - much faster than loading all records
        moves = self.env['stock.move'].search([
            ('custom_requisition_line_id', '=', self.id)
        ])
        picking = moves.mapped('picking_id')
        res = {
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
        }
        if len(picking) == 1:
            res.update({
                'view_mode': 'form',
                'res_id': picking.id,
            })
        else:
            res.update({
                'name': _("%s Pickings") % self.product_id.display_name,
                'domain': [('id', 'in', picking.ids)],
                'view_mode': 'tree,form',
            })
        return res

    def action_view_purchase(self):
        """OPTIMIZED: Use proper domain instead of search([]).filtered()"""
        # Direct search with domain - much faster than loading all records
        po_lines = self.env['purchase.order.line'].search([
            ('custom_requisition_line_id', '=', self.id)
        ])
        purchase = po_lines.mapped('order_id')
        res = {
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
        }
        if len(purchase) == 1:
            res.update({
                'view_mode': 'form',
                'res_id': purchase.id,
            })
        else:
            res.update({
                'name': _("%s RFQs") % self.product_id.display_name,
                'domain': [('id', 'in', purchase.ids)],
                'view_mode': 'tree,form',
            })
        return res

    def _compute_is_picking_po_created(self):
        """OPTIMIZED: Replaced search([]).filtered() with batched domain-based queries"""
        # Initialize defaults
        for record in self:
            record.is_picking_created = False
            record.is_purchase_created = False

        if not self.ids:
            return

        # Separate records by type
        internal_records = self.filtered(lambda r: r.requisition_type == 'internal')
        purchase_records = self.filtered(lambda r: r.requisition_type == 'purchase')

        # BATCH QUERY for internal records - check if picking exists
        if internal_records:
            internal_ids = internal_records.ids
            # Single query with proper domain
            moves_with_picking = self.env['stock.move'].search([
                ('custom_requisition_line_id', 'in', internal_ids),
                ('picking_id', '!=', False)
            ])
            # Build set of line IDs that have pickings
            lines_with_picking = set(moves_with_picking.mapped('custom_requisition_line_id').ids)
            for record in internal_records:
                record.is_picking_created = record.id in lines_with_picking

        # BATCH QUERY for purchase records - check if PO exists
        if purchase_records:
            purchase_ids = purchase_records.ids
            # Single query with proper domain
            po_lines = self.env['purchase.order.line'].search([
                ('custom_requisition_line_id', 'in', purchase_ids),
                ('order_id', '!=', False)
            ])
            # Build set of line IDs that have POs
            lines_with_po = set(po_lines.mapped('custom_requisition_line_id').ids)
            for record in purchase_records:
                record.is_purchase_created = record.id in lines_with_po
