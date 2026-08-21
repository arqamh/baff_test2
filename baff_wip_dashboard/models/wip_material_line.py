from odoo import _, api, fields, models, tools


class WipMaterialLine(models.Model):
    _name = 'wip.material.line'
    _description = 'WIP Material Line (one row per ongoing MO x component)'
    _auto = False
    _order = 'production_name desc, product_id asc'

    id = fields.Integer(readonly=True)

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    production_name = fields.Char(string='MO Reference', readonly=True)
    mo_state = fields.Selection([
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
    ], string='MO State', readonly=True)
    mo_product_id = fields.Many2one('product.product', string='Finished Product', readonly=True)
    mo_planned_qty = fields.Float(string='Planned Qty', readonly=True, digits='Product Unit of Measure')
    mo_start_date = fields.Datetime(string='Start Date', readonly=True)
    mo_finish_date = fields.Datetime(string='Expected Finish', readonly=True)
    main_location_id = fields.Many2one('stock.location', string='Main Location', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    current_workcenter_id = fields.Many2one('mrp.workcenter', string='Current Work Center', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    product_id = fields.Many2one('product.product', string='Component', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Component Template', readonly=True)
    category_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)

    required_qty = fields.Float(string='Required Qty', readonly=True, digits='Product Unit of Measure')
    consumed_qty = fields.Float(string='Consumed Qty', readonly=True, digits='Product Unit of Measure')
    remaining_qty = fields.Float(string='Remaining Qty', readonly=True, digits='Product Unit of Measure')
    allocated_qty = fields.Float(string='Allocated', readonly=True, digits='Product Unit of Measure',
                                 help='Reserved on raw-material moves, not yet consumed.')
    available_main_qty = fields.Float(string='Available (Main Loc)', readonly=True,
                                      digits='Product Unit of Measure',
                                      help='Unreserved stock at the MO source location.')
    available_other_qty = fields.Float(string='Available Elsewhere', readonly=True,
                                       digits='Product Unit of Measure',
                                       help='Unreserved stock at other internal locations of the same company.')
    gap_qty = fields.Float(string='Gap (To Be Requested)', readonly=True,
                           digits='Product Unit of Measure',
                           help='Remaining − Allocated, floored at zero.')
    availability_status = fields.Selection([
        ('fully_allocated', 'Fully Allocated'),
        ('stock_available', 'Stock Available'),
        ('insufficient', 'Missing / To Be Requested'),
    ], string='Availability', readonly=True)

    # Phase 3: Procurement status.
    has_material_request = fields.Boolean(
        string='Request Raised', readonly=True,
        help='An active material purchase requisition exists for this component.')
    po_ordered_qty = fields.Float(
        string='PO Ordered', readonly=True, digits='Product Unit of Measure',
        help='Total quantity ordered on confirmed POs for this component (all companies scoped to MO).')
    po_received_qty = fields.Float(
        string='PO Received', readonly=True, digits='Product Unit of Measure')
    pending_receipt_qty = fields.Float(
        string='Pending Receipt', readonly=True, digits='Product Unit of Measure',
        help='PO Ordered − PO Received.')
    procurement_status = fields.Selection([
        ('none', 'No Request'),
        ('requested', 'Request Raised'),
        ('po_created', 'PO Created'),
        ('partial_received', 'Partially Received'),
        ('fully_received', 'Fully Received'),
    ], string='Procurement Status', readonly=True)

    # Phase 2: Value fields (non-stored, computed on read).
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        compute='_compute_currency', readonly=True)
    unit_cost = fields.Monetary(
        string='Unit Cost', compute='_compute_values', readonly=True,
        currency_field='currency_id',
        help='Current standard price for the product in the MO company.')
    consumed_value = fields.Monetary(
        string='Consumed Value', compute='_compute_values', readonly=True,
        currency_field='currency_id',
        help='Historical value of consumed materials, from stock valuation layers when '
             'available, otherwise consumed_qty * current unit cost.')
    allocated_value = fields.Monetary(
        string='Allocated Value', compute='_compute_values', readonly=True,
        currency_field='currency_id',
        help='Allocated qty * current unit cost.')
    wip_value = fields.Monetary(
        string='WIP Value', compute='_compute_values', readonly=True,
        currency_field='currency_id',
        help='Consumed value + allocated value.')

    # Phase 2: Variant/BOM indicators.
    is_variant = fields.Boolean(
        string='Variant Component', compute='_compute_is_variant',
        search='_search_is_variant',
        help='True if the component template has more than one variant.')

    @api.depends('company_id')
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id or self.env.company.currency_id

    @api.depends('product_id', 'company_id', 'production_id',
                 'consumed_qty', 'allocated_qty')
    def _compute_values(self):
        # Batch-fetch historical consumed value from stock.valuation.layer.
        consumed_by_key = self._fetch_consumed_values()
        # Batch-fetch per-(product, company) unit cost.
        unit_cost_by_key = self._fetch_unit_costs()
        for rec in self:
            cost_key = (rec.product_id.id, rec.company_id.id)
            unit_cost = unit_cost_by_key.get(cost_key, 0.0)
            rec.unit_cost = unit_cost
            consumed_val = consumed_by_key.get(
                (rec.production_id.id, rec.product_id.id))
            if consumed_val is None:
                consumed_val = rec.consumed_qty * unit_cost
            rec.consumed_value = consumed_val
            rec.allocated_value = rec.allocated_qty * unit_cost
            rec.wip_value = rec.consumed_value + rec.allocated_value

    def _fetch_consumed_values(self):
        """Return dict {(production_id, product_id): abs_value} from SVL."""
        production_ids = self.mapped('production_id').ids
        if not production_ids:
            return {}
        self._cr.execute("""
            SELECT sm.raw_material_production_id, svl.product_id, SUM(-svl.value)
            FROM stock_valuation_layer svl
            JOIN stock_move sm ON sm.id = svl.stock_move_id
            WHERE sm.raw_material_production_id = ANY(%s)
            GROUP BY sm.raw_material_production_id, svl.product_id
        """, (list(production_ids),))
        return {(mo_id, prod_id): val for mo_id, prod_id, val in self._cr.fetchall()}

    def _fetch_unit_costs(self):
        """Return dict {(product_id, company_id): standard_price}."""
        costs = {}
        products = self.mapped('product_id')
        companies = self.mapped('company_id') or self.env.company
        for company in companies:
            for product in products.with_company(company):
                costs[(product.id, company.id)] = product.standard_price or 0.0
        return costs

    @api.depends('product_tmpl_id')
    def _compute_is_variant(self):
        for rec in self:
            rec.is_variant = rec.product_tmpl_id.product_variant_count > 1

    def _search_is_variant(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return []
        templates = self.env['product.template'].search([('product_variant_count', '>', 1)])
        op = 'in' if (operator == '=') == value else 'not in'
        return [('product_tmpl_id', op, templates.ids)]

    @api.model
    def _select_query(self):
        return """
            WITH raw_components AS (
                SELECT
                    sm.raw_material_production_id AS production_id,
                    sm.product_id                 AS product_id,
                    MIN(sm.product_uom)           AS product_uom_id,
                    SUM(sm.product_uom_qty)       AS required_qty,
                    SUM(CASE WHEN sm.state = 'done' THEN sm.quantity_done ELSE 0 END) AS consumed_qty
                FROM stock_move sm
                JOIN mrp_production mp ON mp.id = sm.raw_material_production_id
                WHERE mp.state IN ('confirmed', 'progress', 'to_close')
                  AND sm.state != 'cancel'
                GROUP BY sm.raw_material_production_id, sm.product_id
            ),
            allocated AS (
                SELECT
                    sm.raw_material_production_id AS production_id,
                    sm.product_id                 AS product_id,
                    SUM(sml.reserved_uom_qty)     AS allocated_qty
                FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                JOIN mrp_production mp ON mp.id = sm.raw_material_production_id
                WHERE mp.state IN ('confirmed', 'progress', 'to_close')
                  AND sm.state NOT IN ('done', 'cancel')
                GROUP BY sm.raw_material_production_id, sm.product_id
            ),
            current_wc AS (
                SELECT DISTINCT ON (mw.production_id)
                    mw.production_id,
                    mw.workcenter_id
                FROM mrp_workorder mw
                WHERE mw.state IN ('ready', 'progress')
                ORDER BY mw.production_id,
                         CASE mw.state WHEN 'progress' THEN 1 WHEN 'ready' THEN 2 ELSE 3 END,
                         mw.id
            ),
            po_agg AS (
                SELECT
                    pol.product_id,
                    po.company_id,
                    SUM(pol.product_qty)    AS ordered_qty,
                    SUM(pol.qty_received)   AS received_qty
                FROM purchase_order_line pol
                JOIN purchase_order po ON po.id = pol.order_id
                WHERE po.state IN ('purchase', 'done')
                GROUP BY pol.product_id, po.company_id
            ),
            mr_agg AS (
                SELECT DISTINCT mrl.product_id, mpr.company_id
                FROM material_purchase_requisition_line mrl
                JOIN material_purchase_requisition mpr ON mpr.id = mrl.requisition_id
                WHERE mpr.state NOT IN ('receive', 'cancel', 'reject')
            )
            SELECT
                ROW_NUMBER() OVER (ORDER BY rc.production_id DESC, rc.product_id) AS id,
                rc.production_id,
                mp.name                                AS production_name,
                mp.state                               AS mo_state,
                mp.product_id                          AS mo_product_id,
                mp.product_qty                         AS mo_planned_qty,
                mp.date_planned_start                  AS mo_start_date,
                mp.date_planned_finished               AS mo_finish_date,
                mp.location_src_id                     AS main_location_id,
                mp.project_id                          AS project_id,
                mp.company_id                          AS company_id,
                cw.workcenter_id                       AS current_workcenter_id,
                rc.product_id                          AS product_id,
                pp.product_tmpl_id                     AS product_tmpl_id,
                pt.categ_id                            AS category_id,
                rc.product_uom_id                      AS product_uom_id,
                rc.required_qty                        AS required_qty,
                COALESCE(rc.consumed_qty, 0)           AS consumed_qty,
                GREATEST(rc.required_qty - COALESCE(rc.consumed_qty, 0), 0) AS remaining_qty,
                COALESCE(al.allocated_qty, 0)          AS allocated_qty,
                COALESCE((
                    SELECT SUM(sq.quantity - sq.reserved_quantity)
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id = sq.location_id
                    WHERE sq.product_id = rc.product_id
                      AND sq.location_id = mp.location_src_id
                      AND sl.usage = 'internal'
                ), 0)                                  AS available_main_qty,
                COALESCE((
                    SELECT SUM(sq.quantity - sq.reserved_quantity)
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id = sq.location_id
                    WHERE sq.product_id = rc.product_id
                      AND sq.location_id != mp.location_src_id
                      AND sl.usage = 'internal'
                      AND sl.company_id IS NOT DISTINCT FROM mp.company_id
                ), 0)                                  AS available_other_qty,
                GREATEST(
                    rc.required_qty
                    - COALESCE(rc.consumed_qty, 0)
                    - COALESCE(al.allocated_qty, 0),
                    0
                )                                      AS gap_qty,
                CASE
                    WHEN COALESCE(rc.consumed_qty, 0) + COALESCE(al.allocated_qty, 0) >= rc.required_qty
                        THEN 'fully_allocated'
                    WHEN COALESCE(rc.consumed_qty, 0)
                       + COALESCE(al.allocated_qty, 0)
                       + COALESCE((
                            SELECT SUM(sq.quantity - sq.reserved_quantity)
                            FROM stock_quant sq
                            JOIN stock_location sl ON sl.id = sq.location_id
                            WHERE sq.product_id = rc.product_id
                              AND sl.usage = 'internal'
                              AND sl.company_id IS NOT DISTINCT FROM mp.company_id
                       ), 0) >= rc.required_qty
                        THEN 'stock_available'
                    ELSE 'insufficient'
                END                                    AS availability_status,
                (mr.product_id IS NOT NULL)            AS has_material_request,
                COALESCE(po.ordered_qty, 0)            AS po_ordered_qty,
                COALESCE(po.received_qty, 0)           AS po_received_qty,
                GREATEST(COALESCE(po.ordered_qty, 0) - COALESCE(po.received_qty, 0), 0) AS pending_receipt_qty,
                CASE
                    WHEN po.ordered_qty IS NOT NULL AND po.ordered_qty > 0
                         AND po.received_qty >= po.ordered_qty
                        THEN 'fully_received'
                    WHEN po.ordered_qty IS NOT NULL AND po.received_qty > 0
                        THEN 'partial_received'
                    WHEN po.ordered_qty IS NOT NULL AND po.ordered_qty > 0
                        THEN 'po_created'
                    WHEN mr.product_id IS NOT NULL
                        THEN 'requested'
                    ELSE 'none'
                END                                    AS procurement_status
            FROM raw_components rc
            JOIN mrp_production mp ON mp.id = rc.production_id
            JOIN product_product pp ON pp.id = rc.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN allocated al
                   ON al.production_id = rc.production_id
                  AND al.product_id    = rc.product_id
            LEFT JOIN current_wc cw ON cw.production_id = rc.production_id
            LEFT JOIN po_agg po
                   ON po.product_id = rc.product_id
                  AND po.company_id IS NOT DISTINCT FROM mp.company_id
            LEFT JOIN mr_agg mr
                   ON mr.product_id = rc.product_id
                  AND mr.company_id IS NOT DISTINCT FROM mp.company_id
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            "CREATE OR REPLACE VIEW %s AS (%s)" % (self._table, self._select_query())
        )

    # Phase 4: action buttons.
    def action_view_stock_elsewhere(self):
        """Open quants for this component at other internal locations."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Elsewhere — %s', self.product_id.display_name),
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [
                ('product_id', '=', self.product_id.id),
                ('location_id.usage', '=', 'internal'),
                ('location_id', '!=', self.main_location_id.id),
                ('company_id', '=', self.company_id.id),
                ('quantity', '>', 0),
            ],
            'context': {'search_default_internal_loc': 1, 'create': False},
        }

    def action_view_open_pos(self):
        """Open active purchase orders containing this component."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Open POs — %s', self.product_id.display_name),
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [
                ('order_line.product_id', '=', self.product_id.id),
                ('state', 'in', ('purchase', 'done')),
                ('company_id', '=', self.company_id.id),
            ],
        }

    def action_view_material_requests(self):
        """Open active material requisitions containing this component."""
        self.ensure_one()
        requisition_lines = self.env['material.purchase.requisition.line'].search([
            ('product_id', '=', self.product_id.id),
            ('requisition_id.state', 'not in', ('receive', 'cancel', 'reject')),
            ('requisition_id.company_id', '=', self.company_id.id),
        ])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Requests — %s', self.product_id.display_name),
            'res_model': 'material.purchase.requisition',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', requisition_lines.mapped('requisition_id').ids)],
        }

    def action_create_requisition(self):
        """Open a new material requisition pre-populated with this component at gap qty."""
        self.ensure_one()
        line_defaults = {
            'product_id': self.product_id.id,
            'description': self.product_id.display_name,
            'qty': self.gap_qty or self.remaining_qty or 1.0,
            'uom': self.product_uom_id.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Material Requisition'),
            'res_model': 'material.purchase.requisition',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_requisition_line_ids': [(0, 0, line_defaults)],
                'default_company_id': self.company_id.id,
            },
        }
