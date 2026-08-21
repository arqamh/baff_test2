from datetime import date, timedelta
from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

AVAILABLE_PRIORITIES = [
    ('none', 'None'),
    ('urgent', 'Urgent'),
    ('super_urgent', 'Super Urgent')
]


class JobCosting(models.Model):
    _name = 'job.costing'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'analytic.mixin']
    _description = "Job Costing"
    _rec_name = 'number'
    _order = 'id desc'

    def _get_default_profit_margin(self):
        if self.env.company.profit_margin:
            return self.env.company.profit_margin
        else:
            return 0.0

    number = fields.Char(readonly=True, default='New', copy=False)
    name = fields.Char(required=True, copy=True, default='New', string='Name')
    notes_job = fields.Text(required=False, copy=True, string='Remarks / Final Price', tracking=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, string='Created By', readonly=True)
    description = fields.Char(string='Description')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id, readonly=True,
                                  tracking=True)
    customer_currency_id = fields.Many2one('res.currency', string='Customer Currency',
                                           default=lambda self: self.env.user.company_id.currency_id, tracking=True)
    currency_rate = fields.Float(string="Currency Rate")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, string='Company', readonly=True)
    project_id = fields.Many2one('project.project', string='Project')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    contract_date = fields.Date(string='Contract Date')
    start_date = fields.Date(string='Date Ordered', default=fields.Date.today(), tracking=True)
    complete_date = fields.Date(string='Date Required', tracking=True)
    material_total = fields.Float(string='Total Material Cost', compute='_compute_material_total', store=True,
                                  tracking=True)
    labor_total = fields.Float(string='Total Labour Cost', compute='_compute_labor_total', store=True, tracking=True)
    overhead_total = fields.Float(string='Total Overhead Cost', compute='_compute_overhead_total', store=True,
                                  tracking=True)
    gross_jobcost_total = fields.Float(string='Total Cost', compute='_compute_gross_jobcost_total', store=True,
                                       tracking=True)
    factory_and_admin_overhead = fields.Float(string='Factory & Admin Overhead',
                                              compute='_compute_factory_and_admin_overhead', store=True, tracking=True)
    gross_profit_markup = fields.Float(string='Gross Profit % Markup', default=_get_default_profit_margin, store=True,
                                       tracking=True)
    profit_margin = fields.Float(string='Profit Margin', compute='_compute_profit_margin',
                                 inverse='_inverse_profit_margin_markup', store=True, tracking=True)

    profit_margin_percentage = fields.Float(string='Sale Commission, After Sales Service and Design Royalties',
                                            store=True, tracking=True)
    sale_commission_price = fields.Float(string='Sale Price without Sale Commission',
                                         compute='_compute_sale_commission_price', store=True, tracking=True)
    sale_commission_margin = fields.Float(string='Sale Commission Margin', compute='_compute_sale_commission_margin',
                                          store=True, tracking=True)
    same_customer_company_currency = fields.Boolean(string='Same Customer Company Currency',
                                                    compute='_compute_same_customer_company_currency')
    total_price_customer_currency = fields.Float(string='Total Price in Customer Currency',
                                                 compute='_compute_total_price_customer_currency', store=True,
                                                 tracking=True)

    jobcost_total = fields.Float(string='Total Price', compute='_compute_jobcost_total', store=True, tracking=True)
    job_cost_line_ids = fields.One2many('job.cost.line', 'job_costing_id', string='Direct Materials', copy=True,
                                        domain=[('job_type', '=', 'material')])
    job_labour_line_ids = fields.One2many('job.cost.line', 'job_costing_id', string='Direct Labours', copy=True,
                                          domain=[('job_type', '=', 'labour')])
    job_overhead_line_ids = fields.One2many('job.cost.line', 'job_costing_id', string='Direct Overheads', copy=True,
                                            domain=[('job_type', '=', 'overhead')])
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    state = fields.Selection(
        selection=[
            ('revised', 'Revised'),
            ('draft', 'Draft'),
            ('waiting_first_approval', 'Awaiting Review'),
            ('confirm', 'Reviewed'),
            ('waiting_second_approval', 'Awaiting Approval'),
            ('approved', 'approved'),
            ('ready_for_production', 'Ready for Production Approval'),
            ('waiting_production_approval', 'Waiting Production Approval'),
            ('done', 'Done'),
            ('cancel', 'Canceled'), ],
        string='State', tracking=True, default='draft')
    task_id = fields.Many2one('project.task', string='Job Order')
    so_number = fields.Char(string='Sale Reference')
    purchase_order_line_count = fields.Integer(compute='_purchase_order_line_count')
    job_costsheet_line_count = fields.Integer(compute='_job_costsheet_line_count')
    purchase_order_line_ids = fields.One2many("purchase.order.line", 'job_cost_id')
    timesheet_line_count = fields.Integer(compute='_timesheet_line_count')
    timesheet_line_ids = fields.One2many('account.analytic.line', 'job_cost_id')
    account_invoice_line_count = fields.Integer(compute='_account_invoice_line_count')
    account_invoice_line_ids = fields.One2many('account.move.line', 'job_cost_id')
    lead_id = fields.Many2one('crm.lead', string="Inquiry Number", tracking=True)
    priority = fields.Selection(selection=[('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High')],
                                string="Priority Level", default='low', tracking=True)
    sales_person_id = fields.Many2one('res.users', string="Salesperson", tracking=True)
    job_number = fields.Char(string="Job Number")
    job_grade = fields.Char(string="Job Grade")
    po_number = fields.Char(string="PO Number")
    quotation_id = fields.Many2one('sale.order', string="Quotation", tracking=True)
    sale_id = fields.Many2one('sale.order', string="Sales Order")
    project_start_date = fields.Date(string="Project Start Date", tracking=True)
    # prepared_by = fields.Many2one('res.users', string="Prepared By")
    checked_by = fields.Many2one('res.users', string="Checked By")
    analytic_plan_id = fields.Many2one('account.analytic.plan', string="Analytic Plan", tracking=True)
    # NON-STORED computes: summed in-memory from the lines on read. Previously
    # plain stored fields written from job.cost.line._compute_budget_cost /
    # _compute_actual_cost during a *read*, which issued UPDATE job_costing on
    # every read and caused "could not serialize access due to concurrent update"
    # under concurrency. Only read for alerts/display (never search/group_by), so
    # non-stored is safe.
    total_budget_cost = fields.Float(string="Total Budget Cost", compute='_compute_total_budget_cost')
    total_actual_cost = fields.Float(string="Total Actual Cost", compute='_compute_total_actual_cost')
    finished_good_location_id = fields.Many2one(related='sale_id.finished_good_location_id', string='Finished Good Location',
                                                 store=True, readonly=True)

    approval_requested_date = fields.Datetime(string="Approval Requested Date", tracking=True)
    approval_requested_by = fields.Many2one('res.users', string="Approval Requested By", tracking=True)
    approval_requested_users = fields.Many2many('res.users', 'account_move_users_requested_rel', 'move_id', 'user_id',
                                                string="Approval Requested Users", tracking=True)

    hide_approve_reject_button = fields.Boolean(compute='_compute_hide_approve_reject_button')

    first_approval_requested_date = fields.Datetime(string="Approval Requested Date ", tracking=True)
    first_approval_requested_by = fields.Many2one('res.users', string="Approval Requested By ", tracking=True)
    first_approval_requested_users = fields.Many2many('res.users', 'account_move_first_users_requested_rel', 'move_id',
                                                      'user_id', string="Approval Requested Users ", tracking=True)

    production_approval_requested_date = fields.Datetime(string="Approval Requested Date  ", tracking=True)
    production_approval_requested_by = fields.Many2one('res.users', string="Approval Requested By  ", tracking=True)
    production_approval_requested_users = fields.Many2many('res.users', 'account_move_production_users_requested_rel',
                                                           'move_id', 'user_id', string="Approval Requested Users  ",
                                                           tracking=True)

    is_all_users_approve = fields.Boolean(default=False)
    approved_by = fields.Many2many('res.users', 'account_move_users_approved_rel', 'move_id', 'user_id',
                                   string="Approved By", tracking=True)
    approved_date = fields.Datetime(string="Last Approved Date", tracking=True)
    approved_note = fields.Text('Approved Note', tracking=True)

    first_approved_by = fields.Many2many('res.users', 'account_first_move_users_approved_rel', 'move_id', 'user_id',
                                         string="Approved By ", tracking=True)
    first_approved_date = fields.Datetime(string="Last Approved Date ", tracking=True)
    first_approved_note = fields.Text('Approved Note ', tracking=True)

    production_approved_by = fields.Many2many('res.users', 'account_production_move_users_approved_rel', 'move_id',
                                              'user_id', string="Approved By  ", tracking=True)
    production_approved_date = fields.Datetime(string="Last Approved Date  ", tracking=True)
    production_approved_note = fields.Text('Approved Note  ', tracking=True)

    rejected_by = fields.Many2many('res.users', 'account_move_users_rejected_rel', 'move_id', 'user_id',
                                   string="Rejected By", tracking=True)
    rejected_date = fields.Datetime(string="Last Rejected Date", tracking=True)
    rejected_note = fields.Char('Rejected Note', tracking=True)

    purchase_requisition_ids = fields.Many2many('material.purchase.requisition', 'costing_sheet_requisitions_rels',
                                                'requisition_id', 'costing_id',
                                                compute="_compute_purchase_requisition_ids")
    finished_good_ids = fields.One2many(
        'job.costing.finished.good', 'job_costing_id',
        string='Finished Goods', copy=True,
        help='One line per finished good produced under this Job Costing '
             'Sheet. Replaces the legacy single-product/quantity header.')
    invoice_ids = fields.Many2many(
        'account.move', string='Invoices',
        compute='_compute_invoice_ids',
        help='Customer invoices generated from the linked Sales Order.')
    invoice_count = fields.Integer(
        string='# of Invoices', compute='_compute_invoice_ids')
    job_costing_approval_line_ids = fields.One2many('job.costing.approval.lines', 'job_costing_id', copy=True)
    boat_type_id = fields.Many2one('boat.type', string="Boat Type")
    cost_analysis_line = fields.One2many('job.cost.line', 'job_costing_id', string='Variant Analysis', copy=False)
    project_name = fields.Char(string="Project Name")
    line_type = fields.Selection([('material', 'Material'), ('component', 'Component')], default=False,
                                 compute='_compute_line_type')
    labour_line_type = fields.Boolean(string="Labor Line Type", default=False, compute='_compute_line_type')
    parent_bom_domain_ids = fields.Many2many('mrp.bom', string="Parent BOM", compute='_compute_parent_bom_domain_ids')
    bom_domain_ids = fields.Many2many('mrp.bom', string="BOM", compute='_compute_parent_bom_domain_ids')

    is_revised = fields.Boolean(string='Is Revised')
    original_number = fields.Char(string='Original Number')
    revised_number = fields.Char(string='Revised Number')
    original_job_costing_id = fields.Many2one('job.costing', string='Original Job Costing Sheet')

    def action_add_lines(self):
        """ Update invoiceable lines in sales quotation using overhead lines and material lines """
        if self.job_cost_line_ids:
            lines = self.job_cost_line_ids.filtered(lambda x: x.is_include_report == True).sorted(key='component')
            if not lines:
                lines = self.job_cost_line_ids
            if lines:
                sequence = 1
                invoiceable_lines = [(5, 0, 0)]

                # Update overhead expenses to the sale order
                if self.job_overhead_line_ids:
                    overhead_lines = []
                    for line in self.job_overhead_line_ids:
                        unit_price = 0.0
                        if self.currency_id == self.customer_currency_id:
                            unit_price = line.cost_price
                        else:
                            if self.currency_rate:
                                unit_price = line.cost_price / self.currency_rate
                            overhead_lines.append((0, 0, {
                                'name': line.product_id.name,
                                'product_id': line.product_id.id,
                                'product_uom_qty': line.product_qty,
                                'product_uom': line.uom_id.id,
                                'price_unit': unit_price,
                                'price_subtotal': line.total_cost,
                            }))

                    for line in lines:
                        vals = {}
                        if line.is_include_report:
                            if line.material_type in ['parent', 'bom']:
                                unit_price = 0.0
                                if self.currency_id == self.customer_currency_id:
                                    unit_price = line.total_cost
                                else:
                                    if self.currency_rate:
                                        unit_price = line.total_cost / self.currency_rate
                                vals = {
                                    'sequence': sequence,
                                    'product_id': line.product_id.id,
                                    'product_uom_qty': line.product_qty,
                                    'product_uom': line.uom_id.id,
                                    'price_unit': unit_price,
                                    'name': line.component
                                }
                        elif line.material_type == 'component':
                            if line.is_include_report:
                                unit_price = 0.0
                                if self.currency_id == self.customer_currency_id:
                                    unit_price = line.cost_price
                                else:
                                    if self.currency_rate:
                                        unit_price = line.cost_price / self.currency_rate
                                vals = {
                                    'sequence': sequence,
                                    'product_id': line.product_id.id,
                                    'product_uom_qty': line.product_qty,
                                    'product_uom': line.uom_id.id,
                                    'price_unit': unit_price,
                                    'name': line.product_id.display_name
                                }
                        sequence += 1
                        if vals:
                            invoiceable_lines.append((0, 0, vals))
                    self.quotation_id.invoiceable_line = invoiceable_lines
                    self.quotation_id.invoiceable_line = overhead_lines


    def action_revise_job_costing(self):
        """
        Revised job costing sheets and provide the flexibility to reset job costing sheets and associated
        quotations to the draft state when necessary.
        """
        for record in self:
            if record.quotation_id.state == 'quotation_done':
                raise UserError(
                    _('You cannot revise the job costing sheet because the associated quotation is not in the draft state.'))
            else:
                if not self.env.company.job_cost_revise_suffix:
                    raise UserError(_("Please configure revise job costing sheet number suffix from the settings."))

                original_number = record.original_number or record.number
                # Count existing revisions for this quotation
                revision_count = self.env['job.costing'].search_count([('original_job_costing_id', '=', record.id)]) + 1
                revised_number = f"{original_number}/{self.env.company.job_cost_revise_suffix}{revision_count}"

                record.write({
                    'state': 'draft',
                    'is_revised': True,
                    'number': original_number
                })
                revised_copy = record.copy()
                revised_copy.write({
                    'state': 'revised',
                    'number': revised_number,
                    'original_job_costing_id': record.id
                })
                # revised_copy.job_costing_approval_line_ids.write({'state':  'revised'})
                record.job_costing_approval_line_ids.unlink()
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'job.costing',
                    'view_mode': 'form',
                    'res_id': revised_copy.id,
                    'target': 'current',
                }

    @api.depends('sale_id.invoice_ids', 'quotation_id.invoice_ids')
    def _compute_invoice_ids(self):
        """Aggregate the customer invoices created from the linked SO. Multiple
        invoices are supported via standard partial-qty invoicing."""
        for rec in self:
            invoices = rec.sale_id.invoice_ids | rec.quotation_id.invoice_ids
            invoices = invoices.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund'))
            rec.invoice_ids = invoices
            rec.invoice_count = len(invoices)

    def action_view_invoices(self):
        """Open the customer invoices generated from this sheet's Sales Order."""
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        invoices = self.invoice_ids
        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_id': invoices.id,
            })
        else:
            action['domain'] = [('id', 'in', invoices.ids)]
        return action

    def _compute_purchase_requisition_ids(self):
        """OPTIMIZED: Single batch search instead of search per record"""
        # Initialize all records
        for record in self:
            record.purchase_requisition_ids = [(5,)]
        if not self.ids:
            return
        # Single batch search for all records
        all_req_lines = self.env['material.purchase.requisition.line'].search(
            [('job_costing_id', 'in', self.ids)])
        # Group requisition IDs by job_costing_id
        req_ids_by_job = {}
        for line in all_req_lines:
            jc_id = line.job_costing_id.id
            if jc_id not in req_ids_by_job:
                req_ids_by_job[jc_id] = set()
            req_ids_by_job[jc_id].add(line.requisition_id.id)
        # Apply grouped data
        for record in self:
            req_ids = req_ids_by_job.get(record.id)
            if req_ids:
                record.purchase_requisition_ids = [(6, 0, list(req_ids))]

    @api.model
    def create(self, vals):
        """set job costing number"""
        result = super(JobCosting, self).create(vals)
        prefix = self.env.company.job_cost_prefix
        if prefix:
            number = self.env['ir.sequence'].next_by_code('job.costing')
            if number:
                result.write({
                    'number': prefix + number,
                })
        else:
            raise UserError(_("Please configure Job Costing Sheet Number Prefix from the settings."))
        return result

    def unlink(self):
        """restriction when deleting job costs"""
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete Job Cost Sheet which is not draft or cancelled.'))
        return super(JobCosting, self).unlink()

    @api.depends('job_cost_line_ids', 'job_cost_line_ids.product_qty', 'job_cost_line_ids.cost_price')
    def _compute_material_total(self):
        """compute material cost and each component cost - OPTIMIZED V2
        Replaced O(n*m) nested loops with O(n) prefix-based grouping"""
        for rec in self:
            material_total = 0.0
            parent_lines = rec.job_cost_line_ids.filtered(lambda x: x.material_type == 'parent')

            if not parent_lines:
                rec.material_total = 0.0
                continue

            # Pre-group lines by exact component for direct lookup
            materials_by_component = {}
            boms_by_component = {}
            all_material_components = []
            all_bom_components = []

            for line in rec.job_cost_line_ids:
                if line.material_type == 'component' and line.job_type == 'material' and line.component:
                    if line.component not in materials_by_component:
                        materials_by_component[line.component] = []
                        all_material_components.append(line.component)
                    materials_by_component[line.component].append(line)
                elif line.material_type == 'bom' and line.job_type == 'material' and line.component:
                    if line.component not in boms_by_component:
                        boms_by_component[line.component] = []
                        all_bom_components.append(line.component)
                    boms_by_component[line.component].append(line)

            # Pre-group labour by component
            labour_by_component = {}
            all_labour_components = []
            for line in rec.job_labour_line_ids:
                if line.job_type == 'labour' and line.component:
                    if line.component not in labour_by_component:
                        labour_by_component[line.component] = []
                        all_labour_components.append(line.component)
                    labour_by_component[line.component].append(line)

            # Build prefix index: parent_component -> [child_components]
            # This avoids O(n*m) substring checks by pre-computing child relationships
            def get_children_for_prefix(prefix, all_components):
                """Get all components that have this prefix (O(n) but only once per prefix)"""
                if not prefix:
                    return []
                return [c for c in all_components if prefix in c]

            # Pre-compute children for all parent components (done once, not per lookup)
            parent_components = [p.component for p in parent_lines if p.component]
            bom_component_values = [b.component for b in rec.job_cost_line_ids
                                    if b.material_type == 'bom' and b.component]

            material_children_cache = {}
            bom_children_cache = {}
            labour_children_cache = {}

            for pc in parent_components + bom_component_values:
                if pc and pc not in material_children_cache:
                    material_children_cache[pc] = get_children_for_prefix(pc, all_material_components)
                    bom_children_cache[pc] = get_children_for_prefix(pc, all_bom_components)
                    labour_children_cache[pc] = get_children_for_prefix(pc, all_labour_components)

            # Get overhead once (only for first parent)
            overhead_total = sum(
                rec.job_overhead_line_ids.filtered(lambda x: x.job_type == 'overhead').mapped('total_cost'))

            for idx, parent_line in enumerate(parent_lines):
                # Find materials using pre-computed cache (O(1) lookup + O(k) iteration where k = children count)
                material = []
                if parent_line.component:
                    for child_comp in material_children_cache.get(parent_line.component, []):
                        material.extend(materials_by_component.get(child_comp, []))

                # Find labour using cache
                labour = []
                if parent_line.component:
                    for child_comp in labour_children_cache.get(parent_line.component, []):
                        labour.extend(labour_by_component.get(child_comp, []))

                total_cost = 0.0
                if material:
                    mat_total = sum(line.total_cost for line in material)
                    material_total += mat_total
                    total_cost += mat_total
                if labour:
                    total_cost += sum(line.total_cost for line in labour)
                if idx == 0:  # Only first parent gets overhead
                    total_cost += overhead_total

                parent_line.rollup_cost = total_cost

                # Process BOM components using cache
                components = []
                if parent_line.component:
                    for child_comp in bom_children_cache.get(parent_line.component, []):
                        components.extend(boms_by_component.get(child_comp, []))

                for component in components:
                    component_material = []
                    if component.component:
                        for child_comp in material_children_cache.get(component.component, []):
                            component_material.extend(materials_by_component.get(child_comp, []))

                    component_labour = []
                    if component.component:
                        for child_comp in labour_children_cache.get(component.component, []):
                            component_labour.extend(labour_by_component.get(child_comp, []))

                    component_total_cost = 0.0
                    if component_material:
                        component_total_cost += sum(line.total_cost for line in component_material)
                    if component_labour:
                        component_total_cost += sum(line.total_cost for line in component_labour)
                    component.rollup_cost = component_total_cost

            rec.material_total = material_total

    @api.depends('job_labour_line_ids', 'job_labour_line_ids.hours', 'job_labour_line_ids.cost_price')
    def _compute_labor_total(self):
        """compute labor cost"""
        for rec in self:
            rec.labor_total = sum(rec.job_labour_line_ids.mapped('total_cost'))

    @api.depends('job_overhead_line_ids', 'job_overhead_line_ids.product_qty', 'job_overhead_line_ids.cost_price')
    def _compute_overhead_total(self):
        """compute overhead total"""
        for rec in self:
            rec.overhead_total = sum([(p.product_qty * p.cost_price) for p in rec.job_overhead_line_ids])

    def _compute_total_budget_cost(self):
        """Sum of line budget costs (NON-STORED, in-memory). Replaces the old
        write-from-child-on-read that caused serialization conflicts."""
        for rec in self:
            all_lines = rec.job_cost_line_ids | rec.job_labour_line_ids | rec.job_overhead_line_ids
            rec.total_budget_cost = sum(all_lines.mapped('budget_cost'))

    def _compute_total_actual_cost(self):
        """Sum of line actual costs (NON-STORED, in-memory). Replaces the old
        write-from-child-on-read that caused serialization conflicts."""
        for rec in self:
            all_lines = rec.job_cost_line_ids | rec.job_labour_line_ids | rec.job_overhead_line_ids
            rec.total_actual_cost = sum(all_lines.mapped('actual_cost'))

    @api.depends('material_total', 'labor_total', 'overhead_total')
    def _compute_gross_jobcost_total(self):
        """compute gross jobcost"""
        for rec in self:
            rec.gross_jobcost_total = rec.material_total + rec.labor_total + rec.overhead_total

    @api.depends('gross_jobcost_total', 'company_id.factory_admin_overhead')
    def _compute_factory_and_admin_overhead(self):
        """compute overhead cost"""
        # remove this
        for record in self:
            record.factory_and_admin_overhead = 0.0

    @api.depends('gross_jobcost_total', 'gross_profit_markup')
    def _compute_profit_margin(self):
        """compute profit margin"""
        for record in self:
            if record.gross_profit_markup:
                record.profit_margin = record.gross_jobcost_total * (record.gross_profit_markup / 100)
            else:
                record.profit_margin = 0

    def _inverse_profit_margin_markup(self):
        """compute profit margin"""
        for record in self:
            if record.profit_margin:
                record.gross_profit_markup = (record.profit_margin / record.gross_jobcost_total) * 100
            else:
                record.gross_profit_markup = 0

    @api.depends('gross_jobcost_total', 'profit_margin', 'gross_profit_markup')
    def _compute_sale_commission_price(self):
        """Sale price without sale commission = Total Cost + Profit Margin"""
        for rec in self:
            rec.sale_commission_price = rec.gross_jobcost_total + rec.profit_margin

    @api.depends('sale_commission_price', 'profit_margin_percentage')
    def _compute_sale_commission_margin(self):
        """Calculate sale commission margin"""
        for rec in self:
            if rec.profit_margin_percentage:
                rec.sale_commission_margin = rec.sale_commission_price * rec.profit_margin_percentage / (
                        100 - rec.profit_margin_percentage)

    @api.depends('currency_id', 'customer_currency_id')
    def _compute_same_customer_company_currency(self):
        """Hide the total price in customer currency when company, customer currency is same"""
        for record in self:
            if record.currency_id == record.customer_currency_id:
                record.same_customer_company_currency = False
            else:
                record.same_customer_company_currency = True

    @api.depends('jobcost_total', 'currency_rate')
    def _compute_total_price_customer_currency(self):
        """Total price need to represent both customer currency and base currency"""
        for rec in self:
            if rec.customer_currency_id:
                if rec.currency_rate and rec.currency_rate > 0:
                    rec.total_price_customer_currency = rec.jobcost_total / rec.currency_rate
            else:
                rec.total_price_customer_currency = rec.jobcost_total / 1

    @api.depends('gross_jobcost_total', 'profit_margin', 'factory_and_admin_overhead', 'profit_margin_percentage',
                 'sale_commission_margin')
    def _compute_jobcost_total(self):
        """compute jobcost total"""
        for rec in self:
            rec.jobcost_total = rec.gross_jobcost_total + rec.factory_and_admin_overhead + rec.profit_margin + rec.sale_commission_margin

    def _purchase_order_line_count(self):
        """OPTIMIZED: Single read_group instead of search_count per record"""
        counts = {}
        if self.ids:
            data = self.env['purchase.order.line'].read_group(
                [('job_cost_id', 'in', self.ids)], ['job_cost_id'], ['job_cost_id'])
            counts = {row['job_cost_id'][0]: row['job_cost_id_count'] for row in data}
        for order_line in self:
            order_line.purchase_order_line_count = counts.get(order_line.id, 0)

    def _job_costsheet_line_count(self):
        """OPTIMIZED: Single read_group instead of search_count per record"""
        counts = {}
        if self.ids:
            data = self.env['job.cost.line'].read_group(
                [('job_costing_id', 'in', self.ids)], ['job_costing_id'], ['job_costing_id'])
            counts = {row['job_costing_id'][0]: row['job_costing_id_count'] for row in data}
        for jobcost_sheet_line in self:
            jobcost_sheet_line.job_costsheet_line_count = counts.get(jobcost_sheet_line.id, 0)

    def _timesheet_line_count(self):
        """OPTIMIZED: Single read_group instead of search_count per record"""
        counts = {}
        if self.ids:
            data = self.env['account.analytic.line'].read_group(
                [('job_cost_id', 'in', self.ids)], ['job_cost_id'], ['job_cost_id'])
            counts = {row['job_cost_id'][0]: row['job_cost_id_count'] for row in data}
        for timesheet_line in self:
            timesheet_line.timesheet_line_count = counts.get(timesheet_line.id, 0)

    def _account_invoice_line_count(self):
        """OPTIMIZED: Single read_group instead of search_count per record"""
        counts = {}
        if self.ids:
            data = self.env['account.move.line'].read_group(
                [('job_cost_id', 'in', self.ids)], ['job_cost_id'], ['job_cost_id'])
            counts = {row['job_cost_id'][0]: row['job_cost_id_count'] for row in data}
        for invoice_line in self:
            invoice_line.account_invoice_line_count = counts.get(invoice_line.id, 0)

    def action_draft(self):
        """inbuilt function from the vendor"""
        for rec in self:
            rec.state = 'draft'

    def action_confirm(self):
        """inbuilt function from the vendor"""
        for rec in self:
            rec.state = 'confirm'

    def update_sequence(self):
        for line in self.job_cost_line_ids:
            line.sequence += 1

    def action_sent_for_first_approval(self):
        # """sent for approval"""
        if self.currency_rate <= 0:
            raise UserError(_('Please Update Exchange Rate'))
        self.update_sequence()
        for line in self.job_cost_line_ids:
            if line.material_type not in ['bom', 'parent'] and not line.partner_id:
                raise UserError(
                    _('Please Add Vendor for Material (' + str(line.sequence) + ') - ' + str(line.display_name)))

        amount = self.currency_id._convert(self.jobcost_total, self.currency_id, self.company_id,
                                           self.start_date or fields.Date.today())
        review_line = self.company_id.automatic_approval_lines.filtered(lambda x: x.is_review == True)
        vals = []
        count = 1

        if not review_line:
            raise UserError(_("Please define an approval line for the Job Costing value."))
        if review_line:
            for user in review_line.user_ids:
                vals.append((0, 0, {
                    'sequence': count,
                    'user_id': user.id,
                }))
                count += 1

        return {
            'name': _('Send For Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'job.costing.approvers.wizard',
            'target': 'new',
            'context': {'default_job_costing_approver_line_ids': vals,
                        'default_approval_type': 'review'}
        }

    def action_sent_for_second_approval(self):
        """Loads the wizard to send for approval"""
        amount = self.currency_id._convert(self.jobcost_total, self.currency_id, self.company_id,
                                           self.start_date or fields.Date.today())
        approval_line = self.company_id.automatic_approval_lines.filtered(
            lambda x: x.to_limit >= amount and x.condition == 'below' or
                      x.to_limit <= amount and x.condition == 'above' or x.to_limit >= amount >= x.from_amount)
        vals = []
        count = 1

        if not approval_line:
            raise UserError(_("Please define an approval line for the Job Costing value."))

        if approval_line:
            for user in approval_line.user_ids:
                vals.append((0, 0, {
                    'sequence': count,
                    'user_id': user.id,
                }))
                count += 1
        return {
            'name': _('Send For Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'job.costing.approvers.wizard',
            'target': 'new',
            'context': {'default_job_costing_approver_line_ids': vals,
                        'default_approval_type': 'approve'}
        }

    def action_sent_for_production_approval(self):
        """sent for approval"""
        # model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        # mail_body = {
        #     'subject': 'Request For Approve - %s' % self.name,
        #     'msg_type': 'Please approve this record'
        # }
        # return {
        #     'name': _('Request approval'),
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'request.user.approve.wizard',
        #     'target': 'new',
        #     'context': {
        #         'default_model_id': model.id,
        #         'mail_body': mail_body,
        #         'approve_group': self.env.ref('odoo_job_costing_management.group_job_costing_production').ids
        #     }
        # }
        user_ids = self.env.ref("odoo_job_costing_management.group_job_costing_production").users.ids
        users = self.env['res.users'].browse(user_ids)
        # amount = self.currency_id._convert(self.jobcost_total, self.currency_id, self.company_id,
        #                                    self.start_date or fields.Date.today())
        # approval_line = self.company_id.automatic_approval_lines.filtered(
        #     lambda x: x.to_limit >= amount and x.condition == 'below' or
        #               x.to_limit <= amount and x.condition == 'above' or x.to_limit >= amount >= x.from_amount)
        vals = []
        count = 1

        if not user_ids:
            raise UserError(_("Please define users with Production Access Level."))

        if users:
            for user in users:
                vals.append((0, 0, {
                    'sequence': count,
                    'user_id': user.id,
                }))
                count += 1
        return {
            'name': _('Send For Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'job.costing.approvers.wizard',
            'target': 'new',
            'context': {'default_job_costing_approver_line_ids': vals,
                        'default_approval_type': 'approve'}
        }

    def send_to_next_approver(self):
        """This function automatically sets next available approver."""
        if self.state == 'draft':
            self.write({
                'state': 'waiting_first_approval'
            })
        elif self.state == 'confirm':
            self.write({
                'state': 'waiting_second_approval'
            })
        elif self.state == 'ready_for_production':
            self.write({
                'state': 'waiting_production_approval'
            })
        next_approvers = self.job_costing_approval_line_ids.filtered(lambda x: x.state == 'pending')
        if next_approvers:
            next_approvers[0].write({
                'state': 'requested',
                'approval_request_datetime': datetime.now(),
            })
            template_id = self.env.ref(
                'odoo_job_costing_management.odoo_job_costing_management_request_for_approval_mail_template')
            msg = 'There is a pending Job Costing Sheet for your approval.'
            model = self._context.get('params').get('model') if self._context.get('params') else self._context.get(
                'active_model')
            self.with_context(mail_body={}).send_email_job_costing(self.id, 'job.costing',
                                                                   "Request for Approval", next_approvers[0].user_id,
                                                                   template_id, msg)

    def send_email_job_costing(self, record, model, subject, users, template_id, msg):
        """Common function to send email. Parameters contains all required date for the mail template"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = '%s/web?login/#id=%s&view_type=form&model=%s' % (base_url, record, model)
        context = self.env.context.get('mail_body')
        context['mail_to'] = ','.join([str(x.partner_id.id) for x in users])
        context['custom_url'] = url
        context['subject'] = subject
        context['msg_type'] = msg
        self.env['mail.template'].sudo().browse(template_id.id).with_context(context).send_mail(self.id, True)

    def action_requested_approval(self, approval_requested_by, approval_requested_date, approval_requested_users):
        """function for after request the approval
            state changed to waiting approve
        """
        if self.state == 'draft':
            self.write({
                'first_approval_requested_by': approval_requested_by,
                'first_approval_requested_date': approval_requested_date,
                'first_approval_requested_users': approval_requested_users,
                'state': 'waiting_first_approval'
            })
        if self.state == 'confirm':
            self.write({
                'approval_requested_by': approval_requested_by,
                'approval_requested_date': approval_requested_date,
                'approval_requested_users': approval_requested_users,
                'state': 'waiting_second_approval'
            })
        if self.state == 'ready_for_production':
            self.write({
                'production_approval_requested_by': approval_requested_by,
                'production_approval_requested_date': approval_requested_date,
                'production_approval_requested_users': approval_requested_users,
                'state': 'waiting_production_approval'
            })

    def action_first_approve(self):
        """approve button action and popup approve wizard"""

        approver_line = self.job_costing_approval_line_ids.filtered(
            lambda x: x.user_id.id == self._uid and x.state == 'requested')
        if not approver_line:
            raise UserError("You Don't have access to approve.")
        approver_line.write({
            'state': 'reviewed',
            'status_updated_datetime': datetime.now(),
        })
        next_approver_line = self.job_costing_approval_line_ids.filtered(lambda x: x.state == 'pending')
        if next_approver_line:
            self.send_to_next_approver()
        else:
            template_id = self.env.ref(
                'odoo_job_costing_management.odoo_job_costing_management_reject_or_approve_template')
            msg = 'The following Job Costing Sheet is approved by %s' % self.env['res.users'].browse(self._uid).name
            self.with_context(mail_body={}).send_email_job_costing(self.id, 'job.costing',
                                                                "Reviewed", self.create_uid, template_id, msg)
            self.state = 'confirm'
            

    def action_second_approve(self):
        """approve button action and popup approve wizard"""
        # model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        # mail_body = {
        #     'subject': 'Request has been Approved - %s' % self.name,
        #     'msg_type': 'Your record have been Approved'
        # }
        # return {
        #     'name': _('Approve'),
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'request.approve.reject.wizard',
        #     'target': 'new',
        #     'context': {
        #         'default_model_id': model.id,
        #         'mail_body': mail_body,
        #         'default_action_type': 'approve',
        #         'default_requested_user': self.approval_requested_by.id
        #     }
        # }
        approver_line = self.job_costing_approval_line_ids.filtered(
            lambda x: x.user_id.id == self._uid and x.state == 'requested')
        if not approver_line:
            raise UserError("You Don't have access to approve.")
        approver_line.write({
            'state': 'approved',
            'status_updated_datetime': datetime.now(),
        })
        next_approver_line = self.job_costing_approval_line_ids.filtered(lambda x: x.state == 'pending')
        if next_approver_line:
            self.send_to_next_approver()
        else:
            template_id = self.env.ref(
                'odoo_job_costing_management.odoo_job_costing_management_reject_or_approve_template')
            msg = 'The following Job Costing Sheet is approved by %s' % self.env['res.users'].browse(self._uid).name
            self.with_context(mail_body={}).send_email_job_costing(self.id, 'job.costing',
                                                                   "Approved", self.create_uid, template_id, msg)
            self.state = 'approved'
            self.update_sales_price()

    def action_production_approve(self):
        """approve button action and popup approve wizard"""

        approver_line = self.job_costing_approval_line_ids.filtered(
            lambda x: x.user_id.id == self._uid and x.state == 'requested')
        if not approver_line:
            raise UserError("You Don't have access to approve.")
        approver_line.write({
            'state': 'approved',
            'status_updated_datetime': datetime.now(),
        })
        next_approver_line = self.job_costing_approval_line_ids.filtered(lambda x: x.state == 'pending')
        if next_approver_line:
            self.send_to_next_approver()
        else:
            template_id = self.env.ref(
                'odoo_job_costing_management.odoo_job_costing_management_reject_or_approve_template')
            msg = 'The following Job Costing Sheet is approved by %s' % self.env['res.users'].browse(self._uid).name
            self.with_context(mail_body={}).send_email_job_costing(self.id, 'job.costing',
                                                                   "Approved", self.create_uid, template_id, msg)
            self.state = 'done'
            products = self.finished_good_ids.mapped('product_id')
            if products:
                # Resolve routes once outside the loop
                route_ids = []
                mto_route = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
                manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
                if mto_route:
                    route_ids.append(mto_route.id)
                else:
                    raise UserError(_("Could not find the Make To Order Route to map to the product"))
                if manufacture_route:
                    route_ids.append(manufacture_route.id)
                else:
                    raise UserError(_("Could not find the Manufacture Route to map to the product"))
                # OPTIMIZED: Single batch write instead of per-product write
                products.write({
                    'detailed_type': 'product',
                    'sale_ok': True,
                    'purchase_ok': False,
                    'route_ids': [(6, 0, route_ids)]
                })

            if self.is_revised:
                self.create_bom(self.number)
            else:
                self.create_bom()


    def action_approve_the_request(self, approved_by, approved_date, approved_note):
        """function for after the approval
            state changed to approved
        """
        approval_method = self.env['ir.config_parameter'].sudo().get_param(
            'centrics_user_approve.multiple_approval_method') or False
        if self.state == 'waiting_first_approval':
            self.write({
                'first_approved_by': [(4, approved_by.id)],
                'first_approved_date': approved_date,
                'first_approved_note': self.approved_note if self.approved_note else '' + approved_note if approved_note else '',
            })
            message = _('Approved By - %s <br/> Approved Date - %s  ' % (approved_by.name, str(approved_date)))
            self.sudo().message_post(body=message, message_type='comment')
        if self.state == 'waiting_second_approval':
            self.write({
                'approved_by': [(4, approved_by.id)],
                'approved_date': approved_date,
                'approved_note': self.approved_note if self.approved_note else '' + approved_note if approved_note else ''
            })
            message = _('Approved By - %s <br/> Approved Date - %s  ' % (approved_by.name, str(approved_date)))
            self.sudo().message_post(body=message, message_type='comment')
        if self.state == 'waiting_production_approval':
            self.write({
                'production_approved_by': [(4, approved_by.id)],
                'production_approved_date': approved_date,
                'production_approved_note': self.approved_note if self.approved_note else '' + approved_note if approved_note else '',
            })
            message = _('Approved By - %s <br/> Approved Date - %s  ' % (approved_by.name, str(approved_date)))
            self.sudo().message_post(body=message, message_type='comment')
        if approval_method:
            if approval_method == "all":
                if self.state == 'waiting_first_approval':
                    if self.approval_requested_users == self.first_approved_by:
                        self.state = 'confirm'
                    else:
                        self.state = 'waiting_first_approval'
                if self.state == 'waiting_second_approval':
                    if self.approval_requested_users == self.approved_by:
                        self.state = 'approved'
                        self.update_sales_price()
                    else:
                        self.state = 'waiting_second_approval'
                if self.state == 'waiting_production_approval':
                    if self.production_approval_requested_users == self.production_approved_by:
                        self.state = 'done'
                        self.create_bom()
                        self.create_budget()
                    else:
                        self.state = 'waiting_production_approval'
            else:
                if self.state == 'waiting_first_approval':
                    self.state = 'confirm'
                if self.state == 'waiting_second_approval':
                    self.state = 'approved'
                    self.update_sales_price()
                if self.state == 'waiting_production_approval':
                    self.state = 'done'
                    self.create_bom()
                    self.create_budget()
        else:
            if self.state == 'waiting_first_approval':
                self.state = 'confirm'
            if self.state == 'waiting_second_approval':
                self.state = 'approved'
                self.update_sales_price()
            if self.state == 'waiting_production_approval':
                self.state = 'done'
                self.create_bom()
                self.create_budget()

    def update_sales_price(self):
        """Allocate the sheet's totals across finished goods and emit
        categorised invoiceable lines on the quotation.

        Allocation rules:
          - Each finished good carries its prorated share of the sheet's
            total cost (`jobcost_total`), pro-rated by its `product_qty`
            relative to the sum of all finished-good qtys.
          - One invoiceable line per finished good (`category='product'`).
          - One aggregated invoiceable line for Labor (`category='labor'`).
          - One aggregated invoiceable line for Overhead (`category='overhead'`).
          - The matching `sale.order.line` price_unit is updated so standard
            `_create_invoices` / partial-qty invoicing propagates the values.
        """
        if not self.quotation_id:
            return
        finished_goods = self.finished_good_ids.filtered(lambda fg: fg.product_id)
        if not finished_goods:
            return

        # Currency conversion: pick the rate that maps company → customer.
        cross_currency = self.currency_id.id != self.customer_currency_id.id
        rate = self.currency_rate or 1.0
        if cross_currency and not self.currency_rate:
            return  # nothing we can do without a rate

        def to_customer(amount):
            return amount / rate if cross_currency else amount

        # Pricelist alignment when crossing currencies — kept from the original
        # method so downstream pricing logic still finds a usable list.
        if cross_currency and self.quotation_id.partner_id:
            partner_pl = self.quotation_id.partner_id.property_product_pricelist
            if partner_pl and partner_pl.currency_id.id == self.customer_currency_id.id:
                price_list = partner_pl
            else:
                price_list = self.env['product.pricelist'].search([
                    ('currency_id', '=', self.customer_currency_id.id)
                ], limit=1)
            if price_list:
                self.quotation_id.pricelist_id = price_list.id
                self.quotation_id.action_update_prices()

        # Allocate jobcost_total across finished goods, pro-rated by qty.
        total_qty = sum(finished_goods.mapped('product_qty')) or 1.0
        jobcost_total_customer = to_customer(self.jobcost_total)

        sol_writes = []  # (sale.order.line, price_unit) — applied at the end
        fg_writes = []   # (finished_good, unit_price)
        inv_vals_list = []

        for fg in finished_goods:
            fg_share = jobcost_total_customer * (fg.product_qty / total_qty)
            unit_price = fg_share / fg.product_qty if fg.product_qty else 0.0
            fg_writes.append((fg, unit_price))
            if fg.sale_order_line_id:
                sol_writes.append((fg.sale_order_line_id, unit_price))

            inv_vals_list.append({
                'order_id': self.quotation_id.id,
                'product_id': fg.product_id.id,
                'name': fg.product_id.display_name,
                'product_uom_qty': fg.product_qty,
                'product_uom': fg.product_uom_id.id,
                'tax_id': fg.sale_order_line_id.tax_id.ids if fg.sale_order_line_id else [],
                'price_unit': unit_price,
                'category': 'product',
                'job_costing_id': self.id,
                'finished_good_id': fg.id,
            })

        # Aggregate Labor and Overhead (single line each, regardless of how
        # many finished goods exist).
        if self.labor_total:
            inv_vals_list.append({
                'order_id': self.quotation_id.id,
                'name': _('Labor — %s') % (self.number or self.name or ''),
                'product_uom_qty': 1.0,
                'price_unit': to_customer(self.labor_total),
                'category': 'labor',
                'job_costing_id': self.id,
            })
        if self.overhead_total:
            inv_vals_list.append({
                'order_id': self.quotation_id.id,
                'name': _('Overhead — %s') % (self.number or self.name or ''),
                'product_uom_qty': 1.0,
                'price_unit': to_customer(self.overhead_total),
                'category': 'overhead',
                'job_costing_id': self.id,
            })

        # Drop any prior invoiceable lines this sheet generated, then recreate.
        existing = self.quotation_id.invoiceable_line.filtered(
            lambda l: l.job_costing_id.id == self.id)
        if existing:
            existing.unlink()
        if inv_vals_list:
            self.env['invoiceable.lines'].create(inv_vals_list)

        # Propagate prices to the SO lines (so standard invoicing flows pick
        # them up). Group identical prices to minimise writes.
        for sol, price in sol_writes:
            if sol.price_unit != price:
                sol.price_unit = price
        for fg, price in fg_writes:
            fg.unit_price = price

    def action_reject_the_request(self, rejected_by, rejected_date, rejected_note):
        """function for after the rejected
            state changed to rejected
        """
        self.write({
            'rejected_by': [(4, rejected_by.id)],
            'rejected_date': rejected_date,
            'rejected_note': self.rejected_note if self.rejected_note else '' + rejected_note if rejected_note else '',
        })
        message = _(
            'Reject By - %s <br/> Reject Date - %s  ' % (rejected_by.name, str(rejected_date)))
        self.sudo().message_post(body=message, message_type='comment')
        self.action_cancel()

    def action_user_reject(self):
        """Reject button action and popup Reject wizard"""
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': 'Request has been rejected  - %s' % self.name,
            'msg_type': 'Your record have been rejected'
        }
        return {
            'name': _('Reject'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'request.approve.reject.wizard',
            'target': 'new',
            'context': {
                'default_model_id': model.id,
                'mail_body': mail_body,
                'default_action_type': 'reject',
                'default_requested_user': self.approval_requested_by.id or self.first_approval_requested_by.id
            }
        }

    def action_cancel(self):
        """cancel sales order"""
        for rec in self:
            if rec.state == 'waiting_production_approval':
                rec.state = 'ready_for_production'
            else:
                rec.state = 'cancel'

    def action_view_purchase_order_line(self):
        """view purchase order line — OPTIMIZED: use domain directly, skip intermediate search"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order Line',
            'res_model': 'purchase.order.line',
            'domain': [('job_cost_id', '=', self.id)],
            'view_type': 'form',
            'view_mode': 'tree,form',
        }

    def action_view_hr_timesheet_line(self):
        """view timesheet lines — OPTIMIZED: use domain directly"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_timesheet.act_hr_timesheet_line")
        action['domain'] = [('job_cost_id', '=', self.id)]
        return action

    def action_view_jobcost_sheet_lines(self):
        """view job cost lines — OPTIMIZED: use domain directly"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("odoo_job_costing_management.action_job_cost_line_custom")
        action['domain'] = [('job_costing_id', '=', self.id)]
        ctx = 'context' in action and action['context'] and eval(action['context']).copy() or {}
        ctx.update(create=False)
        ctx.update(edit=False)
        ctx.update(delete=False)
        action['context'] = ctx
        return action

    def action_view_vendor_bill_line(self):
        """View vendor bill lines — OPTIMIZED: use domain directly"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Account Invoice Line',
            'res_model': 'account.move.line',
            'domain': [('job_cost_id', '=', self.id)],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': {'create': False, 'edit': False},
        }

    def create_bom(self, revise_no = False):
        """create a bom and bom lines
        OPTIMIZED: Batch fetch BOMs once and use dictionary lookup instead of search per line"""
        # --- Source B: attach NEW lines to their copied (job-cost) BOM ---
        # Resolve the target BOM from the line's direct relations (bom_id / parent_bom_id)
        # instead of matching on display_name, and guard so only this sheet's BOMs are
        # touched. Idempotent: skip lines already linked from a previous run.

        # Labour operations
        new_labour = self.job_labour_line_ids.filtered(lambda l: l.new_line)
        already_routed = set()
        if new_labour:
            already_routed = set(self.env['mrp.routing.workcenter'].search(
                [('jobcost_line_id', 'in', new_labour.ids)]).mapped('jobcost_line_id.id'))
        routing_vals_list = []
        for line in new_labour:
            if line.id in already_routed:
                continue
            target_bom = line.bom_id or line.parent_bom_id
            if not target_bom or target_bom.job_cost_id.id != self.id:
                continue
            routing_vals_list.append({
                "name": line.work_center_id.name,
                "workcenter_id": line.work_center_id.id,
                'bom_id': target_bom.id,
                "time_cycle_manual": 60 * line.hour,
                "jobcost_line_id": line.id,
            })
        if routing_vals_list:
            self.env['mrp.routing.workcenter'].create(routing_vals_list)

        # New materials are entered as the TOTAL planned quantity across all finished
        # goods. The BOM line must hold the per-finished-good quantity so that exploding
        # the finished-good MOs reproduces the entered total (e.g. 25 entered across
        # 5 finished goods -> BOM line of 5).
        finished_good_qty = sum(self.finished_good_ids.mapped('product_qty')) or 1.0

        # Material components
        new_materials = self.job_cost_line_ids.filtered(lambda l: l.new_line)
        existing_bom_lines = {}
        if new_materials:
            for bl in self.env['mrp.bom.line'].search([('jobcost_line_id', 'in', new_materials.ids)]):
                existing_bom_lines.setdefault(bl.jobcost_line_id.id, bl)
        bom_line_vals_list = []
        lines_for_vals = []
        for line in new_materials:
            existing = existing_bom_lines.get(line.id)
            if existing:
                # Already attached on a previous run; keep the link and baseline.
                line.bom_line_id = existing.id
                if not line.original_product_qty:
                    line.original_product_qty = line.product_qty
                continue
            target_bom = line.parent_bom_id
            if not target_bom or target_bom.job_cost_id.id != self.id:
                continue
            bom_line_vals_list.append({
                'product_id': line.product_id.id,
                'bom_id': target_bom.id,
                'jobcost_line_id': line.id,
                'product_uom_id': line.uom_id.id,
                'product_qty': line.product_qty / finished_good_qty,
            })
            lines_for_vals.append(line)
        if bom_line_vals_list:
            created = self.env['mrp.bom.line'].create(bom_line_vals_list)
            for line, bom_line in zip(lines_for_vals, created):
                # Link back and set baseline so future runs/edits sync correctly.
                line.bom_line_id = bom_line.id
                line.original_product_qty = line.product_qty

        # --- Source A: ratio-sync edited quantities of existing leaf components ---
        # The line stores the exploded quantity while the BOM line stores the per-parent
        # quantity, so scale by (new / original) to preserve the explosion semantics.
        for line in self.job_cost_line_ids:
            if line.new_line or line.material_type != 'component' or not line.bom_line_id:
                continue
            bom_line = line.bom_line_id
            if bom_line.bom_id.job_cost_id.id != self.id:
                continue
            if not line.original_product_qty or line.original_product_qty == line.product_qty:
                continue
            ratio = line.product_qty / line.original_product_qty
            vals = {'product_qty': bom_line.product_qty * ratio}
            if line.uom_id and bom_line.product_uom_id.id != line.uom_id.id:
                vals['product_uom_id'] = line.uom_id.id
            bom_line.write(vals)

        # Iterate finished goods on the sheet — one BOM per finished good.
        # Pre-fetch previous revision per product template (single batch search).
        finished_goods = self.finished_good_ids.filtered(lambda fg: fg.product_id)
        previous_revision_by_tmpl = {}
        if revise_no and finished_goods:
            tmpl_ids = finished_goods.mapped('product_id.product_tmpl_id').ids
            revision_boms = self.env['mrp.bom'].search([
                ('job_cost_id', '=', self.id),
                ('product_tmpl_id', 'in', tmpl_ids),
            ], order='id desc')
            for bom in revision_boms:
                previous_revision_by_tmpl.setdefault(bom.product_tmpl_id.id, bom.name)

        # Pre-build the shared bom_line_ids commands once (parent material lines
        # apply to every finished good).
        parent_materials = self.job_cost_line_ids.filtered(
            lambda x: x.job_type == 'material' and x.material_type == 'parent')
        shared_bom_line_cmds = [(0, 0, {
            'product_id': material.product_id.id,
            'jobcost_line_id': material.id,
            'product_qty': material.product_qty,
        }) for material in parent_materials]

        for fg in finished_goods:
            if revise_no:
                previous_revision = previous_revision_by_tmpl.get(
                    fg.product_id.product_tmpl_id.id)
                if previous_revision and '-R' in previous_revision:
                    try:
                        next_revision = int(previous_revision.split('-R')[1]) + 1
                    except (IndexError, ValueError):
                        next_revision = 1
                else:
                    next_revision = 1
            else:
                next_revision = 1
            values = {
                "name": revise_no + '-R' + str(next_revision) if revise_no else False,
                "product_tmpl_id": fg.product_id.product_tmpl_id.id,
                "product_id": fg.product_id.id,
                "job_cost_id": self.id,
                "analytic_plan_id": self.analytic_plan_id.id,
                "type": 'normal',
                "product_qty": fg.product_qty,
                "bom_line_ids": list(shared_bom_line_cmds),
                "byproduct_ids": [],
            }
            bom = self.env['mrp.bom'].create(values)
            fg.bom_id = bom.id

    def create_budget(self):
        """creating a budget and it's budget line"""
        budget = {
            "name": self.project_id.display_name,
            "date_from": None,
            "date_to": None,
            "crossovered_budget_line": []
        }
        for cost_line in self.job_cost_line_ids + self.job_labour_line_ids + self.job_overhead_line_ids:
            budget["crossovered_budget_line"].append((0, 0, {
                'analytic_account_id': self.analytic_id.id,
                'line_type': cost_line.job_type,
                'jobtype_id': cost_line.job_type_id.id,
                'costsheet_id': cost_line.job_costing_id.id,
                'jobcost_line_id': cost_line.id,
                'product_id': cost_line.product_id.id,
                'uom_id': cost_line.uom_id.id,
                'description': cost_line.description,

                'date_from': cost_line.job_costing_id.start_date,
                'date_to': cost_line.job_costing_id.complete_date,
                'planned_amount': cost_line.total_cost,
                'material_planned_qyt': cost_line.product_qty if cost_line.job_type == 'material' else 0,
                'overhead_planned_qyt': cost_line.product_qty if cost_line.job_type == 'overhead' else 0,
                'labour_hour': cost_line.hours,
            }))
        budget_obj = self.env['crossovered.budget'].create(budget)
        return budget_obj

    def action_open_quotation(self):
        # open the quotation for the current job costing sheet
        if self.quotation_id:
            return {
                'name': 'Sale Order',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.quotation_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current'
            }

    def action_open_lead(self):
        # open the lead for the current job costing sheet
        if self.lead_id:
            return {
                'name': 'Lead',
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': self.lead_id.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current'
            }

    def action_view_purchase_requisitions(self):
        """view Purchase Requisitions"""
        self.ensure_one()
        purchase_req_obj = self.env['material.purchase.requisition']
        purchase_req_lines_obj = self.env['material.purchase.requisition.line']
        cost_ids = purchase_req_lines_obj.search([('job_costing_id', '=', self.id)])
        if cost_ids:
            purchase_req = purchase_req_obj.browse(cost_ids.mapped('requisition_id').ids)
            if purchase_req:
                action = {'type': 'ir.actions.act_window',
                          'name': 'Purchase Requisitions',
                          'res_model': 'material.purchase.requisition',
                          # 'res_id': self.id,
                          'domain': [('id', 'in', purchase_req.ids)],
                          'view_type': 'form',
                          'view_mode': 'tree,form'
                          }
                return action

    def action_add_standard_components(self):
        finished_good_qty = sum(self.finished_good_ids.mapped('product_qty'))
        return {
            'name': _('Request approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'add.components.wizard',
            'target': 'new',
            'context': {
                'default_boat_type_id': self.boat_type_id.id,
                'default_quantity': int(finished_good_qty) or 1,
            }
        }

    def action_add_component(self, job_components=False, quantity=1):
        """
        Adds components and their details to the job cost lines list and processes BOM
        (Bill of Materials) data to generate job costs and labour entries.

        OPTIMIZED: Batch queries for vendor lookups to eliminate N+1 queries.

        This method processes a given set of job components and their associated BOMs
        to generate job cost material and labour lines for a project.

        Parameters:
            job_components (bool or list): A list of job components containing BOMs or
                False if no components are provided to process.
            quantity (int): The quantity multiplier for the materials in the BOM. By
                default, it is set to 1.

        Returns:
            None: The method updates internal attributes of the object and does not
            return any value.
        """
        lines = []
        start_date = False
        if job_components:
            if self.project_start_date:
                start_date = datetime(self.project_start_date.year,
                                      self.project_start_date.month,
                                      self.project_start_date.day, 8, 30, 0)
            for job_component in job_components:
                new_component = job_component.copy()
                new_component.write({'is_this_standard_bom':False}),
                new_component.name = self.display_name + '_' + new_component.product_tmpl_id.name
                new_component.job_cost_id = self.id
                if new_component.bom_line_ids:
                    if new_component.bom_line_ids.child_bom_id:
                        for child_bom in new_component.bom_line_ids.child_bom_id:
                            new_child_bom = child_bom.copy()
                            new_child_bom.name = self.display_name + '_' + new_child_bom.product_tmpl_id.name
                            new_child_bom.job_cost_id = self.id
                            child_bom = new_child_bom
                # when bom is doesn't map
                for line in new_component.bom_line_ids:
                    line._compute_child_bom_id()
                materials = []
                labour = []
                names = []
                bom_details = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=new_component.id)
                if bom_details:
                    lines = bom_details.get('lines')
                    if lines:
                        value = self.job_cost_line_ids.filtered(lambda x: x.material_type == 'parent')
                        vals = {
                            'material_index': str(lines.get('index')).replace(str(lines.get('index'))[0],
                                                                              str(len(value)),
                                                                              1) if value else lines.get('index'),
                            'bom_id': lines.get('bom_id'),
                            'component': lines.get('name'),
                            'material_type': 'parent',
                            'product_id': lines.get('product_id'),
                            'product_qty': lines.get('quantity') * quantity,
                            'uom_id': lines.get('uom').id,
                            'cost_price': 0.0,
                            'job_type': 'material',
                        }
                        materials.append((0, 0, vals))
                        names.append(lines.get('product').name)
                        components = []
                        operations = []
                        if lines.get('components'):
                            [x.update({'parent_code': lines.get('name')}) for x in lines.get('components')]
                            components.append(lines.get('components'))
                        if lines.get('operations'):
                            [x.update({'parent_code': lines.get('name')}) for x in lines.get('operations')]
                            operations.append(lines.get('operations'))

                        # OPTIMIZATION: Collect all product_tmpl_ids and BOM line keys for batch lookup
                        product_tmpl_ids_to_lookup = set()
                        bom_line_lookup_keys = set()  # (bom_id, product_id, product_qty)
                        all_component_lines = []
                        if components:
                            # First pass: collect all product template IDs and BOM line keys
                            temp_components = list(components)
                            for component in temp_components:
                                for line in component:
                                    if line.get('type') == 'component':
                                        product = self.env['product.product'].browse(line.get('product_id'))
                                        if product:
                                            product_tmpl_ids_to_lookup.add(product.product_tmpl_id.id)
                                        # Collect BOM line lookup keys
                                        if line.get('parent_id') and line.get('product_id') and line.get('base_bom_line_qty'):
                                            bom_line_lookup_keys.add((
                                                line.get('parent_id'),
                                                line.get('product_id'),
                                                line.get('base_bom_line_qty')
                                            ))
                                    if line.get('components'):
                                        temp_components.append(line.get('components'))

                            # BATCH QUERY: Fetch all vendors in single query
                            vendor_info_by_tmpl = {}
                            if product_tmpl_ids_to_lookup:
                                all_vendors = self.env['product.supplierinfo'].search([
                                    ('product_tmpl_id', 'in', list(product_tmpl_ids_to_lookup))
                                ], order='product_tmpl_id, job_cost_price')
                                # Group by product_tmpl_id, keeping only first (cheapest) vendor
                                for vendor in all_vendors:
                                    if vendor.product_tmpl_id.id not in vendor_info_by_tmpl:
                                        vendor_info_by_tmpl[vendor.product_tmpl_id.id] = vendor

                            # BATCH QUERY: Fetch all BOM lines in single query
                            bom_lines_by_key = {}
                            if bom_line_lookup_keys:
                                bom_ids = list(set(k[0] for k in bom_line_lookup_keys))
                                product_ids = list(set(k[1] for k in bom_line_lookup_keys))
                                all_bom_lines = self.env['mrp.bom.line'].search([
                                    ('bom_id', 'in', bom_ids),
                                    ('product_id', 'in', product_ids)
                                ])
                                # Group by (bom_id, product_id, product_qty) for O(1) lookup
                                for bl in all_bom_lines:
                                    key = (bl.bom_id.id, bl.product_id.id, bl.product_qty)
                                    if key not in bom_lines_by_key:
                                        bom_lines_by_key[key] = bl

                            # Second pass: process components with prefetched vendor and BOM line data
                            for component in components:
                                for line in component:
                                    cost = 0
                                    vendor = False
                                    bom_line = False
                                    currency_id = False
                                    currency_rate = False
                                    if line.get('type') == 'bom':
                                        if line.get('parent_code'):
                                            line.update(
                                                {'parent_code': line.get('parent_code') + '/' + line.get('name'),
                                                 'is_this_standard_bom': False,
                                                 })
                                        else:
                                            line.update({'parent_code': line.get('name')})
                                    elif line.get('type') == 'component':
                                        product_tmpl = self.env['product.product'].browse(line.get('product_id'))
                                        if product_tmpl:
                                            # Use batch-fetched vendor info (O(1) lookup)
                                            vendor = vendor_info_by_tmpl.get(product_tmpl.product_tmpl_id.id)
                                        if vendor:
                                            cost = vendor.job_cost_price
                                            currency_id = vendor.currency_id.id
                                            currency_rate = vendor.currency_id.inverse_rate
                                        elif line.get('product'):
                                            cost = line.get('product').last_purchase_price if line.get(
                                                'product').last_purchase_price else line.get('product').standard_price
                                        if line.get('parent_id'):
                                            # Use batch-fetched BOM line (O(1) lookup)
                                            bom_line_key = (line.get('parent_id'), line.get('product_id'), line.get('base_bom_line_qty'))
                                            bom_line = bom_lines_by_key.get(bom_line_key)
                                    vals = {
                                        'material_index': line.get('index').replace(line.get('index')[0],
                                                                                    str(len(value)),
                                                                                    1) if value else line.get('index'),
                                        'bom_id': line.get('bom_id') if line.get('bom_id') else False,
                                        'component': line.get('parent_code'),
                                        'material_type': line.get('type'),
                                        'product_id': line.get('product_id'),
                                        'product_qty': line.get('quantity') * quantity,
                                        'original_product_qty': line.get('quantity') * quantity,
                                        'uom_id': line.get('uom').id,
                                        'job_type': 'material',
                                        'partner_id': vendor.partner_id.id if vendor else False,
                                        'cost_price': cost,
                                        'supplier_currency_id': currency_id,
                                        'supplier_currency_rate': currency_rate,
                                        'bom_line_id': bom_line.id if bom_line else False,
                                    }
                                    names.append(line.get('product').name)
                                    materials.append((0, 0, vals))
                                    if line.get('components'):
                                        [x.update({'parent_code': line.get('parent_code')}) for x in
                                         line.get('components') if line.get('parent_code')]
                                        components.append(line.get('components'))
                                        [x.update({'parent_code': line.get('parent_code')}) for x in
                                         line.get('operations') if line.get('parent_code')]
                                        operations.append(line.get('operations'))

                        if operations:
                            count = 1
                            for operation in operations:
                                for line in operation:
                                    hour = line.get('quantity') / 60 if line.get('quantity') else 0
                                    hour = hour * quantity
                                    vals = {
                                        'labour_index': line.get('index').replace(line.get('index')[0], str(len(value)),
                                                                                  1) if value else line.get('index'),
                                        'sequence': count,
                                        # 'job_type_id': line.get('operation').workcenter_id.id,
                                        'component': line.get('parent_code'),
                                        'bom_id': line.get('operation').bom_id.id if line.get(
                                            'operation').bom_id else False,
                                        'work_center_id': line.get('operation').workcenter_id.id if line.get(
                                            'operation').workcenter_id else False,
                                        'bom_operation_id': line.get('operation').id,
                                        'hour': hour,
                                        'workcenter_cost_price': line.get(
                                            'operation').workcenter_id.costs_hour if line.get(
                                            'operation').workcenter_id else 0,
                                        'job_type': 'labour',
                                        'operation_start_date': start_date,
                                        'operation_end_date': (
                                                start_date + timedelta(hours=hour)) if start_date else False,
                                        'description': "Charges of %s" % line.get(
                                            'operation').workcenter_id.name if line.get(
                                            'operation').workcenter_id else False
                                    }
                                    labour.append((0, 0, vals))
                                    start_date = (start_date + timedelta(hours=hour)) if start_date else False
                                    count += 1
                self.job_cost_line_ids = materials
                # OPTIMIZED: Build dict for O(1) parent lookups instead of O(n²) filtered()
                material_by_index = {}
                for line in self.job_cost_line_ids:
                    if line.material_index:
                        existing = material_by_index.get(line.material_index)
                        if not existing or line.id > existing.id:
                            material_by_index[line.material_index] = line
                index = 0
                for line in self.job_cost_line_ids:
                    if not line.material_type == 'parent':
                        parent_index = line.material_index[:-1] if line.material_index else False
                        parent = material_by_index.get(parent_index) if parent_index else False
                        line.parent_bom_id = parent.bom_id.id if parent else False
                    line.sequence = index
                    index += 1
                self.job_labour_line_ids = labour
                # OPTIMIZED: Build dict for O(1) parent lookups
                labour_by_index = {}
                for line in self.job_labour_line_ids:
                    if line.labour_index:
                        existing = labour_by_index.get(line.labour_index)
                        if not existing or line.id > existing.id:
                            labour_by_index[line.labour_index] = line
                for line in self.job_labour_line_ids:
                    parent_index = line.labour_index[:-1] if line.labour_index else False
                    parent = labour_by_index.get(parent_index) if parent_index else False
                    line.parent_bom_id = parent.bom_id.id if parent else False

    def action_change_product_supplier(self, products, vendor):
        """OPTIMIZED: Batch fetch vendor prices instead of per-line lookups"""
        for record in self:
            if products and vendor:
                lines = record.job_cost_line_ids.filtered(lambda x: x.product_id.id in products.ids)
                if not lines:
                    continue

                # BATCH QUERY: Fetch all supplier info for these products and vendor
                product_tmpl_ids = lines.mapped('product_id.product_tmpl_id').ids
                all_vendor_prices = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', 'in', product_tmpl_ids),
                    ('partner_id', '=', vendor.id)
                ])
                # Build lookup dictionary: product_tmpl_id -> job_cost_price
                price_by_tmpl = {v.product_tmpl_id.id: v.job_cost_price for v in all_vendor_prices}

                # Apply changes using O(1) lookups
                for line in lines:
                    line.partner_id = vendor.id
                    price = price_by_tmpl.get(line.product_id.product_tmpl_id.id)
                    line.cost_price = price if price else False

    def _compute_hide_approve_reject_button(self):
        """function to decide whether to hide approve & reject buttons"""
        for record in self:
            if record.job_costing_approval_line_ids.filtered(
                    lambda x: x.user_id.id == self._uid and x.state == 'requested'):
                record.hide_approve_reject_button = False
            else:
                record.hide_approve_reject_button = True

    def action_change_supplier(self):
        for record in self:
            product_ids = record.job_cost_line_ids.filtered(
                lambda x: x.job_costing_id.id == record.id and x.selected == True)
            return record.job_cost_line_ids.change_supplier(product_ids)

    def update_approvers(self):
        """function to update approvers"""
        vals = []
        count = 1
        amount = self.currency_id._convert(self.jobcost_total, self.currency_id, self.company_id,
                                           self.start_date or fields.Date.today())
        users = False
        if self.state == 'waiting_first_approval':
            users = self.company_id.automatic_approval_lines.filtered(lambda x: x.is_review == True)
        elif self.state == 'waiting_second_approval':
            users = self.company_id.automatic_approval_lines.filtered(
                lambda x: x.to_limit >= amount and x.condition == 'below' or
                          x.to_limit <= amount and x.condition == 'above' or x.to_limit >= amount >= x.from_amount).mapped(
                'user_ids')
        elif self.state == 'waiting_production_approval':
            user_ids = self.env.ref("odoo_job_costing_management.group_job_costing_production").users.ids
            users = self.env['res.users'].browse(user_ids)
        if users:
            for user in users:
                vals.append((0, 0, {
                    'sequence': count,
                    'user_id': user.id,
                }))
                count += 1
        return {
            'name': _('Update Approvers'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'job.costing.approvers.wizard',
            'target': 'new',
            'context': {'default_job_costing_approver_line_ids': vals, 'default_type': 'update'}
        }

    @api.onchange('customer_currency_id')
    def _onchange_currency_rate(self):
        for record in self:
            if record.customer_currency_id:
                if not record.customer_currency_id.id == self.env.user.company_id.currency_id.id:
                    if record.customer_currency_id.rate_ids:
                        latest_rate = record.customer_currency_id.rate_ids.sorted('name', reverse=True)
                        if latest_rate:
                            record.currency_rate = latest_rate[0].company_rate
                else:
                    record.currency_rate = 0.0
            else:
                record.currency_rate = 0.0

    def action_add_components(self):
        pass

    def action_add_raw_materials(self):

        return {
            'name': _('Add Raw Materials'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'job.cost.line',
            'target': 'new',
            'view_id': self.env.ref('odoo_job_costing_management.job_mrp_bom_form_view').id,
            'context': {'default_is_additional_component': True, 'default_job_cost_id': self.id}
        }

    def action_update_prices(self):
        """OPTIMIZED: Batch fetch all vendor info instead of search per material"""
        for record in self:
            if record.job_cost_line_ids:
                materials = record.job_cost_line_ids.filtered(
                    lambda x: x.material_type == 'component' and x.product_id and x.partner_id
                )
                if materials:
                    # Collect all unique (product_tmpl_id, partner_id) combinations
                    product_tmpl_ids = set()
                    partner_ids = set()
                    for material in materials:
                        product_tmpl_ids.add(material.product_id.product_tmpl_id.id)
                        partner_ids.add(material.partner_id.id)

                    # BATCH QUERY: Fetch all vendor lines in single query
                    all_vendor_lines = self.env['product.supplierinfo'].search([
                        ('product_tmpl_id', 'in', list(product_tmpl_ids)),
                        ('partner_id', 'in', list(partner_ids))
                    ])

                    # Group by (product_tmpl_id, partner_id) for O(1) lookup
                    vendor_by_key = {}
                    for vl in all_vendor_lines:
                        key = (vl.product_tmpl_id.id, vl.partner_id.id)
                        if key not in vendor_by_key:
                            vendor_by_key[key] = vl

                    # OPTIMIZED: Group materials by target price, one write() per group
                    materials_by_price = {}
                    for material in materials:
                        key = (material.product_id.product_tmpl_id.id, material.partner_id.id)
                        vendor_line = vendor_by_key.get(key)
                        if vendor_line:
                            price = vendor_line.job_cost_price or vendor_line.price
                            if price:
                                materials_by_price.setdefault(price, self.env['job.cost.line'])
                                materials_by_price[price] |= material
                    for price, mats in materials_by_price.items():
                        mats.write({'cost_price': price})

    @api.onchange('analytic_id')
    def _onchange_analytic_id(self):
        for record in self:
            if record.analytic_id:
                if record.project_id:
                    record.project_id.analytic_account_id = record.analytic_id.id
                if record.quotation_id:
                    record.quotation_id.analytic_account_id = record.analytic_id.id
                    if record.quotation_id.sale_id:
                        record.quotation_id.sale_id.analytic_account_id = record.analytic_id.id


    @api.depends('job_cost_line_ids.line_type', 'job_labour_line_ids.labour_line_type')
    def _compute_line_type(self):
        for record in self:
            material = record.job_cost_line_ids.filtered(lambda x: x.line_type == 'material')
            component = record.job_cost_line_ids.filtered(lambda x: x.line_type == 'component')
            labour = record.job_labour_line_ids.filtered(lambda x: x.labour_line_type == True)
            if material:
                record.line_type = 'material'
            elif component:
                record.line_type = 'component'
            else:
                record.line_type = False
            if labour:
                record.labour_line_type = True
            else:
                record.labour_line_type = False

    def _compute_parent_bom_domain_ids(self):
        """ Method to get all the parent components related to the job costing sheet and
        BOMs configured as standard BOMs.
        OPTIMIZED: Batch searches instead of per-record queries """
        if not self.ids:
            for record in self:
                record.parent_bom_domain_ids = False
                record.bom_domain_ids = False
            return

        # BATCH 1: Single search for all job cost lines across all records
        all_cost_lines = self.env['job.cost.line'].search([
            ('job_costing_id', 'in', self.ids)
        ])
        # Group bom_ids by job_costing_id
        boms_by_costing = {}
        for cl in all_cost_lines:
            if cl.bom_id:
                boms_by_costing.setdefault(cl.job_costing_id.id, self.env['mrp.bom'])
                boms_by_costing[cl.job_costing_id.id] |= cl.bom_id

        # BATCH 2: Single search for standard BOMs by all boat types
        boat_type_ids = [r.boat_type_id.id for r in self if r.boat_type_id]
        std_boms_by_boat = {}
        if boat_type_ids:
            std_boms = self.env['mrp.bom'].search([
                ('boat_type_ids', 'in', boat_type_ids),
                ('is_this_standard_bom', '=', True),
                ('job_cost_id', '=', False)
            ])
            for bom in std_boms:
                for bt in bom.boat_type_ids:
                    std_boms_by_boat.setdefault(bt.id, self.env['mrp.bom'])
                    std_boms_by_boat[bt.id] |= bom

        for record in self:
            parent_boms = boms_by_costing.get(record.id)
            record.parent_bom_domain_ids = [(6, 0, parent_boms.ids)] if parent_boms else False
            std = std_boms_by_boat.get(record.boat_type_id.id) if record.boat_type_id else None
            record.bom_domain_ids = [(6, 0, std.ids)] if std else False


class JobCostingApprovalLines(models.Model):
    _name = 'job.costing.approval.lines'
    _description = "Job Costing Approval Lines"
    _order = 'sequence'

    job_costing_id = fields.Many2one('job.costing', string="Job Costing")
    sequence = fields.Integer(string="Sequence", default=1)
    user_id = fields.Many2one('res.users', string="Users")
    state = fields.Selection(
        [('pending', 'Pending'), ('requested', 'Requested'), ('reviewed', 'Reviewed'), ('approved', 'Approved'),
         ('rejected', 'Rejected')],
        default='pending')
    approval_request_datetime = fields.Datetime(string="Request Date")
    status_updated_datetime = fields.Datetime(string="Last Status Updated Date")
    type = fields.Selection([('review', 'Review'), ('approval', 'Approval')], string="Type", default=False)
    show_signature = fields.Boolean(string="Show Signature")
    comment = fields.Char(string="Comment")
