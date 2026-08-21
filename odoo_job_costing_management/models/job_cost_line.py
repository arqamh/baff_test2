import logging
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class JobCostLine(models.Model):
    _name = 'job.cost.line'
    _description = 'Job Cost Line'
    _rec_name = 'product_id'
    _order = "material_index,labour_index"

    job_costing_id = fields.Many2one('job.costing', string='Job Costing')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    work_center_id = fields.Many2one('mrp.workcenter', string='Work Center')
    product_id = fields.Many2one('product.product', string='Raw Material', copy=False)
    job_type_id = fields.Many2one('job.type', string='Job Type')
    description = fields.Char(string='Description', copy=False)
    reference = fields.Char(string='Reference', copy=False)
    available_for_production_team = fields.Boolean(string="Available for Production Team")
    uom_id = fields.Many2one('uom.uom', string='Uom')
    cost_price = fields.Float(string='Cost / Unit', copy=False)
    cost_price_company_currency = fields.Float(string='Cost / Unit (Company Currency)', compute='_compute_cost_price_company_currency', store=True, copy=False)

    supplier_currency_id = fields.Many2one('res.currency', string='Supplier Currency', copy=False)
    supplier_currency_rate = fields.Float(string='Supplier Currency Rate', copy=False)
    is_same_currency_id = fields.Boolean(string='Is Same Currency', compute='_compute_is_same_currency_id', store=True)

    cost_price_per_hour = fields.Float(string='Total Cost per Hour', copy=False, compute='_compute_total_cost_hours')
    # Leaf-line cost, owned solely by _compute_total_cost.
    total_cost = fields.Float(string='Sub Total', compute='_compute_total_cost', store=True)
    # Rolled-up subtotal for parent/BOM header lines, written by
    # job.costing._compute_material_total during its sheet-wide pass (only when
    # lines actually change, not on read). Kept separate from total_cost so the
    # two are never written by two different computes (which caused write-on-read
    # UPDATEs and "could not serialize access due to concurrent update").
    rollup_cost = fields.Float(string='Sub Total', copy=False)
    # Single value shown in the "Sub Total" column: the roll-up for parent/BOM
    # header rows, the leaf cost otherwise. NON-STORED (computed in-memory on
    # read) so displaying it never writes to the DB.
    display_total_cost = fields.Float(string='Sub Total', compute='_compute_display_total_cost')
    currency_id = fields.Many2one('res.currency', string='Currency', related='job_costing_id.currency_id')
    job_type = fields.Selection(selection=[('material', 'Material'), ('labour', 'Labour'), ('overhead', 'Overhead')],
                                string="Type", required=True)
    basis = fields.Char(string='Basis')
    hours = fields.Float(string='Total Hours')
    hour = fields.Float(string='Hours')
    qty = fields.Float(string='Quantity')
    purchase_order_line_ids = fields.One2many('purchase.order.line', 'job_cost_line_id')
    timesheet_line_ids = fields.One2many('account.analytic.line', 'job_cost_line_id')
    account_invoice_line_ids = fields.One2many('account.move.line', 'job_cost_line_id')
    actual_invoice_quantity = fields.Float(string='Actual Vendor Bill Quantity',
                                           compute='_compute_actual_invoice_quantity')
    actual_hour = fields.Float(string='Actual Timesheet Hours', compute='_compute_actual_hour')

    product_qty = fields.Float(string='Planned Quantity', copy=False)
    original_product_qty = fields.Float(string='Original Planned Quantity', copy=False,
                                        help="Exploded quantity captured when the line was first created from the "
                                             "standard BOM. Used to translate edited quantities back to the per-parent "
                                             "BOM line quantity (ratio sync) when generating the manufacturing BOM.")
    actual_quantity = fields.Float(string='Supplied Quantity', compute='_compute_qty_fields')
    # Plain stored, writable field (NOT computed). Stateful quantity: starts at
    # product_qty, decremented/zeroed when a PR is created, restored on reset
    # (material_purchase_requisitions). Was a stored compute driven by
    # _compute_qty_fields, which rewrote it on every read (write_date bump) and
    # caused "could not serialize access due to concurrent update". Kept stored so
    # the "To Order Qty" search-view domain filter keeps working.
    to_order_quantity = fields.Float(string='To Order', copy=False, default=0.0)
    # Live-derived by _compute_qty_fields. NON-STORED so the compute runs
    # in-memory on read and never writes to the DB (write-on-read → serialization
    # conflict). Nothing writes these externally.
    remaining_qty = fields.Float(string='Required Qty', copy=False, compute='_compute_qty_fields')
    pr_created_qty = fields.Float(string='PR Created Qty', copy=False, compute='_compute_qty_fields')
    actual_remaining_qty = fields.Float(string='Remaining Qty', copy=False, compute='_compute_qty_fields')
    po_created_qty = fields.Float(string='PO Created Qty', copy=False, invisible=True, compute='_compute_qty_fields')
    extra_qty = fields.Float(string='Extra Qty', copy=False, compute='_compute_qty_fields')

    prepared_by = fields.Many2one('res.users', compute="_compute_prepared_by", store=True)
    checked_by = fields.Many2one('res.users', string="Checked By", store=True)
    approved_by = fields.Many2one('res.users', string="Approved By", store=True)
    priority = fields.Selection(related="job_costing_id.priority")
    # Direct MO link — populated when production is approved per-finished-good.
    # Was previously a `related='job_costing_id.mrp_id'` shim against the now-
    # removed sheet-level mrp_id; kept as a real Many2one so mrp.production's
    # cost_analysis_line One2many keeps resolving.
    mrp_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    is_new_item = fields.Boolean(string="Is new item", default=False)

    mrp_qty = fields.Float(string="Actual Qty", compute="_compute_mrp_fields")
    mrp_time = fields.Float(string="Actual Hrs", compute="_compute_mrp_fields")
    mrp_cost = fields.Float(string="Unit Price", compute="_compute_mrp_fields")
    budget_cost = fields.Float(string="Budget Cost", compute="_compute_budget_cost")
    actual_cost = fields.Float(string="Actual Cost", compute="_compute_actual_cost")
    qty_variance = fields.Float(string="Qty Difference", compute="_compute_variance_fields")
    unit_cost_variance = fields.Float(string="Unit Cost Difference", compute="_compute_variance_fields")
    total_cost_variance = fields.Float(string="Total Cost Difference", compute="_compute_variance_fields")
    internal_move_id = fields.One2many('stock.move', 'job_cost_line_id')
    cost_center_dependency = fields.Boolean(string="Produced from Cost Center")
    estimation_buffer = fields.Boolean(string="Estimation Buffer", default=False)
    operation_id = fields.Many2one('mrp.workorder', string="Operation")
    bom_operation_id = fields.Many2one('mrp.routing.workcenter', string="Operation")
    slot_id = fields.Many2one('planning.slot', string="Planning Slot")
    parent_bom_id = fields.Many2one('mrp.bom', string="Parent BOM")
    bom_id = fields.Many2one('mrp.bom', string="BOM")
    material_index = fields.Char(string="Index")
    labour_index = fields.Char(string="Index")
    material_type = fields.Char(string="Type")
    component = fields.Char(string="Component")
    sequence = fields.Integer(default=0)
    workcenter_cost_price = fields.Float(string='Workcenter Cost per Hour', copy=False)
    employee_cost_price = fields.Float(string='Employee Cost per Hour', copy=False)
    related_vendor_ids = fields.Many2many('res.partner', 'job_line_partner_rel', 'partner_id', 'job_line_id', compute="compute_related_vendor_ids")
    partner_id = fields.Many2one('res.partner', string="Vendor")
    selected = fields.Boolean(string="Selected")
    boat_type_id = fields.Many2one('boat.type', string="Type of Boat", related='job_costing_id.boat_type_id')
    inventory_location_id = fields.Many2one('stock.location', string="Part Location", related='product_id.property_stock_inventory')
    product_category_id = fields.Many2one('product.category', string="Article Category", related='product_id.categ_id')
    product_code = fields.Char(string="Article Code", related='product_id.default_code')
    vendor_reference = fields.Char(string="Supplier Reference", compute='_compute_vendor_reference', store=True, compute_sudo=True, precompute=True)
    new_line = fields.Boolean(string="New Line", default=False)
    operation_start_date = fields.Datetime(string="Scheduled Start Date")
    operation_end_date = fields.Datetime(string="Scheduled End Date")
    scheduled_date = fields.Datetime(string="Scheduled Date")
    status = fields.Selection([('pending', 'Pending'), ('partial', 'Partially Received'), ('completed', 'Completed')],
                              compute='_compute_qty_fields')
    line_type = fields.Selection([('material', 'Material'), ('component', 'Component')])
    labour_line_type = fields.Boolean(string="Labour Line Type", defalt=False)
    is_include_report = fields.Boolean(string="Is Included In Report")
    bom_line_id = fields.Many2one(comodel_name='mrp.bom.line', string="BOM Line")
    date = fields.Date(string="Date", related="job_costing_id.complete_date" )
    calculate_bom_total = fields.Boolean(string="Calculate BOM Total", compute='_compute_calculate_bom_total')

    # def _compute_scheduled_date(self):
    #     for record in self:
    #         if record.mrp_id:
    #             record.scheduled_date = record.mrp_id.date_planned_start
    #         else:
    #             record.scheduled_date = False
    # def _compute_line_type(self):
    #     job_costing = False
    #     for record in self:
    #         record.line_type = False
    #         job_costing = record.job_costing_id
    #     line_type = self.env.context.get('default_line_type')
    #     if line_type:
    #         if line_type == 'component':
    #             job_costing.line_type = 'component'
    #         elif line_type == 'material':
    #             job_costing.line_type = 'material'

    @api.depends('partner_id', 'product_id')
    def _compute_vendor_reference(self):
        """
        Optimized vendor reference computation with batch prefetching.
        Eliminates N+1 queries by prefetching all seller_ids in batch.
        """
        # Initialize all records with False
        for record in self:
            record.vendor_reference = False

        # Only process records with both partner and product
        records_with_data = self.filtered(lambda r: r.partner_id and r.product_id)
        if not records_with_data:
            return

        # Collect unique product template IDs and partner IDs
        product_tmpl_ids = set()
        product_ids = set()
        partner_ids = set()
        for record in records_with_data:
            product_tmpl_ids.add(record.product_id.product_tmpl_id.id)
            product_ids.add(record.product_id.id)
            partner_ids.add(record.partner_id.id)

        # BATCH QUERY: Fetch all supplier info for these products/partners
        all_supplier_info = self.env['product.supplierinfo'].search([
            '|',
            ('product_tmpl_id', 'in', list(product_tmpl_ids)),
            ('product_id', 'in', list(product_ids)),
            ('partner_id', 'in', list(partner_ids))
        ])

        # Build lookup dictionary: (product_tmpl_id, partner_id) -> product_name
        vendor_ref_by_tmpl = {}
        vendor_ref_by_product = {}
        for supplier in all_supplier_info:
            if supplier.product_name:
                if supplier.product_id:
                    key = (supplier.product_id.id, supplier.partner_id.id)
                    if key not in vendor_ref_by_product:
                        vendor_ref_by_product[key] = supplier.product_name
                if supplier.product_tmpl_id:
                    key = (supplier.product_tmpl_id.id, supplier.partner_id.id)
                    if key not in vendor_ref_by_tmpl:
                        vendor_ref_by_tmpl[key] = supplier.product_name

        # Apply vendor references using O(1) lookups
        for record in records_with_data:
            # First check product-specific vendor reference
            key = (record.product_id.id, record.partner_id.id)
            if key in vendor_ref_by_product:
                record.vendor_reference = vendor_ref_by_product[key]
                continue
            # Fall back to template-level vendor reference
            key = (record.product_id.product_tmpl_id.id, record.partner_id.id)
            if key in vendor_ref_by_tmpl:
                record.vendor_reference = vendor_ref_by_tmpl[key]

    @api.depends('product_id')
    def compute_related_vendor_ids(self):
        """OPTIMIZED: Batch prefetch all seller_ids to eliminate N+1 queries"""
        # Initialize all records
        for rec in self:
            rec.related_vendor_ids = [(5,)]
        records_with_product = self.filtered(lambda r: r.product_id and r.line_type == 'material')
        if not records_with_product:
            return
        # Batch prefetch: access all products' seller_ids and variant_seller_ids in bulk
        all_products = records_with_product.mapped('product_id')
        all_tmpl = all_products.mapped('product_tmpl_id')
        all_tmpl_ids = all_tmpl.ids
        all_product_ids = all_products.ids
        # Single query for all supplier info records
        all_supplier_info = self.env['product.supplierinfo'].search([
            '|',
            ('product_tmpl_id', 'in', all_tmpl_ids),
            ('product_id', 'in', all_product_ids),
        ])
        # Group partner IDs by product_tmpl_id and product_id
        vendors_by_tmpl = {}
        vendors_by_product = {}
        for si in all_supplier_info:
            if si.product_tmpl_id:
                vendors_by_tmpl.setdefault(si.product_tmpl_id.id, set()).add(si.partner_id.id)
            if si.product_id:
                vendors_by_product.setdefault(si.product_id.id, set()).add(si.partner_id.id)
        # Apply using O(1) lookups
        for rec in records_with_product:
            vendor_ids = set()
            tmpl_vendors = vendors_by_tmpl.get(rec.product_id.product_tmpl_id.id)
            if tmpl_vendors:
                vendor_ids.update(tmpl_vendors)
            product_vendors = vendors_by_product.get(rec.product_id.id)
            if product_vendors:
                vendor_ids.update(product_vendors)
            if vendor_ids:
                rec.related_vendor_ids = [(6, 0, list(vendor_ids))]

    def _compute_qty_fields(self):
        """Compute (NON-STORED, in-memory) the live quantity/status fields from
        requisition/PO/stock data via SQL.

        NOTE: must NOT write to_order_quantity — that is a plain stored,
        workflow-managed field, not a computed one. Writing it here would clobber
        its state on read and cause write-on-read serialization conflicts.
        """
        # Initialize all records with defaults
        for record in self:
            record.actual_quantity = 0
            record.po_created_qty = 0
            record.pr_created_qty = 0
            record.remaining_qty = record.product_qty
            record.actual_remaining_qty = 0
            record.extra_qty = 0
            record.status = 'pending'

        if not self.ids:
            return

        cr = self.env.cr
        ids_tuple = tuple(self.ids)

        # Defaults so a SQL failure degrades to the initialized values instead of
        # poisoning the request transaction.
        purchase_data = {}  # {job_cost_line_id: {purchased_qty, po_requested_qty}}
        internal_requested = {}
        internal_transfer = {}

        # Savepoint-guard the raw SQL: a failure rolls back locally and is logged
        # rather than aborting the request and surfacing later as an opaque
        # InFailedSqlTransaction on an unrelated field read.
        try:
            with cr.savepoint():
                # SQL 1: Get all purchase-type requisition lines with their key fields
                cr.execute("""
                    SELECT rl.id, rl.job_cost_line_id, rl.requisition_id, rl.product_id, rl.remaining_qty
                    FROM material_purchase_requisition_line rl
                    WHERE rl.job_cost_line_id IN %s
                      AND rl.requisition_type = 'purchase'
                """, (ids_tuple,))
                purchase_lines_raw = cr.fetchall()

                # SQL 2: Get procurement plan ordered/received quantities via PO lines
                # Group by (requisition_id, product_id) to match the ORM lookup key
                req_ids = set()
                prod_ids = set()
                for row in purchase_lines_raw:
                    req_ids.add(row[2])
                    prod_ids.add(row[3])

                proc_plans_by_key = {}
                if req_ids and prod_ids:
                    cr.execute("""
                        SELECT pp.requisition_id,
                               pp.product_id,
                               COALESCE(SUM(pol.product_qty) FILTER (WHERE po.state = 'purchase'), 0) AS ordered_qty,
                               COALESCE(SUM(pol.qty_received) FILTER (WHERE po.state = 'purchase'), 0) AS received_qty
                        FROM procurement_plan pp
                        JOIN purchase_line_procurement_rel plpr ON plpr.po_line_id = pp.id
                        JOIN purchase_order_line pol ON pol.id = plpr.proc_id
                        JOIN purchase_order po ON po.id = pol.order_id
                        WHERE pp.requisition_id IN %s
                          AND pp.product_id IN %s
                        GROUP BY pp.requisition_id, pp.product_id
                    """, (tuple(req_ids), tuple(prod_ids)))
                    for row in cr.fetchall():
                        proc_plans_by_key[(row[0], row[1])] = {'ordered_qty': row[2], 'received_qty': row[3]}

                # Process purchase lines per job_cost_line_id
                for row in purchase_lines_raw:
                    _, jcl_id, req_id, product_id, remaining_qty = row
                    if jcl_id not in purchase_data:
                        purchase_data[jcl_id] = {'purchased_qty': 0, 'po_requested_qty': 0}
                    plan = proc_plans_by_key.get((req_id, product_id))
                    if plan:
                        purchase_data[jcl_id]['purchased_qty'] += plan['received_qty']
                        purchase_data[jcl_id]['po_requested_qty'] += plan['ordered_qty']
                    else:
                        purchase_data[jcl_id]['po_requested_qty'] += remaining_qty

                # SQL 3: Get internal transfer data — remaining_qty per job_cost_line_id
                cr.execute("""
                    SELECT rl.job_cost_line_id,
                           SUM(rl.remaining_qty) AS it_requested_qty
                    FROM material_purchase_requisition_line rl
                    WHERE rl.job_cost_line_id IN %s
                      AND rl.requisition_type = 'internal'
                    GROUP BY rl.job_cost_line_id
                """, (ids_tuple,))
                internal_requested = {row[0]: row[1] for row in cr.fetchall()}

                # SQL 4: Get stock move quantity_done minus returned quantity_done for internal lines
                cr.execute("""
                    SELECT rl.job_cost_line_id,
                           SUM(sm.quantity_done - COALESCE(ret.return_qty, 0)) AS transfer_qty
                    FROM material_purchase_requisition_line rl
                    JOIN stock_move sm ON sm.id = rl.move_id
                    LEFT JOIN LATERAL (
                        SELECT COALESCE(SUM(rsm.quantity_done), 0) AS return_qty
                        FROM stock_move rsm
                        WHERE rsm.origin_returned_move_id = sm.id
                    ) ret ON TRUE
                    WHERE rl.job_cost_line_id IN %s
                      AND rl.requisition_type = 'internal'
                      AND rl.move_id IS NOT NULL
                    GROUP BY rl.job_cost_line_id
                """, (ids_tuple,))
                internal_transfer = {row[0]: row[1] for row in cr.fetchall()}
        except Exception:
            _logger.exception(
                "job.cost.line._compute_qty_fields: quantity SQL failed for ids %s; "
                "falling back to default quantities", ids_tuple)

        # Process each record using SQL-fetched data
        for record in self:
            rid = record.id
            p_data = purchase_data.get(rid, {})
            purchased_qty = p_data.get('purchased_qty', 0)
            po_requested_qty = p_data.get('po_requested_qty', 0)
            it_requested_qty = internal_requested.get(rid, 0)
            internal_transfer_qty = internal_transfer.get(rid, 0)

            record.actual_quantity = purchased_qty + internal_transfer_qty
            record.po_created_qty = po_requested_qty
            record.pr_created_qty = it_requested_qty + po_requested_qty
            record.remaining_qty = (record.product_qty - record.actual_quantity) - record.po_created_qty
            extra_qty = record.pr_created_qty - record.product_qty
            actual_remaining_qty = record.pr_created_qty - record.actual_quantity
            record.actual_remaining_qty = max(actual_remaining_qty, 0)
            record.extra_qty = max(extra_qty, 0)

            if record.product_qty > record.actual_quantity > 0:
                record.status = 'partial'
            elif record.product_qty <= record.actual_quantity:
                record.status = 'completed'
            else:
                record.status = 'pending'

    @api.depends('job_costing_id', 'product_qty', 'remaining_qty')
    def _compute_prepared_by(self):
        """Get prepared User from costing Sheet"""
        for rec in self:
            if rec.job_costing_id:
                rec.prepared_by = rec.job_costing_id.user_id
            else:
                rec.prepared_by = False

    def _compute_mrp_fields(self):
        """Consolidated computation for mrp_qty, mrp_time, and mrp_cost - OPTIMIZED

        Eliminates N+1 queries by:
        1. Batching all sale_order_ids from records
        2. Single search for all manufacturing orders
        3. Pre-grouping moves and workorders by sale_order_id
        4. Computing all three fields in one pass
        """
        # Initialize defaults
        for record in self:
            record.mrp_qty = 0
            record.mrp_time = 0
            record.mrp_cost = 0

        if not self.ids:
            return

        # Get unique sale_order_ids from all records' job_costing_id.sale_id
        sale_order_ids = set()
        records_by_sale_order = {}
        for record in self:
            if record.job_costing_id and record.job_costing_id.sale_id:
                so_id = record.job_costing_id.sale_id.id
                sale_order_ids.add(so_id)
                if so_id not in records_by_sale_order:
                    records_by_sale_order[so_id] = []
                records_by_sale_order[so_id].append(record)

        if not sale_order_ids:
            return

        # SINGLE BATCH QUERY for all manufacturing orders
        manufacturing_orders = self.env['mrp.production'].search([
            ('sale_order_id', 'in', list(sale_order_ids))
        ])

        if not manufacturing_orders:
            return

        # Group MOs by sale_order_id for O(1) lookup
        mos_by_sale_order = {}
        for mo in manufacturing_orders:
            so_id = mo.sale_order_id.id
            if so_id not in mos_by_sale_order:
                mos_by_sale_order[so_id] = self.env['mrp.production']
            mos_by_sale_order[so_id] |= mo

        # Pre-fetch related data in batch
        all_moves = manufacturing_orders.mapped('move_raw_ids')
        all_workorders = manufacturing_orders.mapped('workorder_ids')

        # Build lookup dictionaries for moves by jobcost_line_id
        moves_by_jobcost_line = {}
        for move in all_moves:
            if move.bom_line_id and move.bom_line_id.jobcost_line_id:
                jcl_id = move.bom_line_id.jobcost_line_id.id
                if jcl_id not in moves_by_jobcost_line:
                    moves_by_jobcost_line[jcl_id] = self.env['stock.move']
                moves_by_jobcost_line[jcl_id] |= move

        # Build lookup dictionaries for workorders by jobcost_line_id
        workorders_by_jobcost_line = {}
        for wo in all_workorders:
            if wo.operation_id and wo.operation_id.jobcost_line_id:
                jcl_id = wo.operation_id.jobcost_line_id.id
                if jcl_id not in workorders_by_jobcost_line:
                    workorders_by_jobcost_line[jcl_id] = self.env['mrp.workorder']
                workorders_by_jobcost_line[jcl_id] |= wo

        # Cache company OT rates
        company = self.env.company
        holiday_ot = getattr(company, 'holiday_ot', 0)
        saturday_ot = getattr(company, 'saturday_ot', 0)
        working_days_ot = getattr(company, 'working_days_ot', 0)

        # BATCH: Pre-fetch all stock valuation layers for material moves
        material_move_ids = []
        for jcl_id, moves in moves_by_jobcost_line.items():
            material_move_ids.extend(moves.ids)

        valuation_by_move = {}
        if material_move_ids:
            # OPTIMIZED: Raw SQL instead of ORM search + Python iteration.
            # Savepoint-guarded so a SQL failure degrades to the planned-cost
            # fallback below instead of poisoning the request transaction.
            try:
                with self.env.cr.savepoint():
                    self.env.cr.execute("""
                        SELECT stock_move_id,
                               SUM(ABS(value)) AS total_value,
                               SUM(ABS(quantity)) AS total_qty
                        FROM stock_valuation_layer
                        WHERE stock_move_id IN %s
                        GROUP BY stock_move_id
                    """, (tuple(material_move_ids),))
                    for row in self.env.cr.fetchall():
                        valuation_by_move[row[0]] = {'value': row[1], 'quantity': row[2]}
            except Exception:
                _logger.exception(
                    "job.cost.line._compute_mrp_fields: stock valuation SQL failed "
                    "for moves %s; falling back to planned cost", material_move_ids)

        # Process records
        for record in self:
            # MRP Quantity (materials only)
            if record.job_type == 'material':
                moves = moves_by_jobcost_line.get(record.id)
                if moves:
                    record.mrp_qty = sum(moves.mapped('quantity_done'))
                    # Calculate mrp_cost from stock valuation layers (actual cost at consumption time)
                    total_value = 0
                    total_qty = 0
                    for move in moves:
                        if move.id in valuation_by_move:
                            total_value += valuation_by_move[move.id]['value']
                            total_qty += valuation_by_move[move.id]['quantity']
                    # Unit cost = total value / total quantity
                    if total_qty > 0:
                        record.mrp_cost = total_value / total_qty
                    else:
                        # Fallback to planned cost if no valuation layer exists
                        record.mrp_cost = record.cost_price_company_currency

            # MRP Time and Cost (labour only)
            elif record.job_type == 'labour':
                workorder = record.operation_id or workorders_by_jobcost_line.get(record.id)
                if workorder:
                    # Handle recordset vs single record
                    if hasattr(workorder, '__iter__') and len(workorder) > 1:
                        workorder = workorder[0]

                    if workorder and workorder.time_ids:
                        mrp_time = 0
                        total_cost = 0
                        total_lines = len(workorder.time_ids)

                        for time_entry in workorder.time_ids:
                            # Calculate time
                            if time_entry.workcenter_id == record.work_center_id:
                                mrp_time += time_entry.duration / 60
                            elif not getattr(time_entry, 'slot_id', False) or not time_entry.slot_id.work_center_id:
                                mrp_time += time_entry.duration / 60

                            # Calculate cost with OT
                            if time_entry.date_start:
                                end_of_day = datetime(
                                    time_entry.date_start.year,
                                    time_entry.date_start.month,
                                    time_entry.date_start.day, 17, 0, 0
                                ) - timedelta(seconds=19800)

                                if time_entry.date_start > end_of_day:
                                    weekday = time_entry.date_start.weekday()
                                    if weekday == 6:
                                        ot_rate = holiday_ot
                                    elif weekday == 5:
                                        ot_rate = saturday_ot
                                    else:
                                        ot_rate = working_days_ot

                                    if ot_rate and time_entry.employee_id:
                                        total_cost += ot_rate * time_entry.employee_id.hourly_cost
                                    else:
                                        total_cost += record.cost_price
                                else:
                                    total_cost += record.cost_price

                        record.mrp_time = mrp_time
                        record.mrp_cost = total_cost / total_lines if total_lines else 0

    def _compute_budget_cost(self):
        """Per-line budget cost (NON-STORED, in-memory).

        Must NOT write the parent job.costing.total_budget_cost: that was a
        write-on-read on job_costing and caused "could not serialize access due
        to concurrent update". The parent total is now a proper stored compute
        on job.costing (_compute_total_budget_cost).
        """
        for record in self:
            if record.job_type == 'material':
                record.budget_cost = record.product_qty * record.cost_price_company_currency
            elif record.job_type == 'labour':
                record.budget_cost = record.hour * record.cost_price_company_currency
            else:
                record.budget_cost = 0.0

    def _compute_actual_cost(self):
        """Per-line actual cost (NON-STORED, in-memory).

        Uses mrp_cost (derived from stock valuation layers). Must NOT write the
        parent job.costing.total_actual_cost nor the stored estimation_buffer:
        those were write-on-read on job_costing/job_cost_line and caused
        serialization conflicts. The parent total is now a stored compute on
        job.costing (_compute_total_actual_cost).
        """
        for record in self:
            if record.job_type == 'material':
                record.actual_cost = record.mrp_qty * record.mrp_cost
            elif record.job_type == 'labour':
                record.actual_cost = record.mrp_time * record.mrp_cost
            else:
                record.actual_cost = 0.0

    def _compute_variance_fields(self):
        for record in self:
            if record.job_type == 'material':
                record.qty_variance = record.product_qty - record.mrp_qty
            elif record.job_type == 'labour':
                record.qty_variance = record.hour - record.mrp_time
            else:
                record.qty_variance = 0.0
            record.unit_cost_variance = record.cost_price_company_currency - record.mrp_cost
            record.total_cost_variance = record.budget_cost - record.actual_cost

    @api.onchange('product_id', 'work_center_id', 'partner_id')
    def _onchange_product_id(self):
        """Onchange workcenter, product_id set values to description, costs."""
        if self.work_center_id and self.job_type == 'labour':
            self.description = "Charges of %s" % self.work_center_id.name
            self.hour = 1
            self.workcenter_cost_price = self.work_center_id.costs_hour
            self.employee_cost_price = self.employee_id.hourly_cost if self.employee_id else self.work_center_id.employee_costs_hour
        elif self.product_id and self.job_type in ['material', 'overhead']:
            self.description = self.product_id.name
            self.product_qty = 1.0
            self.uom_id = self.product_id.uom_id.id
            self.cost_price = self.product_id.standard_price
        if self.product_id:
            if self.product_id.bom_ids:
                if self.product_id.bom_ids[0]:
                    if self.product_id.bom_ids.analytic_plan_id.id != self.job_costing_id.analytic_plan_id.id:
                        self.cost_center_dependency = True
            vendors = False
            if self.partner_id:
                vendors = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                    ('partner_id', '=', self.partner_id.id)
                ]).sorted('job_cost_price')[:1]
            else:
                vendors = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)
                ]).sorted('job_cost_price')[:1]
            if vendors:
                self.partner_id = vendors[0].partner_id.id
                self.supplier_currency_id = vendors[0].currency_id.id
                self.supplier_currency_rate = vendors[0].currency_id.inverse_rate
                self.cost_price = vendors[0].job_cost_price
            elif self.product_id.last_purchase_price:
                self.cost_price = self.product_id.last_purchase_price
            elif self.product_id.standard_price:
                self.cost_price = self.product_id.standard_price
            # Notification of the Last Purchase Date Price of the product
            if self.product_id.last_purchase_date and self.product_id.last_purchase_price:
                return {'warning': {
                    'title': _('Last Purchase Price and Date'),
                    'message': _('The last purchase date of this product is %s and the last purchase price is %s',
                                 self.product_id.last_purchase_date, self.product_id.last_purchase_price)
                }}


    @api.depends('product_qty', 'hour', 'cost_price', 'job_costing_id', 'qty', 'employee_cost_price',
                 'workcenter_cost_price', 'supplier_currency_rate', 'cost_price_per_hour')
    def _compute_total_cost(self):
        """ Calculation of total cost based on product, quantity and unit prices.

        IMPORTANT: This compute must write ONLY total_cost (the field it owns).
        It previously also wrote product_qty / hour / supplier_currency_rate, which
        turned every read/recompute into an UPDATE on job_cost_line and caused
        "could not serialize access due to concurrent update" under concurrency.
        Those normalizations are now done locally, without writing them back.
        """
        for rec in self:
            if rec.job_type == 'labour':
                rec.total_cost = rec.hour * rec.cost_price_per_hour
            else:
                rate = rec.supplier_currency_rate or 1
                rec.total_cost = rec.product_qty * (rec.cost_price * rate)

    @api.depends('total_cost', 'rollup_cost', 'material_type')
    def _compute_display_total_cost(self):
        """Value for the 'Sub Total' column: roll-up for parent/BOM header rows,
        leaf cost otherwise. Non-stored — never writes to the DB on read."""
        for rec in self:
            if rec.material_type in ('bom', 'parent'):
                rec.display_total_cost = rec.rollup_cost
            else:
                rec.display_total_cost = rec.total_cost

    def _compute_calculate_bom_total(self):
        """Compute the calculate_bom_total flag ONLY.

        This is a NON-STORED compute that fires on every read of the materials
        tree. It must NOT write total_cost (or any other stored field): doing so
        turned each read into an UPDATE on job_cost_line and caused
        "could not serialize access due to concurrent update" under concurrency.
        The BOM/header roll-up subtotal is owned by
        job.costing._compute_material_total (written to rollup_cost) and shown via
        display_total_cost — this method no longer duplicates it.
        """
        for rec in self:
            rec.calculate_bom_total = False

    @api.depends('purchase_order_line_ids', 'purchase_order_line_ids.product_qty',
                 'purchase_order_line_ids.order_id.state')
    def _compute_actual_quantity(self):
        """Compute and update qty from purchased amount and internal transferred qty"""
        for rec in self:
            purchased_quantity = sum(
                [p.order_id.state in ['purchase', 'done'] and p.qty_received for p in rec.purchase_order_line_ids])
            internal_transferred_qty = sum([moves.quantity_done for moves in rec.internal_move_id])
            actual_quantity = purchased_quantity + internal_transferred_qty
            rec.actual_quantity = actual_quantity
            rec.remaining_qty = rec.product_qty - actual_quantity

    @api.depends('timesheet_line_ids', 'timesheet_line_ids.unit_amount')
    def _compute_actual_hour(self):
        """calculate hour quantity"""
        for rec in self:
            rec.actual_hour = sum([p.unit_amount for p in rec.timesheet_line_ids])

    @api.depends('account_invoice_line_ids', 'account_invoice_line_ids.quantity',
                 'account_invoice_line_ids.move_id.state', 'account_invoice_line_ids.move_id.payment_state')
    def _compute_actual_invoice_quantity(self):
        """calculate invoiced quantity"""
        for rec in self:
            rec.actual_invoice_quantity = sum([p.quantity or 0.0 for p in rec.account_invoice_line_ids if
                                               p.move_id.state in ['posted'] or p.move_id.payment_state in ['paid']])

    @api.onchange('job_type_id')
    def onchange_job_type_id(self):
        """Flagging whether the job is for production team"""
        self.available_for_production_team = self.job_type_id.available_for_production_team

    @api.depends('actual_quantity', 'product_qty')
    def _compute_remaining_qty(self):
        """Compute remaining quantity
            remaining quantity = product_qty - actual_quantity
        """
        for line in self:
            line.remaining_qty = line.product_qty - line.actual_quantity

    def create_purchase_requisitions_wizard(self):
        """ Server Actions: get selected job costing lines and return a wizard for purchase requisitions """
        job_cost_lines = self.filtered(lambda line: line.to_order_quantity > 0)

        if job_cost_lines:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            source = job_cost_lines.mapped('job_costing_id')
            job_cost = False
            if source:
                if len(source) == 1:
                    job_cost = source.id

            requisitions_vals = {
                'employee_id': employee_id.id if employee_id else False,
                'default_task_user_id': self.env.user.id,
                'default_mp_project_id': self.job_costing_id.project_id.id,
                'default_job_costing_id': job_cost if job_cost else False,
                'default_requisition_line_ids': []
            }

            for cost_line in job_cost_lines:
                requisitions_vals['default_requisition_line_ids'].append((0, 0, {
                    'product_id': cost_line.product_id.id,
                    'description': cost_line.description if cost_line.description else cost_line.product_id.display_name,
                    'uom': cost_line.uom_id.id,
                    'remaining_qty': cost_line.to_order_quantity,
                    'qty': cost_line.to_order_quantity,
                    'scheduled_date': cost_line.scheduled_date,
                    'required_quantity': cost_line.to_order_quantity,
                    'job_costing_id': cost_line.job_costing_id.id,
                    'job_cost_line_id': cost_line.id,
                    'parent_bom_id': cost_line.parent_bom_id.id if cost_line.parent_bom_id else cost_line.bom_line_id.bom_id.id,
                    'parent_bom_name': cost_line.parent_bom_id.name if cost_line.parent_bom_id else cost_line.bom_line_id.bom_id.display_name,
                }))

            address_form_id = self.env.ref('material_purchase_requisitions.material_purchase_requisition_form_view').id
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Purchase Requisitions',
                'res_model': 'material.purchase.requisition',
                'views': [(address_form_id, 'form')],
                'view_mode': 'form',
                'target': 'current',
                'context': requisitions_vals
            }

            return action

    @api.depends('employee_cost_price', 'workcenter_cost_price')
    def _compute_total_cost_hours(self):
        """ Calculating total hours in a labour line """
        for record in self:
            record.cost_price_per_hour = record.employee_cost_price + record.workcenter_cost_price

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        pass

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Onchange employee_id set values to employee costs."""
        if self.employee_id and self.job_type == 'labour':
            self.employee_cost_price = self.employee_id.hourly_cost if self.employee_id else self.work_center_id.employee_costs_hour

    def change_supplier(self, product_ids=None):
        products = product_ids if product_ids else False
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        lines = []
        vendors = []
        if products:
            # OPTIMIZED: Batch fetch all supplier info instead of filtered() per record
            product_tmpl_ids = [r.product_id.product_tmpl_id.id for r in products if r.product_id]
            partner_ids = [r.partner_id.id for r in products if r.partner_id]
            all_sellers = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', 'in', product_tmpl_ids),
                ('partner_id', 'in', partner_ids),
            ]) if product_tmpl_ids and partner_ids else self.env['product.supplierinfo']
            # Build dict keyed by (product_tmpl_id, partner_id) for O(1) lookup
            seller_by_key = {}
            for s in all_sellers:
                key = (s.product_tmpl_id.id, s.partner_id.id)
                if key not in seller_by_key:
                    seller_by_key[key] = s

            for record in products:
                if record.product_id:
                    seller = seller_by_key.get(
                        (record.product_id.product_tmpl_id.id, record.partner_id.id)
                    ) if record.partner_id else None
                    lines.append((0, 0, {
                        'product_id': record.product_id.id,
                        'partner_id': record.partner_id.id,
                        'job_costing_price': seller.job_cost_price if seller else False,
                        'lead_time': seller.delay if seller else False,
                        'job_cost_line_id': record.id,
                    }))
                    if record.partner_id:
                        if record.partner_id.id not in vendors:
                            vendors.append(record.partner_id.id)

        return {
            'name': _('Change Supplier'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'change.supplier.wizard',
            'target': 'new',
            'context': {
                'vendors': self.partner_id.ids,
                'default_model_id': model.id,
                'default_current_supplier_id': vendors[0] if len(vendors) == 1 else False,
                'default_current_supplier_product_line': lines if lines else False,
            }
        }

    @api.depends('supplier_currency_id', 'job_costing_id.customer_currency_id')
    def _compute_is_same_currency_id(self):
        """Check if the customer and supplier currency are the same"""
        for record in self:
            record.is_same_currency_id = record.supplier_currency_id == record.job_costing_id.customer_currency_id

    @api.depends('cost_price', 'supplier_currency_id')
    def _compute_cost_price_company_currency(self):
        """Convert cost_price from supplier currency to company base currency
        OPTIMIZED: Cache company currency and date to avoid repeated lookups"""
        # Cache these values outside the loop
        company_currency = self.env.company.currency_id
        company = self.env.company
        today = fields.Date.today()

        # Pre-fetch exchange rates for all currencies in batch
        supplier_currencies = self.filtered(lambda r: r.supplier_currency_id and r.cost_price).mapped('supplier_currency_id')
        # This triggers rate caching for all currencies at once
        if supplier_currencies:
            for currency in supplier_currencies:
                # Access rate to cache it (Odoo caches rates after first access)
                _ = currency.rate

        for record in self:
            if record.supplier_currency_id and record.cost_price:
                # Convert from supplier currency to company currency (uses cached rates)
                record.cost_price_company_currency = record.supplier_currency_id._convert(
                    record.cost_price,
                    company_currency,
                    company,
                    today
                )
            elif record.cost_price:
                # If no supplier currency is set, assume it's already in company currency
                record.cost_price_company_currency = record.cost_price
            else:
                record.cost_price_company_currency = 0.0

    def unlink(self):
        """Keep the job-cost BOM in sync when a cost line is removed.

        Deleting a line on the sheet also removes the BOM artefacts that were
        generated from it: the linked BOM line (snapshot/standard-derived
        component), any BOM lines created from this line (new components and
        parent materials) and any routing operations. Only BOMs that belong to a
        job costing sheet are touched, never a standard BOM.
        """
        bom_lines = self.mapped('bom_line_id').filtered(lambda b: b.bom_id.job_cost_id)
        bom_lines |= self.env['mrp.bom.line'].search([
            ('jobcost_line_id', 'in', self.ids),
            ('bom_id.job_cost_id', '!=', False),
        ])
        routings = self.env['mrp.routing.workcenter'].search([
            ('jobcost_line_id', 'in', self.ids),
            ('bom_id.job_cost_id', '!=', False),
        ])
        if bom_lines:
            bom_lines.unlink()
        if routings:
            routings.unlink()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals):
        results = super().create(vals)
        # Initialize the stateful "To Order" quantity for new lines that didn't
        # get an explicit value: it starts equal to the planned quantity and is
        # later decremented/restored by the purchase-requisition workflow.
        # (to_order_quantity is a plain stored field, not computed.)
        for result, val in zip(results, vals):
            if 'to_order_quantity' not in val and result.product_qty:
                result.to_order_quantity = result.product_qty
        # Map each newly added line individually so that adding several
        # materials/components at once (the web client batches them into a
        # single create call) gets the same component/index mapping as adding a
        # single line. Lines that already carry their mapping were built
        # internally (BOM explosion below, action_add_component, record copy)
        # and must not be reprocessed.
        for result in results:
            if result.material_index or result.labour_index \
                    or result.material_type or result.component:
                continue
            if result.bom_id and result.job_type == 'material':
                parent = False
                component = ''
                if result.parent_bom_id:
                    parent = self.search([
                        ('job_costing_id', '=', result.job_costing_id.id),
                        ('bom_id', '=', result.parent_bom_id.id),
                        ('id', '!=', result.id),
                        ('material_type', 'in', ['bom', 'parent'])
                    ], limit=1)
                    if parent:
                        components = self.search([
                            ('job_costing_id', '=', result.job_costing_id.id),
                            ('parent_bom_id', '=', parent.bom_id.id),
                            ('material_type', '=', 'component'),
                            ('material_index', '!=', False)
                        ], order='material_index desc', limit=1)
                        if components:
                            material_index = components.material_index
                            length = len(material_index)
                            last_value = int(material_index[length - 1])
                            last_value += 1
                            result.material_index = material_index[:-1] + str(last_value)
                            result.sequence = components.sequence + 1
                        else:
                            result.material_index = parent.material_index + str(0)
                            result.sequence = parent.sequence + 1

                        component += parent.component + '/'
                    component += result.bom_id.name if result.bom_id.name else result.bom_id.display_name

                result.material_type = 'bom'
                result.component = component
                if result.bom_id.product_id:
                    result.product_id = result.bom_id.product_id.id
                elif result.bom_id.product_tmpl_id.product_variant_count == 1:
                    if result.bom_id.product_tmpl_id.product_variant_id:
                        result.product_id = result.bom_id.product_tmpl_id.product_variant_id.id
                    else:
                        raise UserError(_("Please map the relevant product variant in the BOM record."))
                elif result.bom_id.product_tmpl_id.product_variant_count > 1:
                    raise UserError(_("There are multiple product variants related to this BOM. "
                                      "Please map the relevant variant in the BOM record."))
                else:
                    result.product_id = result.bom_id.product_tmpl_id.id
                # result.product_qty = result.bom_id.product_qty
                result.uom_id = result.bom_id.product_uom_id.id
                result.parent_bom_id = result.bom_id.parent_component_id.id
                result.new_line = True
                lines = []
                if result.bom_id.bom_line_ids:
                    count = 0
                    sequence = result.sequence + 1
                    index = False

                    # OPTIMIZED: Batch fetch all vendor info for BOM line products
                    bom_product_tmpl_ids = result.bom_id.bom_line_ids.mapped('product_tmpl_id').ids
                    all_vendors = self.env['product.supplierinfo'].search([
                        ('product_tmpl_id', 'in', bom_product_tmpl_ids)
                    ], order='product_tmpl_id, job_cost_price')
                    # Group by product_tmpl_id, keeping only cheapest (first due to ordering)
                    vendor_by_tmpl = {}
                    for v in all_vendors:
                        if v.product_tmpl_id.id not in vendor_by_tmpl:
                            vendor_by_tmpl[v.product_tmpl_id.id] = v

                    for material in result.bom_id.bom_line_ids:
                        # Use pre-fetched vendor data
                        vendor = vendor_by_tmpl.get(material.product_tmpl_id.id)
                        if vendor:
                            cost = vendor.job_cost_price
                        else:
                            cost = material.product_id.last_purchase_price if material.product_id.last_purchase_price \
                                else material.product_id.standard_price

                        lines.append({
                            'job_costing_id': result.job_costing_id.id,
                            'sequence': sequence,
                            'material_index': result.material_index + str(count),
                            'bom_id': False,
                            'parent_bom_id': result.bom_id.id,
                            'component': result.component,
                            'material_type': 'component',
                            'product_id': material.product_id.id,
                            'product_qty': material.product_qty * result.product_qty,
                            'original_product_qty': material.product_qty * result.product_qty,
                            'uom_id': material.product_uom_id.id,
                            'job_type': 'material',
                            'partner_id': vendor.partner_id.id if vendor else False,
                            'cost_price': cost,
                        })
                        count += 1
                        sequence += 1
                if result.bom_id.operation_ids:
                    components = self.search([
                        ('job_costing_id', '=', result.job_costing_id.id),
                        ('parent_bom_id', '=', parent.bom_id.id),
                        ('job_type', '=', 'labour'),
                        ('labour_index', '!=', False)
                    ], order='labour_index desc', limit=1)
                    if components:
                        labour_index = components.labour_index
                        length = len(labour_index)
                        last_value = int(labour_index[length - 1])
                        last_value += 1
                        index = labour_index[:-1] + str(last_value)
                    else:
                        components = self.search([
                            ('job_costing_id', '=', result.job_costing_id.id),
                            ('bom_id', '=', parent.bom_id.id),
                            ('job_type', '=', 'labour'),
                            ('labour_index', '!=', False)
                        ], order='labour_index desc', limit=1)
                        if components:
                            index = components.labour_index
                    count = 0
                    sequence = components.sequence if components else result.sequence + 1
                    for labour in result.bom_id.operation_ids:
                        lines.append({
                            'job_costing_id': result.job_costing_id.id,
                            'labour_index': index + str(count),
                            'sequence': sequence,
                            # 'job_type_id': line.get('operation').workcenter_id.id,
                            'component': result.component,
                            'bom_id': result.bom_id.id,
                            'parent_bom_id': parent.bom_id.id,
                            'work_center_id': labour.workcenter_id.id,
                            'bom_operation_id': labour.id,
                            'hour': (labour.time_cycle / 60 * result.product_qty) if labour.time_cycle else 0,
                            'workcenter_cost_price': labour.workcenter_id.costs_hour if labour.workcenter_id else 0,
                            'job_type': 'labour',
                        })
                        count += 1
                        sequence += 1
                if lines:
                    self.create(lines)
            elif result.parent_bom_id and result.product_id:
                parent = self.search([
                    ('job_costing_id', '=', result.job_costing_id.id),
                    ('bom_id', '=', result.parent_bom_id.id),
                    ('id', '!=', result.id),
                    ('material_type', 'in', ['bom', 'parent'])
                ], limit=1)
                if parent:
                    components = self.search([
                        ('job_costing_id', '=', result.job_costing_id.id),
                        ('parent_bom_id', '=', parent.bom_id.id),
                        ('job_type', '=', 'material'),
                        ('id', '!=', result.id),
                        ('material_index', '!=', False)
                    ], order='material_index desc', limit=1)
                    if components:
                        material_index = components.material_index
                        length = len(material_index)
                        last_value = int(material_index[length - 1])
                        last_value += 1
                        result.material_index = material_index[:-1] + str(last_value)
                        result.sequence = components.sequence + 1

                result.component = parent.component
                result.material_type = 'component'
                result.new_line = True
            elif result.bom_id and result.work_center_id and result.job_type == 'labour':
                operations = self.search([
                    ('job_costing_id', '=', result.job_costing_id.id),
                    ('bom_id', '=', result.bom_id.id),
                    ('job_type', '=', 'labour'),
                    ('id', '!=', result.id),
                    ('labour_index', '!=', False)
                ], order='labour_index desc', limit=1)
                if operations:
                    labour_index = operations.labour_index
                    length = len(labour_index)
                    last_value = int(labour_index[length - 1])
                    last_value += 1
                    result.labour_index = labour_index[:-1] + str(last_value)
                    result.sequence = operations.sequence + 1
                    result.parent_bom_id = operations.parent_bom_id.id
                    result.component = operations.component
                    result.new_line = True
        results.line_type = False
        results.labour_line_type = False
        return results

    @api.onchange('operation_end_date', 'operation_start_date')
    def _onchange_operation_start_end_date(self):
        """ Checking whether the operation start date is greater than the operation end date"""
        for record in self:
            if record.operation_end_date and record.operation_start_date:
                if record.operation_start_date > record.operation_end_date:
                    raise UserError(_("Start date of the operation can't be higher that end date."))

    def action_change_product_supplier(self, vendor, price):
        """Unchecking whether the selected boolean field after the supplier change confirm"""
        self.partner_id = vendor.id
        self.cost_price = price if price else False
        self.selected = False
