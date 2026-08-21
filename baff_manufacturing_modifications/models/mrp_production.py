from odoo import api, fields, models, _
from datetime import date, datetime, time
from odoo.exceptions import ValidationError, AccessError, UserError
from odoo.http import request
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
import datetime


class InheritMrpProduction(models.Model):
    _inherit = 'mrp.production'

    scheduled_start_date = fields.Datetime(string='Scheduled Start Date')
    is_qc_by_supervisor = fields.Boolean(string='QC by Supervisor')
    progress = fields.Float(string='Progress (%)', compute='_compute_progress')
    is_cnc_complete = fields.Boolean(string='Dependencies', compute='_compute_is_cnc_complete')
    planned_start_date = fields.Datetime(
        'Planned Start Date', compute='_compute_date_planned_start')
    approval_state = fields.Selection(
        [('required_approval', 'Required Approval'), ('waiting_approve', 'Waiting Approve'), ('approve', 'Approve'), ('reject', 'Reject')])
    current_state = fields.Boolean(string="Current State", default=False)
    approval_required = fields.Boolean(string="Approval Required", default=False)

    #   Approval fields
    is_have_user_access = fields.Boolean(default=False, compute="compute_is_have_user_access", copy=False)
    approval_requested_date = fields.Datetime(string="Requested Date", tracking=True, copy=False)
    approval_requested_by = fields.Many2one('res.users', string="Requested By", copy=False)
    approval_requested_users = fields.Many2many('res.users', 'mrp_users_rel', 'production_id', 'users_id',
                                                string="Approval Requested users", tracking=True, copy=False)
    approved_by = fields.Many2many('res.users', 'mrp_approved_users_rel', 'production_id', 'users_id',
                                   string="Approved By", copy=False)
    approved_date = fields.Datetime(string="Last Approved Date", copy=False)
    approved_note = fields.Text('Approved Note', copy=False)

    rejected_by = fields.Many2many('res.users', 'mrp_rejected_users_rel', 'production_id', 'users_id',
                                   string="Rejected By", copy=False)
    rejected_date = fields.Datetime(string="Last Rejected Date", copy=False)
    rejected_note = fields.Char('Rejected Note', copy=False)

    quantity_check = fields.Selection(selection=[('pass', 'Pass'), ('fail', 'Fail')], string="Quality Check")
    mo_completion = fields.Selection(selection=[('complete', 'Complete'), ('partial', 'Partial'), ('fail', 'Fail')])

    # Material Purchase Requisition fields
    material_requisition_ids = fields.One2many('material.purchase.requisition', 'mrp_id', string='Material Requisitions')
    material_requisition_count = fields.Integer(string='Material Requisition Count', compute='_compute_material_requisition_count')
    has_new_components_without_requisition = fields.Boolean(
        string='Has New Components Without Requisition',
        compute='_compute_has_new_components_without_requisition',
        help='Indicates if there are new components added without a material requisition'
    )

    # Job Costing related fields
    job_costing_number = fields.Char(related='job_cost_id.number', string='Job Costing Sheet No.', store=True, readonly=True)
    project_id = fields.Many2one(related='job_cost_id.project_id', string='Project', store=True, readonly=True)
    finished_good_location_id = fields.Many2one(related='job_cost_id.finished_good_location_id', string='Finished Good Location',
                                                 store=True, readonly=True)

    @api.depends('material_requisition_ids')
    def _compute_material_requisition_count(self):
        """Compute the count of material requisitions related to this MO"""
        for record in self:
            record.material_requisition_count = len(record.material_requisition_ids)

    @api.depends('move_raw_ids.is_new_component', 'material_requisition_ids')
    def _compute_has_new_components_without_requisition(self):
        """Check if there are new components without material requisition"""
        for record in self:
            # Get new components (those with is_new_component = True)
            new_components = record.move_raw_ids.filtered(
                lambda x: x.is_new_component and x.bom_line_id.id == False and x.state != 'cancel'
            )

            if new_components:
                # Collect all stock move IDs already linked in ANY requisition for this MO
                linked_move_ids = record.material_requisition_ids.mapped('requisition_line_ids.move_id').ids
                # Check if any new component stock move is not yet linked to a requisition line
                missing_components = new_components.filtered(lambda c: c.id not in linked_move_ids)
                record.has_new_components_without_requisition = bool(missing_components)
            else:
                record.has_new_components_without_requisition = False

    def action_view_material_requisitions(self):
        """Smart button action to view related material requisitions"""
        self.ensure_one()
        return {
            'name': _('Material Requisitions'),
            'type': 'ir.actions.act_window',
            'res_model': 'material.purchase.requisition',
            'view_mode': 'tree,form',
            'domain': [('mrp_id', '=', self.id)],
            'context': {'default_mrp_id': self.id},
        }

    def create_material_requisition_for_components(self, components=False):
        """Create or update material purchase requisition for new components"""
        if not components:
            pass

        # Check if there's already a draft requisition for this MO
        existing_requisition = self.env['material.purchase.requisition'].search([
            ('mrp_id', '=', self.id),
            ('state', '=', 'draft')
        ], limit=1)

        if existing_requisition:
            # Use existing draft requisition
            requisition = existing_requisition
            # Update the reason to indicate new components were added
            if 'New components added' not in (requisition.reason or ''):
                requisition.reason = (requisition.reason or '') + '\nAdditional components added on ' + fields.Date.today().strftime('%Y-%m-%d')
        else:
            # Get the employee from the current user
            employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            if not employee:
                # If no employee found for current user, get the first employee
                employee = self.env['hr.employee'].search([], limit=1)

            # Create a new material purchase requisition
            requisition_vals = {
                'employee_id': employee.id,
                'department_id': employee.department_id.id if employee.department_id else False,
                'request_date': fields.Date.today(),
                'reason': f'Auto-generated requisition for MO {self.name} - New components added',
                'mrp_id': self.id,
                'company_id': self.company_id.id,
                'mp_project_id': self.project_id.id if self.project_id else False,
                'analytic_account_id': self.job_cost_id.analytic_id.id if self.job_cost_id and self.job_cost_id.analytic_id else False,
            }
            requisition = self.env['material.purchase.requisition'].create(requisition_vals)

        # Create requisition lines for each component (avoid duplicates by stock move)
        for component in components:
            # Check if this specific stock move already has a requisition line
            existing_line = self.env['material.purchase.requisition.line'].search([
                ('requisition_id', '=', requisition.id),
                ('move_id', '=', component.id)
            ], limit=1)

            if existing_line:
                # Skip if this specific stock move already has a requisition line
                continue

            # Create new requisition line for this component
            component_qty = component.quantity_done if component.quantity_done else component.product_uom_qty  # Use the required quantity to consume
            line_vals = {
                'requisition_id': requisition.id,
                'product_id': component.product_id.id,
                'description': component.product_id.name,
                'qty': component_qty,
                'required_quantity': component_qty,  # Map to required quantity
                'uom': component.product_uom.id,
                'requisition_type': 'purchase',  # Default to purchase, can be changed by user
                'move_id': component.id,  # Link to the specific stock move
            }
            self.env['material.purchase.requisition.line'].create(line_vals)

        return requisition

    @api.model
    def production_alerts_during_production_process(self):
        """Send Production Alerts for MOs where budget cost or expected duration is exceeded."""
        in_progress_mos = self.env['mrp.production'].search([('state', '=', 'progress')])
        if not in_progress_mos:
            return

        def _fmt_duration(minutes):
            """Format minutes as Xh Ym."""
            h, m = divmod(int(minutes), 60)
            return f"{h}h {m}m"

        def _fmt_cost(amount):
            """Format amount to 2 decimal places."""
            return f"{amount:,.2f}"

        # Group exceeded MOs per salesperson email
        # Each entry: {email: {'cost_rows': [...], 'duration_rows': [...]}}
        alerts_by_salesperson = {}

        for mo in in_progress_mos:
            if not mo.job_cost_id or not mo.job_cost_id.sale_id.user_id.email:
                continue
            email = mo.job_cost_id.sale_id.user_id.email
            if email not in alerts_by_salesperson:
                alerts_by_salesperson[email] = {
                    'name': mo.job_cost_id.sale_id.user_id.name,
                    'cost_rows': [],
                    'duration_rows': [],
                }

            # Check cost exceeded
            if mo.job_cost_id.total_actual_cost > mo.job_cost_id.total_budget_cost:
                alerts_by_salesperson[email]['cost_rows'].append({
                    'mo_name': mo.name,
                    'product': mo.product_id.name,
                    'project': mo.project_id.name if mo.project_id else 'N/A',
                    'job_costing_number': mo.job_costing_number or 'N/A',
                    'analytic_account': mo.job_cost_id.analytic_id.name if mo.job_cost_id.analytic_id else 'N/A',
                    'bom': mo.bom_id.display_name if mo.bom_id else 'N/A',
                    'budget_cost': _fmt_cost(mo.job_cost_id.total_budget_cost),
                    'actual_cost': _fmt_cost(mo.job_cost_id.total_actual_cost),
                })

            # Check duration exceeded (not elif — check both independently)
            if mo.production_duration_expected and mo.production_real_duration > mo.production_duration_expected:
                alerts_by_salesperson[email]['duration_rows'].append({
                    'mo_name': mo.name,
                    'product': mo.product_id.name,
                    'project': mo.project_id.name if mo.project_id else 'N/A',
                    'job_costing_number': mo.job_costing_number or 'N/A',
                    'analytic_account': mo.job_cost_id.analytic_id.name if mo.job_cost_id.analytic_id else 'N/A',
                    'bom': mo.bom_id.display_name if mo.bom_id else 'N/A',
                    'expected_duration': _fmt_duration(mo.production_duration_expected),
                    'actual_duration': _fmt_duration(mo.production_real_duration),
                })

        if not alerts_by_salesperson:
            return

        template = self.env.ref(
            'baff_manufacturing_modifications.fine_finish_production_alerts_during_production_access_new')

        for email, alert_data in alerts_by_salesperson.items():
            if not alert_data['cost_rows'] and not alert_data['duration_rows']:
                continue

            context = {
                'subject': "Production Alert: Budget Cost / Duration Exceeded",
                'heading': "Production Alert",
                'mail_body': "The following manufacturing orders have exceeded their budget cost and/or expected duration:",
                'email_from': self.env.user.email,
                'email_to': email,
                'data': alert_data,
            }

            template.with_context(context).send_mail(
                in_progress_mos[0].id, force_send=True)

            # Chatter notification to the salesperson
            user = self.env['res.users'].sudo().search([('email', '=', email)], limit=1)
            if user:
                body_parts = ["The following manufacturing orders have exceeded their limits:"]
                if alert_data['cost_rows']:
                    body_parts.append("\nCost Exceeded:")
                    for row in alert_data['cost_rows']:
                        body_parts.append(
                            f"- {row['mo_name']} ({row['product']}): "
                            f"Budget {row['budget_cost']} / Actual {row['actual_cost']}")
                if alert_data['duration_rows']:
                    body_parts.append("\nDuration Exceeded:")
                    for row in alert_data['duration_rows']:
                        body_parts.append(
                            f"- {row['mo_name']} ({row['product']}): "
                            f"Expected {row['expected_duration']} / Actual {row['actual_duration']}")
                user.partner_id.sudo().message_post(
                    body="\n".join(body_parts),
                    subject="Production Alert: Budget Cost / Duration Exceeded",
                    subtype_id=self.env.ref('mail.mt_comment').id,
                    message_type='notification',
                )

    @api.depends('production_real_duration', 'production_duration_expected')
    def _compute_progress(self):
        # calculating progress percentage of real duration and expected duration
        for production in self:
            if production.production_duration_expected > 0:
                production.progress = (production.production_real_duration / production.production_duration_expected) * 100
            else:
                production.progress = 0

    def _compute_is_cnc_complete(self):
        """ Checking availability of the components which depend on another cost center and
        setting the CNC completed field Tru or False accordingly """
        for record in self:
            if record.state not in ('done', 'cancel'):
                lines = record.move_raw_ids.filtered(lambda x: x.bom_line_id.jobcost_line_id.cost_center_dependency == True and x.forecast_availability == x.product_qty)
                if lines.filtered(lambda x: x.forecast_availability == 0):
                    record.is_cnc_complete = False
                else:
                    record.is_cnc_complete = True
            else:
                record.is_cnc_complete = True

    def button_mark_done(self):
        """check whether qc by supervisor has checked when mark as done"""
        if not self.is_qc_by_supervisor:
            raise ValidationError('Please ensure that the QC by Supervisor checkbox is checked before marking '
                                  'this production order as done.')
        else:
            # Setting MO Completion level and call the super method to execute any existing functionality
            # of button_mark_done
            if self.quantity_check == 'fail':
                self.mo_completion = 'fail'
            elif self.quantity_check == 'pass' and self.qty_producing == self.product_qty:
                self.mo_completion = 'complete'
            elif self.quantity_check == 'pass' and self.qty_producing < self.product_qty:
                self.mo_completion = 'partial'
            res = super(InheritMrpProduction, self).button_mark_done()
        return res

    @api.onchange('is_qc_by_supervisor')
    def qc_by_supervisor(self):
        """allow to check qc by supervisor for the initiated user group"""
        if not self.env.user.has_group('baff_manufacturing_modifications.'
                                       'group_manufacturing_modification_allow_check_qc_by_supervisor'):
            raise AccessError(_("You do not have permission check."))

    def _compute_date_planned_start(self):
        """Method to assign project start date form sale order to scheduled date in mo and work orders"""
        for record in self:
            sales_orders = self.env['sale.order'].search([]).filtered(
                lambda x: record.id in x.mrp_production_ids.ids)
            start_date = sales_orders[:1].project_start_date if sales_orders else False
            if start_date:
                if record.state == 'draft':
                    record.planned_start_date = start_date
                    record.date_planned_start = start_date
                    if record.workorder_ids:
                        for line in record.workorder_ids:
                            line.date_planned_start = start_date
                    else:
                        record.planned_start_date = start_date
                else:
                    record.planned_start_date = start_date
            else:
                record.planned_start_date = False

    def add_new_component_operation(self):
        """ Method to check for new components and operations added to manufacturing order
        during production and trigger approval process if needed. Only processes items
        marked with is_new_component or is_new_operation flags to exclude old unmapped items. """
        for record in self:
            if record.state == 'progress' and record.approval_state == False:
                values = record.calculate_cost_buffer()
                new_components = values[2]
                new_operations = values[3]
                if new_components or new_operations:
                    record.new_components_approval(values)

    def calculate_cost_buffer(self):
        """ Method to calculate newly added components and operations cost,
        getting the budget cost of the job cost sheet and calculating cost buffer.
        Returning cost buffer, new components, new operations, total cost and job costing sheet values. """
        new_components = self.move_raw_ids.filtered(lambda x: x.bom_line_id.id == False and x.state != 'cancel' and x.is_new_component == True)
        new_operations = self.workorder_ids.filtered(lambda x: x.operation_id.id == False and x.is_new_operation == True)

        cost_of_new_components = 0.0
        cost_of_new_operations = 0.0

        if new_components:
            for new_component in new_components:
                cost_of_new_components += (new_component.product_id.standard_price * (new_component.quantity_done if new_component.quantity_done else new_component.product_uom_qty))
        if new_operations:
            for new_operation in new_operations:
                cost_of_new_operations += (new_operation.workcenter_id.costs_hour * new_operation.qty_remaining)

        job_costing_sheet = self.job_cost_id
        total_costs = cost_of_new_components + cost_of_new_operations
        cost_buffer = job_costing_sheet.jobcost_total + job_costing_sheet.jobcost_total * 0.05

        return cost_buffer, total_costs, new_components, new_operations, job_costing_sheet

    def new_components_approval(self, values):
        """ Checking whether the new components or operations need to be approved and
        sending for approval if yes. """
        cost_buffer = values[0]
        total_costs = values[1]
        job_costing_sheet = values[4]
        if cost_buffer < (total_costs + job_costing_sheet.jobcost_total):
            sale_order = self.env['sale.order'].search([]).filtered(lambda x: self.id in x.mrp_production_ids.ids)
            if sale_order.quotation_required == 'yes':
                if not self.approval_required and not self.approval_state == 'approve':
                    self.approval_required = True
                    self.approval_state = 'required_approval'
            else:
                self.update_bom_costsheet()
        else:
            self.update_bom_costsheet()

    def compute_is_have_user_access(self):
        """Get access level for stock picking"""
        for rec in self:
            if self.env.user.id in rec.approval_requested_users.ids and rec.approval_state == 'waiting_approve' and \
                    self.env.user.id not in rec.approved_by.ids:
                rec.is_have_user_access = True
            else:
                rec.is_have_user_access = False

    def action_sent_for_approval(self):
        """Method to pop up the user approval wizard and
        to set the mail body when clicking send for approval button"""
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': 'Request For New Component Approve %s' % self.name,
            'msg_type': 'Please approve this %s' % self.name,
        }
        return {
            'name': _('Request approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'request.user.approve.wizard',
            'target': 'new',
            'context': {
                'default_model_id': model.id,
                'mail_body': mail_body,
                'approve_group': self.env.ref(
                    'baff_manufacturing_modifications.group_component_request_approve').id,
            }
        }

    def action_requested_approval(self, approval_requested_by, approval_requested_date, approval_requested_users):
        """Function for after request the approval to set the state to waiting approve and
        to set approval requested by, date and users values accordingly"""

        self.write({
            'approval_requested_by': approval_requested_by,
            'approval_requested_date': approval_requested_date,
            'approval_requested_users': approval_requested_users,
            'approval_state': 'waiting_approve'
        })

    def action_user_approve(self):
        """Approve button action to set the mail body and popup approve wizard"""
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': 'Request has been Approved - %s' % self.name,
            'msg_type': 'Requested %s has been approved' % self.name,
        }
        return {
            'name': _('Approve'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'request.approve.reject.wizard',
            'target': 'new',
            'context': {
                'default_model_id': model.id,
                'mail_body': mail_body,
                'default_action_type': 'approve',
                'default_requested_user': self.approval_requested_by.id,
            }
        }

    def action_approve_the_request(self, approved_by, approved_date, approved_note):
        """Function for after the approval to set the state to approved,
        to set approved by, date, note and to create log note"""
        approval_method = self.env['ir.config_parameter'].sudo().get_param(
            'centrics_user_approve.multiple_approval_method') or False

        self.write({
            'approved_by': [(4, approved_by.id)],
            'approved_date': approved_date,
            'approved_note': self.approved_note + ", " if self.approved_note else '' + approved_note if approved_note else '',
        })
        message = _('Approved By - %s <br/> Approved Date - %s  ' % (approved_by.name, str(approved_date)))
        self.sudo().message_post(body=message, message_type='comment')

        context = {
            'approved_by': [(4, approved_by.id)],
            'approved_date': approved_date,
            'approved_note': self.approved_note + ", " if self.approved_note else '' + approved_note if approved_note else '',
            'message': 'Approved By - %s <br/> Approved Date - %s  ' % (approved_by.name, str(approved_date))
        }
        if approval_method:

            if approval_method == "all":
                if self.approval_requested_users == self.approved_by:
                    self.update_bom_costsheet()
                    self.approval_state = 'approve'
                    self.approval_required = False
                    self.approval_state = False
                else:
                    self.approval_state = 'waiting_approve'
                    self.approval_required = True
                    # validated = True
            else:
                self.update_bom_costsheet()
                self.approval_state = 'approve'
                self.approval_required = False
                self.approval_state = False
        else:
            self.update_bom_costsheet()
            self.approval_state = 'approve'
            self.approval_required = False
            self.approval_state = False

        return True

    def action_user_reject(self):
        """Reject button action to set the mail body and popup Reject wizard"""
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': 'Request has been Rejected  - %s' % self.name,
            'msg_type': 'Requested %s has been rejected' % self.name,
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
                'default_requested_user': self.approval_requested_by.id,
            }
        }

    def action_reject_the_request(self, rejected_by, rejected_date, rejected_note):
        """Function for after the rejected to set the state to rejected,
        to set rejected by, date, note and to create log note"""
        self.write({
            'rejected_by': [(4, rejected_by.id)],
            'rejected_date': rejected_date,
            'rejected_note': self.rejected_note if self.rejected_note else '' + rejected_note if rejected_note else '',
            'approval_state': 'reject'
        })
        values = self.calculate_cost_buffer()
        new_components = values[2]
        new_operations = values[3]
        if new_components:
            for component in new_components:
                component._action_cancel()
                # component.unlink()
        if new_operations:
            for operation in new_operations:
                operation.unlink()
        message = _(
            'Reject By - %s <br/> Reject Date - %s  ' % (rejected_by.name, str(rejected_date)))
        self.approval_required = False
        self.sudo().message_post(body=message, message_type='comment')

    def update_bom_costsheet(self):
        """ Updating job costing sheet and the BOM with the new components or operations and
        sending an email to the relevant person. Creating planning slot for the new operation"""
        values = self.calculate_cost_buffer()
        new_components = values[2]
        new_operations = values[3]
        job_cost_sheet = values[4]

        # Updating new components in job costing sheet and bom
        if new_components:
            if job_cost_sheet.job_cost_line_ids:
                for component in new_components:
                    job_cost_line = job_cost_sheet.job_cost_line_ids.create({
                        'job_costing_id': job_cost_sheet.id,
                        'product_id': component.product_id.id,
                        'description': component.product_id.name,
                        'product_qty': component.quantity_done if component.quantity_done else component.product_uom_qty,
                        'uom_id': component.product_uom.id,
                        'cost_price': component.product_id.standard_price,
                        'remaining_qty': component.quantity_done if component.quantity_done else component.product_uom_qty,
                        'is_new_item': True,
                        'job_type': 'material'
                    })
                    bom_line = self.bom_id.bom_line_ids.create({
                        'product_id': component.product_id.id,
                        'jobcost_line_id': job_cost_line.id,
                        'bom_id': self.bom_id.id,
                        'product_qty': component.quantity_done if component.quantity_done else component.product_uom_qty
                    })
                    if bom_line:
                        component.bom_line_id = bom_line.id
                        component.is_new_component = False  # Reset flag after mapping

            # Create material purchase requisition for new components
            self.create_material_requisition_for_components(new_components)
        # Updating new operations in job costing sheet and bom
        if new_operations:
            if job_cost_sheet.job_cost_line_ids:
                for operation in new_operations:
                    job_type = self.env['job.type'].search([]).filtered(lambda x: x.name == operation.name)

                    if job_type:
                        job_cost_labor_line = job_cost_sheet.job_cost_line_ids.create({
                            'job_costing_id': job_cost_sheet.id,
                            'job_type_id': job_type.id,
                            'work_center_id': operation.workcenter_id.id,
                            'description': job_type.name,
                            'qty': 1.0,
                            'hour': operation.expected_duration_hrs,
                            'cost_price': operation.workcenter_id.costs_hour,
                            'actual_hour': operation.duration,
                            'job_type': 'labour'
                        })
                        bom_line = self.bom_id.operation_ids.create({
                            'name': operation.name,
                            'workcenter_id': operation.workcenter_id.id,
                            'time_mode': 'manual',
                            'time_cycle': operation.duration_expected,
                            'jobcost_line_id': job_cost_labor_line.id,
                            'bom_id': self.bom_id.id
                        })

                        if bom_line:
                            operation.operation_id = bom_line.id
                            operation.is_new_operation = False  # Reset flag after mapping
                    else:
                        raise UserError(_("There is no job type in the name of %s.", operation.name))
                    # Creating planning slot for the new operation
                    sales_order = job_cost_sheet.sale_id
                    if sales_order and operation.date_planned_start and job_cost_labor_line:
                        self.env['sale.order'].employee_planning(sales_order, operation.date_planned_start.date(), job_cost_labor_line)
        # Sending email for new components and operations
        if new_operations or new_components:
            self._send_new_component_email(new_components, new_operations)

    @api.model
    def send_estimation_exceed_email(self):
        """Sending an email if the estimated components quantity or operation times is exceeded."""
        active_mos = self.env['mrp.production'].search([
            ('state', 'in', ('confirmed', 'progress', 'to_close')),
        ])
        if not active_mos:
            return

        template = self.env.ref(
            'baff_manufacturing_modifications.estimation_exceed_email_notification')

        for mo in active_mos:
            rep = mo.job_cost_id.sale_id.user_id
            if not rep.email:
                continue

            # Check cost exceeded (actual > budget)
            if (mo.job_cost_id
                    and mo.job_cost_id.total_actual_cost > mo.job_cost_id.total_budget_cost):
                context = {
                    'subject': f"Budget Exceeded: {mo.name}",
                    'heading': "Budget Cost Exceeded",
                    'receiver': rep.name,
                    'exceed_type': 'cost',
                    'mo_name': mo.name,
                    'mo_product': mo.product_id.name,
                    'project': mo.project_id.name if mo.project_id else 'N/A',
                    'job_costing_number': mo.job_costing_number or 'N/A',
                    'analytic_account': mo.job_cost_id.analytic_id.name if mo.job_cost_id and mo.job_cost_id.analytic_id else 'N/A',
                    'bom': mo.bom_id.display_name if mo.bom_id else 'N/A',
                    'budget_cost': f"{mo.job_cost_id.total_budget_cost:,.2f}",
                    'actual_cost': f"{mo.job_cost_id.total_actual_cost:,.2f}",
                    'exceeded_by': f"{mo.job_cost_id.total_actual_cost - mo.job_cost_id.total_budget_cost:,.2f}",
                    'email_from': self.env.user.email,
                    'email_to': rep.email,
                }
                template.with_context(context).send_mail(mo.id, force_send=True)

            # Check duration exceeded
            if (mo.production_duration_expected
                    and mo.production_real_duration > mo.production_duration_expected):
                expected_h, expected_m = divmod(int(mo.production_duration_expected), 60)
                actual_h, actual_m = divmod(int(mo.production_real_duration), 60)
                context = {
                    'subject': f"Duration Exceeded: {mo.name}",
                    'heading': "Expected Duration Exceeded",
                    'receiver': rep.name,
                    'exceed_type': 'duration',
                    'mo_name': mo.name,
                    'mo_product': mo.product_id.name,
                    'project': mo.project_id.name if mo.project_id else 'N/A',
                    'job_costing_number': mo.job_costing_number or 'N/A',
                    'analytic_account': mo.job_cost_id.analytic_id.name if mo.job_cost_id and mo.job_cost_id.analytic_id else 'N/A',
                    'bom': mo.bom_id.display_name if mo.bom_id else 'N/A',
                    'expected_duration': f"{expected_h}h {expected_m}m",
                    'actual_duration': f"{actual_h}h {actual_m}m",
                    'email_from': self.env.user.email,
                    'email_to': rep.email,
                }
                template.with_context(context).send_mail(mo.id, force_send=True)

    def _send_new_component_email(self, components, operations):
        """Sending an email regarding new components or operations."""
        rep = self.job_cost_id.sale_id.user_id
        if not rep or not rep.email:
            return

        component_details_list = []
        component_total = 0.0
        for idx, component in enumerate(components, 1):
            qty = component.quantity_done or component.product_uom_qty
            line_total = qty * component.product_id.standard_price
            component_total += line_total
            component_details_list.append({
                'serial': idx,
                'product_id': component.product_id.name,
                'quantity': f"{qty:,.2f}",
                'uom': component.product_uom.name,
                'cost_price': f"{component.product_id.standard_price:,.2f}",
                'total': f"{line_total:,.2f}",
            })

        operation_details_list = []
        operation_total = 0.0
        for idx, operation in enumerate(operations, 1):
            duration = operation.duration_expected or operation.duration
            hours = duration / 60
            line_total = hours * operation.workcenter_id.costs_hour
            operation_total += line_total
            h, m = divmod(int(duration), 60)
            operation_details_list.append({
                'serial': idx,
                'operation_name': operation.name,
                'work_center': operation.workcenter_id.name,
                'duration': f"{h}h {m}m",
                'cost_price': f"{operation.workcenter_id.costs_hour:,.2f}",
                'total': f"{line_total:,.2f}",
            })

        context = {
            'subject': f"New Components / Operations Added: {self.name}",
            'heading': "New Components / Operations Added",
            'receiver': rep.name,
            'email_from': self.env.user.email,
            'email_to': rep.email,
            'mo_name': self.name,
            'mo_product': self.product_id.name,
            'project': self.project_id.name if self.project_id else 'N/A',
            'job_costing_number': self.job_costing_number or 'N/A',
            'analytic_account': self.job_cost_id.analytic_id.name if self.job_cost_id and self.job_cost_id.analytic_id else 'N/A',
            'bom': self.bom_id.display_name if self.bom_id else 'N/A',
            'component_details': component_details_list,
            'component_total': f"{component_total:,.2f}",
            'operation_details': operation_details_list,
            'operation_total': f"{operation_total:,.2f}",
        }
        template = self.env.ref(
            'baff_manufacturing_modifications.new_components_email_notification')
        template.with_context(context).send_mail(self.id, force_send=True)

    def map_so_analytic_to_manufacturing_orders(self):
        """Map the analytic account from the related Sales Order to this MO
        and all its child MOs and backorders.

        Called from the MO form view or as a server action on selected MOs.
        """
        MrpProduction = self.env['mrp.production']

        for record in self:
            # Find the related Sale Order
            so = record.sale_order_id or False

            # Fallback: search via procurement group
            if not so and record.procurement_group_id:
                so = record.procurement_group_id.sale_id

            # Fallback: search by origin field
            if not so and record.origin:
                so = self.env['sale.order'].search([
                    ('name', '=', record.origin),
                ], limit=1)

            if not so or not so.analytic_account_id:
                continue

            analytic = so.analytic_account_id

            # Start with this MO
            all_mos = record

            # Find sibling MOs from the same procurement group
            if record.procurement_group_id:
                all_mos |= record.procurement_group_id.mrp_production_ids
                # Also via stock move chain
                all_mos |= (
                    record.procurement_group_id.stock_move_ids
                    .created_production_id
                    .procurement_group_id
                    .mrp_production_ids
                )

            # Find MOs linked via the same job costing sheet
            if record.job_cost_id:
                all_mos |= MrpProduction.search([
                    ('job_cost_id', '=', record.job_cost_id.id),
                ])

            # Expand to include all child MOs recursively
            all_mos = self._get_all_child_mos(all_mos)

            # Include backorders (same procurement group)
            pg_ids = all_mos.mapped('procurement_group_id').ids
            if pg_ids:
                all_mos |= MrpProduction.search([
                    ('procurement_group_id', 'in', pg_ids),
                ])

            # Update only MOs that don't already have the correct analytic account
            mos_to_update = all_mos.filtered(
                lambda mo: mo.analytic_account_id != analytic
            )
            if mos_to_update:
                mos_to_update.write({'analytic_account_id': analytic.id})

    def _get_all_child_mos(self, mos):
        """Recursively find all child MOs from the given set of MOs."""
        all_mos = mos
        current = mos
        seen_ids = set(mos.ids)

        while current:
            # Children via finished product moves → destination moves → created production
            children = (
                current.mapped('move_finished_ids')
                .mapped('move_dest_ids')
                .mapped('created_production_id')
            )
            # Children via raw material origin chain
            children |= (
                current.mapped('move_raw_ids')
                .mapped('move_orig_ids')
                .mapped('production_id')
            )
            new_children = children.filtered(lambda mo: mo.id not in seen_ids)
            if not new_children:
                break
            seen_ids.update(new_children.ids)
            all_mos |= new_children
            current = new_children

        return all_mos