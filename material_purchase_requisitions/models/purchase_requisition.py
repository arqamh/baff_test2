# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, UserError


class MaterialPurchaseRequisition(models.Model):
    _name = 'material.purchase.requisition'
    _description = 'Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'id desc'

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel', 'reject'):
                raise UserError(_('You can not delete Purchase Requisition which is not in draft or '
                                  'cancelled or rejected state.'))
        return super(MaterialPurchaseRequisition, self).unlink()

    name = fields.Char(string='Number', index=True, readonly=1,)
    state = fields.Selection([
        ('draft', 'New'),
        ('dept_confirm', 'Waiting Department Approval'),
        ('ir_approve', 'Waiting IR Approval'),
        ('approve', 'Approved'),
        ('stock', 'Pickings Created'),
        ('procurement', 'Procurement Created'),
        ('stock_procurement', 'Picking and Procurement Created'),
        ('receive', 'Received'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')], default='draft', tracking=True)

    request_date = fields.Date(string='Requisition Date', default=lambda self: fields.Date.context_today(self),
                               required=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True, copy=True)
    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)],
                                                                                      limit=1), required=True, copy=True)
    approve_manager_id = fields.Many2one('hr.employee', string='Department Manager', readonly=True, copy=False)
    reject_manager_id = fields.Many2one('hr.employee', string='Department Manager Reject', readonly=True)
    approve_employee_id = fields.Many2one('hr.employee', string='Approved by', readonly=True, copy=False)
    reject_employee_id = fields.Many2one('hr.employee', string='Rejected by', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 required=True, copy=True)
    location_id = fields.Many2one('stock.location', string='Source Location', copy=True)
    requisition_line_ids = fields.One2many('material.purchase.requisition.line', 'requisition_id',
                                           string='Purchase Requisitions Line', copy=False,
                                           domain=[('sent_procurement', '=', False)])
    purchase_line_ids = fields.One2many('material.purchase.requisition.line', 'requisition_id',
                                        string='Purchase Lines', copy=False,
                                        domain=[('sent_procurement', '=', True)])
    date_end = fields.Date(string='Requisition Deadline', readonly=True, help='Last date for the product to be needed',
                           copy=True)
    date_done = fields.Date(string='Date Done', readonly=True, help='Date of Completion of Purchase Requisition')
    managerapp_date = fields.Date(string='Department Approval Date', readonly=True, copy=False)
    manareject_date = fields.Date(string='Department Manager Reject Date', readonly=True)
    userreject_date = fields.Date(string='Rejected Date', readonly=True, copy=False)
    userrapp_date = fields.Date(string='Approved Date', readonly=True, copy=False)
    receive_date = fields.Date(string='Received Date', readonly=True, copy=False)
    reason = fields.Text(string='Reason for Requisitions', required=False, copy=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', copy=True)
    dest_location_id = fields.Many2one('stock.location', string='Destination Location', required=False, copy=True)
    delivery_picking_id = fields.Many2one('stock.picking', string='Internal Picking', readonly=True, copy=False)
    requisiton_responsible_id = fields.Many2one('hr.employee', string='Requisition Responsible', copy=True)

    # Header-level location fields for easy editing
    header_location_id = fields.Many2one('stock.location', string='Source Location', copy=True)
    header_dest_location_id = fields.Many2one('stock.location', string='Destination Location', copy=True)
    employee_confirm_id = fields.Many2one('hr.employee', string='Confirmed by', readonly=True, copy=False)
    confirm_date = fields.Date(string='Confirmed Date', readonly=True, copy=False)
    purchase_order_ids = fields.One2many('purchase.order', 'custom_requisition_id', string='Purchase Ordes')
    custom_picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type',
                                             default=lambda self: self.env.company.default_picking_type)
    po_created = fields.Boolean(string="PO Created", copy=False, default=False, compute='_compute_po_created')
    is_fully_completed = fields.Boolean(string="PO Created", copy=False, default=False, compute='_compute_is_fully_completed')
    mrp_id = fields.Many2one('mrp.production', string="Manufacturing Order", copy=False)
    need_pickings = fields.Boolean(string="Need Pickings", copy=False, default=False, compute='_compute_is_picking_pr_needed')
    need_procurement = fields.Boolean(string="Need Procurement", copy=False, default=False, compute='_compute_is_picking_pr_needed')
    extra_qty = fields.Boolean(string="Extra Quantity", copy=False, default=False, compute='_compute_extra_qty')
    is_email_sent_once = fields.Boolean(String="Email Sent", copy=False, default=False)

    is_asset_purchase = fields.Boolean(string='Asset Purchase', copy=True, default=False, tracking=True,
                                       help="Mark this requisition as an Asset Purchase.")
    asset_location_id = fields.Many2one('stock.location', string='Asset Location', copy=True, tracking=True,
                                        domain="[('usage', '=', 'internal')]",
                                        help="Location (Branch, Department, Office, Warehouse) where the "
                                             "purchased asset will be allocated/installed.")

    @api.onchange('custom_picking_type_id')
    def _onchange_custom_picking_type_id(self):
        """Get the default source and destination locations from the selected picking type"""
        if self.custom_picking_type_id:
            # Set header locations from picking type
            self.header_location_id = self.custom_picking_type_id.default_location_src_id.id
            self.header_dest_location_id = self.custom_picking_type_id.default_location_dest_id.id

            # Update all line locations
            for line in self.requisition_line_ids:
                location_id = self.custom_picking_type_id.default_location_src_id.id
                location_dest_id = self.custom_picking_type_id.default_location_dest_id.id
                line.update({
                    'location_id': location_id,
                    'dest_location_id': location_dest_id
                })

    @api.onchange('header_location_id')
    def _onchange_header_location_id(self):
        """Update all line source locations when header source location changes"""
        if self.header_location_id:
            for line in self.requisition_line_ids:
                line.location_id = self.header_location_id.id

    @api.onchange('header_dest_location_id')
    def _onchange_header_dest_location_id(self):
        """Update all line destination locations when header destination location changes"""
        if self.header_dest_location_id:
            for line in self.requisition_line_ids:
                line.dest_location_id = self.header_dest_location_id.id

    @api.depends('requisition_line_ids.remaining_qty', 'requisition_line_ids.qty')
    def _compute_extra_qty(self):
        """OPTIMIZED: Replaced search([]).filtered() inside loop with batch query"""
        # Initialize defaults
        for record in self:
            record.extra_qty = False

        # Filter to draft records only
        draft_records = self.filtered(lambda r: r.state == 'draft')
        if not draft_records:
            return

        # Collect all lines that need processing
        all_lines = draft_records.mapped('requisition_line_ids')
        if not all_lines:
            return

        # Set scheduled_date for lines that don't have it
        for line in all_lines:
            if not line.scheduled_date:
                line.scheduled_date = line.requisition_id.request_date

        # Collect unique lookup keys for batch query
        product_ids = set()
        sources = set()
        for line in all_lines:
            if line.product_id:
                product_ids.add(line.product_id.id)
            if line.requisition_id and line.requisition_id.job_costing_id:
                sources.add(line.requisition_id.job_costing_id.name)

        if not product_ids:
            return

        # BATCH QUERY: Fetch all relevant procurement plans in single query
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

        # Process lines using pre-fetched data
        for record in draft_records:
            extra_qty = False
            for line in record.requisition_line_ids:
                if not line.product_id or not line.scheduled_date:
                    continue

                # Build lookup key
                scheduled_date = line.scheduled_date.date() if hasattr(line.scheduled_date, 'date') else line.scheduled_date
                source = line.requisition_id.job_costing_id.name if line.requisition_id and line.requisition_id.job_costing_id else False
                key = (scheduled_date, source, line.product_id.id)

                procurement_line = plans_by_key.get(key)
                if procurement_line:
                    if procurement_line.actual_to_order_qty < line.remaining_qty:
                        line.extra_qty = line.remaining_qty - procurement_line.actual_to_order_qty
                        extra_qty = True

            record.extra_qty = extra_qty

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('purchase.requisition.seq')
        vals.update({
            'name': name
        })
        res = super(MaterialPurchaseRequisition, self).create(vals)
        return res

    def requisition_confirm(self):
        manager_mail_template = self.env.ref('material_purchase_requisitions.'
                                             'email_confirm_material_purchase_requistion')
        today = fields.Date.today()
        for rec in self:
            for req_line in rec.requisition_line_ids:
                if not req_line.scheduled_date:
                    raise UserError(_('Please select Scheduled Date for '+req_line.product_id.name))

            if rec.is_asset_purchase and not rec.asset_location_id:
                raise UserError(_('Please specify the Asset Location for Asset Purchase requisitions.'))

            rec.employee_confirm_id = rec.employee_id.id
            rec.confirm_date = today
            rec.state = 'dept_confirm'
            if manager_mail_template:
                manager_mail_template.send_mail(rec.id)

    def requisition_reject(self):
        """OPTIMIZED: Move employee search outside loop"""
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        today = fields.Date.today()
        for rec in self:
            rec.state = 'reject'
            rec.reject_employee_id = current_employee
            rec.userreject_date = today

    def manager_approve(self):
        """OPTIMIZED: Move employee search and template lookups outside loop"""
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        today = fields.Date.today()
        employee_mail_template = self.env.ref('material_purchase_requisitions.'
                                              'email_purchase_requisition_iruser_custom')
        email_iruser_template = self.env.ref('material_purchase_requisitions.email_purchase_requisition')
        for rec in self:
            rec.managerapp_date = today
            rec.approve_manager_id = current_employee
            rec.message_post(body=_(
                "Department Approval granted by %(approver)s on %(date)s.",
                approver=current_employee.name or self.env.user.name,
                date=fields.Date.to_string(today),
            ))
            employee_mail_template.send_mail(rec.id)
            email_iruser_template.send_mail(rec.id)
            rec.state = 'ir_approve'

    def user_approve(self):
        """OPTIMIZED: Move employee search outside loop"""
        current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        today = fields.Date.today()
        for rec in self:
            rec.userrapp_date = today
            rec.approve_employee_id = current_employee
            rec.message_post(body=_(
                "IR Approval granted by %(approver)s on %(date)s.",
                approver=current_employee.name or self.env.user.name,
                date=fields.Date.to_string(today),
            ))
            rec.state = 'approve'

    def reset_draft(self):
        for rec in self:
            for line in rec.requisition_line_ids:
                line.required_quantity = line.job_cost_line_id.to_order_quantity
                line.job_cost_line_id.update({'to_order_quantity': 0})
            rec.state = 'draft'

    @api.model
    def _prepare_pick_vals(self, line=False, stock_id=False):
        pick_vals = {
            'product_id': line.product_id.id,
            'product_uom_qty': line.qty,
            'product_uom': line.uom.id,
            'location_id': line.location_id.id,
            'location_dest_id': line.dest_location_id.id,
            'name': line.product_id.name,
            'picking_type_id': self.custom_picking_type_id.id,
            'picking_id': stock_id.id,
            'custom_requisition_line_id': line.id,
            'company_id': line.requisition_id.company_id.id}
        return pick_vals

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        seller = line.product_id._select_seller(partner_id=self._context.get('partner_id'), quantity=line.qty,
                                                date=purchase_order.date_order and purchase_order.date_order.date(),
                                                uom_id=line.uom)
        po_line_vals = {'product_id': line.product_id.id, 'name': line.product_id.name, 'product_qty': line.qty,
                        'product_uom': line.uom.id, 'date_planned': fields.Date.today(),
                        'price_unit': seller.price or line.product_id.standard_price or 0.0,
                        'order_id': purchase_order.id,
                        'analytic_distribution':  {self.sudo().analytic_account_id.id: 100} if self.analytic_account_id
                        else False, 'custom_requisition_line_id': line.id}
        return po_line_vals

    def request_stock(self, line=False):
        stock_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        for rec in self:
            if not rec.requisition_line_ids:
                raise UserError(_('Please create some requisition lines.'))

            if any(line.requisition_type == 'internal' for line in rec.requisition_line_ids):
                if not rec.custom_picking_type_id:
                    raise UserError(_('Select Picking Type under the picking details.'))
            # Dict mapping (src, dest) → stock_id for O(1) lookup and correct picking assignment
            picking_by_locations = {}
            lines = line if line else rec.requisition_line_ids
            for line in lines:
                if line.requisition_type == 'internal':
                    if not line.location_id:
                        raise UserError(_('Select Source location under the picking details.'))
                    if not line.dest_location_id:
                        raise UserError(_('Select Destination location under the picking details.'))
                    if not line.pr_state:
                        loc_key = (line.location_id.id, line.dest_location_id.id)
                        if loc_key not in picking_by_locations:
                            picking_vals = {
                                'partner_id': rec.employee_id.sudo().address_home_id.id,
                                'location_id': line.location_id.id,
                                'location_dest_id': line.dest_location_id and line.dest_location_id.id or rec.employee_id.dest_location_id.id or rec.employee_id.department_id.dest_location_id.id,
                                'picking_type_id': rec.custom_picking_type_id.id,
                                'note': rec.reason,
                                'custom_requisition_id': rec.id,
                                'origin': rec.name,
                                'company_id': rec.company_id.id
                            }
                            stock_id = stock_obj.sudo().create(picking_vals)
                            picking_by_locations[loc_key] = stock_id
                        else:
                            stock_id = picking_by_locations[loc_key]
                        pick_vals = rec._prepare_pick_vals(line, stock_id)
                        move_id = move_obj.sudo().create(pick_vals)
                        line.write({
                            'move_id': move_id.id
                        })
            if rec.state == 'procurement':
                rec.state = 'stock_procurement'
            else:
                rec.state = 'stock'

    def action_received(self):
        for rec in self:
            rec.receive_date = fields.Date.today()
            rec.state = 'receive'

    def action_cancel(self):
        for rec in self:
            for line in rec.requisition_line_ids:
                line.job_cost_line_id.update({'to_order_quantity': line.required_quantity})
            rec.state = 'cancel'

    @api.onchange('employee_id')
    def set_department(self):
        for rec in self:
            rec.department_id = rec.employee_id.sudo().department_id.id
            rec.dest_location_id = rec.employee_id.sudo().dest_location_id.id or rec.employee_id.sudo().department_id.\
                dest_location_id.id

    def show_picking(self):
        # res = self.env.ref('stock.action_picking_tree_all')
        # res = res.sudo().read()[0]
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        res['domain'] = str([('custom_requisition_id', '=', self.id)])
        return res

    def action_show_po(self):
        self.ensure_one()
        purchase_action = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_rfq')
        purchase_action['domain'] = str([('custom_requisition_id', '=', self.id)])
        return purchase_action

    def create_purchase_orders(self):
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        for rec in self:
            po_dict = {}
            # Collect PO line vals per PO for batch creation
            po_line_vals_list = {}  # partner → list of vals
            for line in rec.purchase_line_ids:
                if line.requisition_type == 'purchase':
                    if not line.partner_id:
                        raise UserError(_('Please enter at least one vendor on Purchase Lines for'
                                          'Requisition Action Purchase'))

                    for partner in line.partner_id:
                        if partner not in po_dict:
                            po_vals = {'partner_id': partner.id, 'currency_id': rec.env.user.company_id.currency_id.id,
                                       'date_order': fields.Date.today(), 'company_id': rec.company_id.id,
                                       'custom_requisition_id': rec.id, 'origin': rec.name}
                            purchase_order = purchase_obj.create(po_vals)
                            po_dict[partner] = purchase_order
                            po_line_vals_list[partner] = []
                        purchase_order = po_dict[partner]
                        po_line_vals = rec.with_context(partner_id=partner)._prepare_po_line(line, purchase_order)
                        po_line_vals_list[partner].append(po_line_vals)

            # Batch create all PO lines per partner
            for partner, vals_list in po_line_vals_list.items():
                if vals_list:
                    purchase_line_obj.sudo().create(vals_list)

    def _compute_is_fully_completed(self):
        for record in self:
            if record.state in ('stock', 'procurement', 'stock_procurement'):
                all_lines = record.requisition_line_ids | record.purchase_line_ids
                record.is_fully_completed = bool(all_lines) and all(l.pr_state == 'done' for l in all_lines)
            else:
                record.is_fully_completed = False

    def _compute_po_created(self):
        """OPTIMIZED: Replaced search([]).filtered() with batched domain-based query"""
        # Initialize defaults
        for record in self:
            record.po_created = True

        if not self.ids:
            return

        # Get records that have purchase lines (need to check for POs)
        records_with_purchase_lines = self.filtered(lambda r: r.purchase_line_ids)
        if not records_with_purchase_lines:
            return

        # BATCH QUERY: Fetch all non-cancelled POs for these requisitions
        requisition_ids = records_with_purchase_lines.ids
        purchase_orders = self.env['purchase.order'].search([
            ('custom_requisition_id', 'in', requisition_ids),
            ('state', '!=', 'cancel')
        ])

        # Build set of requisition IDs that have POs
        requisitions_with_po = set(purchase_orders.mapped('custom_requisition_id').ids)

        # Update records based on whether they have POs
        for record in records_with_purchase_lines:
            record.po_created = record.id in requisitions_with_po

    def _compute_is_picking_pr_needed(self):
        for record in self:
            record.need_pickings = any(l.requisition_type == 'internal' for l in record.requisition_line_ids)
            record.need_procurement = any(l.requisition_type == 'purchase' and not l.sent_procurement for l in record.requisition_line_ids)

    def send_to_procurement(self):
        for record in self:
            if record.requisition_line_ids:
                for line in record.requisition_line_ids:
                    if not line.scheduled_date:
                        raise UserError(_('Please select Scheduled Date for ' + line.product_id.name))
                    else:
                        line.send_to_pr_and_notify_once()
                        record.is_email_sent_once = True
                if record.state == 'stock':
                    record.state = 'stock_procurement'
                elif record.state == 'approve':
                    record.state = 'procurement'

    def action_change_requisition_type(self):
        """Open wizard to change requisition type for lines"""
        self.ensure_one()

        if self.state != 'approve':
            raise UserError(_('Requisition type can only be changed in Approved state.'))

        if not self.requisition_line_ids:
            raise UserError(_('No requisition lines found.'))

        return {
            'name': _('Change Requisition Type'),
            'type': 'ir.actions.act_window',
            'res_model': 'change.requisition.type.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_requisition_id': self.id,
                'active_model': 'material.purchase.requisition',
                'active_id': self.id,
            }
        }