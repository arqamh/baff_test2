from odoo import api, fields, models, _
from odoo.addons.web.controllers.utils import clean_action
from datetime import datetime, timedelta
from odoo.exceptions import AccessError, UserError
import math


class InheritMrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    real_duration_hrs = fields.Float(string="Real Duration ", compute='_compute_real_duration_hrs')
    expected_duration_hrs = fields.Float(string="Expected Duration ", compute='_compute_expected_duration_hrs',
                                         inverse='_compute_expected_duration_mins', store=True)
    is_new_operation = fields.Boolean(
        string='Is New Operation',
        default=False,
        help='Flag to identify new operations added during production that require approval'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """ Override create to automatically mark new operations added to MO during production """
        workorders = super(InheritMrpWorkorder, self).create(vals_list)
        for workorder in workorders:
            # Check if this is an operation being added to an MO that's already in production
            if workorder.production_id and not workorder.operation_id:
                # If the MO is already confirmed or in progress, this is a new operation
                if workorder.production_id.state in ('confirmed', 'progress', 'to_close'):
                    workorder.is_new_operation = True
        return workorders

    def _change_duration(self):
        """Rounding duration in work order"""
        for record in self:
            if record.duration:
                time = round(record.duration)
                time = time / 30
                if time == 0.5:
                    time += 0.1
                rounded_time = round(time)
                record.duration = rounded_time * 30
                record.real_duration_hrs = record.duration / 60
            else:
                record.duration = 0.0

    @api.onchange('real_duration_hrs')
    def _onchange_real_duration_hrs(self):
        """Rounding duration in work order"""
        for record in self:
            if record.real_duration_hrs:
                time_minutes = record.real_duration_hrs * 60
                time = round(time_minutes)
                time = time / 30
                if time == 0.5:
                    time += 0.1
                rounded_time = round(time)
                record.duration = rounded_time * 30
                record.real_duration_hrs = (rounded_time * 30) / 60
            else:
                record.duration = 0.0

    @api.depends('time_ids.duration')
    def _compute_real_duration_hrs(self):
        """Calculating real duration in work order"""
        for record in self:
            duration = 0.0
            if record.time_ids:
                for time in record.time_ids:
                    duration += time.duration
            record.real_duration_hrs = duration / 60 if duration else duration
            record.duration = duration

    @api.depends('duration_expected')
    def _compute_expected_duration_hrs(self):
        """Calculating expected duration in work order"""
        for record in self:
            if record.duration_expected:
                record.expected_duration_hrs = record.duration_expected / 60
            else:
                record.expected_duration_hrs = 0.0

    def _compute_expected_duration_mins(self):
        """Setting expected duration in minutes"""
        for record in self:
            if record.expected_duration_hrs:
                record.duration_expected = record.expected_duration_hrs * 60
            else:
                record.duration_expected = 0.0

    def button_pending(self):
        """Overriding core method to add time rounding method"""
        self._change_duration()
        self.end_previous()
        return True

    def button_finish(self):
        """Overriding core method to add time rounding method"""
        end_date = datetime.now()
        self._change_duration()
        for workorder in self:
            if workorder.state in ('done', 'cancel'):
                continue
            workorder.end_all()
            vals = {
                'qty_produced': workorder.qty_produced or workorder.qty_producing or workorder.qty_production,
                'state': 'done',
                'date_finished': end_date,
                'date_planned_finished': end_date,
                'costs_hour': workorder.workcenter_id.costs_hour
            }
            if not workorder.date_start:
                vals['date_start'] = end_date
            if not workorder.date_planned_start or end_date < workorder.date_planned_start:
                vals['date_planned_start'] = end_date
            workorder.with_context(bypass_duration_calculation=True).write(vals)
        return True

    def write(self, vals):
        # Check if the manufacturing order is in the done state and in the specific user group
        if vals.get('duration'):
            if self.production_id.state == 'done':
                # Check if the user belongs to the group
                if not self.env.user.has_group('baff_manufacturing_modifications.'
                                               'group_manufacturing_modification_allow_edit_real_time_access'):
                    raise AccessError(_("You do not have permission to edit the duration."))

        if vals.get('time_ids'):
            new_employees = []
            old_employee = self.operation_id.jobcost_line_id.employee_id
            for line in vals.get('time_ids'):
                values = line[2]
                if values:
                    new_employee = values.get('employee_id')
                    if new_employee:
                        if old_employee.id != new_employee:
                            if new_employee not in new_employees:
                                new_employees.append(new_employee)
            if new_employees:
                self._send_new_worker_email(old_employee, new_employees)

        # Call the parent write method to update the record
        result = super(InheritMrpWorkorder, self).write(vals)

        return result

    def _send_new_worker_email(self, old_emp, new_emp):
        """Sending an email regarding worker changes in an operation."""
        rep = self.operation_id.jobcost_line_id.job_costing_id.sale_id.user_id
        if not rep or not rep.email:
            return

        worker_details_list = []
        # Browse all new employee IDs in a single call instead of search([]).filtered() per ID
        employees = self.env['hr.employee'].browse(new_emp).exists()
        for idx, employee in enumerate(employees, 1):
            worker_details_list.append({
                'serial': idx,
                'old_employee': old_emp.name,
                'old_employee_rate': f"{old_emp.hourly_cost:,.2f}",
                'new_employee': employee.name,
                'new_employee_rate': f"{employee.hourly_cost:,.2f}",
            })

        if not worker_details_list:
            return

        mo = self.production_id
        context = {
            'subject': f"Worker Changed: {mo.name} - {self.name}",
            'heading': "Worker Changed",
            'receiver': rep.name,
            'operation_name': self.name,
            'work_center': self.workcenter_id.name,
            'mo_name': mo.name,
            'mo_product': mo.product_id.name,
            'project': mo.project_id.name if mo.project_id else 'N/A',
            'job_costing_number': mo.job_costing_number or 'N/A',
            'analytic_account': mo.job_cost_id.analytic_id.name if mo.job_cost_id and mo.job_cost_id.analytic_id else 'N/A',
            'bom': mo.bom_id.display_name if mo.bom_id else 'N/A',
            'email_from': self.env.user.email,
            'email_to': rep.email,
            'employee_details': worker_details_list,
        }
        template = self.env.ref(
            'baff_manufacturing_modifications.worker_change_email_notification')
        template.with_context(context).send_mail(self.id, force_send=True)

    def action_back(self):
        """
        @Override
        Before - Initially this return work order tablet view
        After  -  #5149- based on the ticket request this will return MO view
        """
        action = super().action_back()
        if self.env.context.get('from_manufacturing_order'):
            # from workorder on MO
            action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_production_action")
            action['view_mode'] = 'form'
            action['res_id'] = self.production_id.id
            if 'views' in action:
                action['views'] = [
                                      (view_id, view_type)
                                      for view_id, view_type in action['views']
                                      if view_type == 'form'
                                  ] or [False, 'form']
        return clean_action(action, self.env)

    def start_employee(self, employee_id):
        """Pre-check overlap before the standard start flow so the tablet shows
        a clear error instead of a generic create-failure trace."""
        if self.allow_employee and employee_id:
            self.env['mrp.workcenter.productivity']._check_employee_workcenter_conflict(
                employee_id, self.workcenter_id)
        return super().start_employee(employee_id)


class MrpWorkcenterProductivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    @api.model
    def _check_employee_workcenter_conflict(self, employee_id, workcenter):
        """Raise UserError if ``employee_id`` has an open productivity record on a
        work center different from ``workcenter``."""
        if not employee_id or not workcenter:
            return
        conflict = self.sudo().search([
            ('employee_id', '=', employee_id),
            ('date_end', '=', False),
            ('workcenter_id', '!=', workcenter.id),
        ], limit=1)
        if not conflict:
            return
        employee = self.env['hr.employee'].browse(employee_id)
        workorder_label = conflict.workorder_id.display_name or _('(no work order)')
        raise UserError(_(
            "Employee '%(employee)s' is already working on Work Center "
            "'%(other_wc)s' (Work Order: %(workorder)s).\n"
            "The same employee cannot be assigned to Work Center "
            "'%(new_wc)s' at the same time. Please stop the current task "
            "before starting a new one.",
            employee=employee.name,
            other_wc=conflict.workcenter_id.display_name,
            workorder=workorder_label,
            new_wc=workcenter.display_name,
        ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('date_end'):
                continue
            employee_id = vals.get('employee_id')
            workcenter_id = vals.get('workcenter_id')
            if not employee_id or not workcenter_id:
                continue
            workcenter = self.env['mrp.workcenter'].browse(workcenter_id)
            self._check_employee_workcenter_conflict(employee_id, workcenter)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('employee_id') and not vals.get('date_end'):
            for record in self:
                if record.date_end:
                    continue
                workcenter = self.env['mrp.workcenter'].browse(
                    vals.get('workcenter_id', record.workcenter_id.id))
                self._check_employee_workcenter_conflict(vals['employee_id'], workcenter)
        return super().write(vals)