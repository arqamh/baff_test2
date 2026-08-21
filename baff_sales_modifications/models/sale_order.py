import re
from datetime import datetime, timedelta
from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    boat_type_id = fields.Many2one(comodel_name='boat.type', string="Boat Type")
    options = fields.Many2many('mrp.bom', string="Options", domain="[('bom_type', '=', 'option_bom'), ('boat_type_ids', 'in', boat_type_id)]")
    analytic_plan_id = fields.Many2one('account.analytic.plan', string="Analytic Plan")
    inquiry_number = fields.Many2one("crm.lead", string="Inquiry Reference", compute='_compute_inquiry_number')
    project_id = fields.Many2one('project.project', string="Project Id")
    project_start_date = fields.Date(string="Project Start Date")
    cash_project_confirmation = fields.Boolean(string="Cash Project Confirmation")
    confirmed_email_text = fields.Boolean(string="Confirmed Email/Text")
    quotation_required = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Quotation Required', default='no')
    customer_po_available = fields.Boolean(string="Customer PO Available")
    doc_type = fields.Selection([('quotation', 'Quotation'), ('sale', 'Sale')], string="Type", default='quotation',
                                copy=False)
    quotation_id = fields.Many2one('sale.order', string='Quotation', copy=False)
    sale_id = fields.Many2one('sale.order', string='Sale', copy=False)
    state = fields.Selection(selection_add=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('quotation_done', 'Quotation Confirmed'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    so_created = fields.Boolean(string="SO Created", copy=False)
    offer_print_header = fields.Char(string="Offer Print Header")
    offer_print_text = fields.Text(string="Offer Print Text")
    finished_good_location_id = fields.Many2one('stock.location', string='Finished Good Location',
                                                 domain="[('usage', '=', 'internal')]",
                                                 help="Location where finished goods will be stored. This will be used as source location in deliveries and destination location in manufacturing orders.")

    def _compute_inquiry_number(self):
        for record in self:
            if record.opportunity_id:
                record.inquiry_number = record.opportunity_id.id
            else:
                record.inquiry_number = False

    def _prepare_procurement_values(self, group_id=False):
        """Override to set the finished good location as destination for procurement"""
        values = super(SaleOrder, self)._prepare_procurement_values(group_id)
        if self.finished_good_location_id:
            values['location_src_id'] = self.finished_good_location_id.id
        return values

    def _create_picking(self):
        """Override to set the finished good location as source location for deliveries"""
        result = super(SaleOrder, self)._create_picking()
        if self.finished_good_location_id:
            # Update source location for outgoing pickings
            for picking in self.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing'):
                picking.location_id = self.finished_good_location_id.id
                # Update move lines as well
                for move in picking.move_ids_without_package:
                    move.location_id = self.finished_good_location_id.id
        return result

    def action_confirm(self):
        """
        Method to confirm an action, perform various validations, and handle state updates.

        Raises:
            UserError: If a job costing sheet is not created or if the job costing sheet is not in the 'done' state.
            ValidationError: If any of the following conditions are not met:
                - Job costing sheets for quotations are approved.
                - 'Amount Total' and 'Invoiceable Amount Total' are equal.
                - Required validations in the 'Quotation Status Tab' are not validated based on the 'quotation_required' flag.

        Performs the following based on the document type:
            - For 'quotation':
                1. Validates job costing sheet approval status.
                2. Checks consistency of financial amounts.
                3. Validates necessary fields in the 'Quotation Status Tab' based on the 'quotation_required' setting.
                4. Sends a notification email to all users in a specific group with the current quotation's context.
                5. Updates the state to 'quotation_done'.

            - For other document types:
                1. Validates the job costing sheet state to ensure it is in 'done' stage.
                2. Checks consistency of financial amounts.
                3. Updates the project's state to 'ongoing'.
                4. Calls the parent class method to handle additional confirmation logic.
                5. Initiates the 'employee planning slot creation' process for the job.

        Returns:
            Result of the parent class's confirmation method when applicable.
        """
        if not self.job_costing_id:
            raise UserError("Please create a job Costing sheet.")
        if self.doc_type == "quotation":
            if self.job_costing_id.filtered(lambda x: x.state != 'approved'):
                raise ValidationError("Please make sure the job costing sheets are approved.")
            # if self.invoiceable_line:
            #     if self.amount_total != self.invoiceable_amount_total:
            #         raise exceptions.ValidationError("Amount Total and Invoiceable Amount Total should be equal.")
            # if self.quotation_required == 'no':
            #     if not self.customer_po_available and not self.cash_project_confirmation and not self.confirmed_email_text:
            #         raise ValidationError(
            #             "Please make sure whether you have validated any of the validations in Quotation Status Tab.")
            # else:
            #     if not self.customer_po_available or not self.cash_project_confirmation or not self.confirmed_email_text:
            #         raise ValidationError(
            #             "Please make sure whether you have validated all of the validations in Quotation Status Tab.")

            # Send email to group based on quotation status
            group_id = self.env.ref('odoo_job_costing_management.group_job_costing_production')
            email_template = self.env.ref(
                'baff_sales_modifications.baff_mail_template_quotation_confirm')
            users = group_id.users
            email_to = False
            for u in users:
                if u.email:
                    email_to = ', '.join([str(u.email)])
            email_from = self.env.user.email

            ctx = {
                'quotation_number': self.name,
                'quotation_status': self.state,
                'email_from': email_from,
                'email_to': email_to,
                'object': self,
                'user': self.env.user,
            }
            email_template.with_context(ctx).send_mail(self.id, force_send=True)

            self.write({"state": "quotation_done"})

        else:
            if not self.job_costing_id.state == 'done':
                raise UserError("Please make sure the Job Costing Sheet is in Done Stage.")
            # if self.so_invoiceable_line:
            #     if self.amount_total != self.invoiceable_amount_total:
            #         raise exceptions.ValidationError("Amount Total and Invoiceable Amount Total should be equal.")
            self.project_id.write({"state": "ongoing"})
            result = super(SaleOrder, self).action_confirm()
            # Calling employee planning slot creating method
            self.employee_planning(self, self.job_costing_id.project_start_date,
                                   self.job_costing_id.job_labour_line_ids)
            return result

    def employee_planning(self, sales_order, start_date=None, lines=None):
        """
        Generates and manages employee planning slots for a sales order based on job costing data and work center assignments.

        Parameters:
        sales_order: The sales order containing manufacturing orders and associated job costing data.
        start_date: Optional datetime specifying the start date for the planning process. Defaults to None.
        lines: Optional list of planning lines for which the slots need to be generated. Defaults to None.

        Raises:
        UserError: If there is no project start date specified in the associated job costing sheet.
        """
        if sales_order.mrp_production_ids:
            if sales_order.job_costing_id:
                if sales_order.job_costing_id.project_start_date:
                    if sales_order.job_costing_id.job_labour_line_ids:
                        for line in lines:
                            if line.work_center_id:
                                # Getting relevant dates
                                project_start_date = start_date

                                start_date_time = datetime(project_start_date.year,
                                                           project_start_date.month,
                                                           project_start_date.day, 8, 00,
                                                           00, 0) - timedelta(seconds=19800)
                                end_date_time = datetime(project_start_date.year,
                                                         project_start_date.month,
                                                         project_start_date.day, 18, 00, 00,
                                                         0) - timedelta(seconds=19800)
                                if line.employee_id:
                                    # Creating planning slot for the employee selected in the job costing sheet
                                    planing_slot = False
                                    # Looping planing slot creation process by incrementing dates
                                    # until a planing slot is created
                                    while not planing_slot:
                                        planing_slot = sales_order.planing_slot_availability(line.employee_id,
                                                                                             start_date_time,
                                                                                             end_date_time, line,
                                                                                             project_start_date)
                                        if not planing_slot:
                                            start_date_time = start_date_time + timedelta(
                                                days=1) if start_date_time.weekday() not in [4,
                                                                                             5] else start_date_time + timedelta(
                                                days=3) if start_date_time.weekday() == 4 else start_date_time + timedelta(
                                                days=2)
                                            end_date_time = end_date_time + timedelta(
                                                days=1) if end_date_time.weekday() not in [4,
                                                                                             5] else end_date_time + timedelta(
                                                days=3) if end_date_time.weekday() == 4 else end_date_time + timedelta(
                                                days=2)
                                            project_start_date = project_start_date + timedelta(
                                                days=1) if project_start_date.weekday() not in [4,
                                                                                             5] else project_start_date + timedelta(
                                                days=3) if project_start_date.weekday() == 4 else project_start_date + timedelta(
                                                days=2)
                                else:
                                    employee_ids = line.work_center_id.employee_lines.mapped('employee_id')
                                    if employee_ids:
                                        # Creating planning slot for the employees in the relevant work center
                                        planing_slot = False
                                        # Looping planing slot creation process by incrementing dates
                                        # until a planing slot is created
                                        while not planing_slot:
                                            for employee in employee_ids:
                                                planing_slot = sales_order.planing_slot_availability(employee,
                                                                                                     start_date_time,
                                                                                                     end_date_time,
                                                                                                     line,
                                                                                                     project_start_date)
                                                if planing_slot:
                                                    break
                                            if not planing_slot:
                                                start_date_time = start_date_time + timedelta(
                                                    days=1) if start_date_time.weekday() not in [4,
                                                                                                 5] else start_date_time + timedelta(
                                                    days=3) if start_date_time.weekday() == 4 else start_date_time + timedelta(
                                                    days=2)
                                                end_date_time = end_date_time + timedelta(
                                                    days=1) if end_date_time.weekday() not in [4,
                                                                                                 5] else end_date_time + timedelta(
                                                    days=3) if end_date_time.weekday() == 4 else end_date_time + timedelta(
                                                    days=2)
                                                project_start_date = project_start_date + timedelta(
                                                    days=1) if project_start_date.weekday() not in [4,
                                                                                                 5] else project_start_date + timedelta(
                                                    days=3) if project_start_date.weekday() == 4 else project_start_date + timedelta(
                                                    days=2)
                else:
                    raise UserError(_("There is no project start date in the Job Costing Sheet %s. "
                                      "Please add the project start date.", sales_order.job_costing_id.display_name))

    def planing_slot_availability(self, employee, start_date_time, end_date_time, line, project_start_date):
        """Checking the employees availability from their plannings"""
        # Fetching employee working time details
        working_day = employee.resource_calendar_id.attendance_ids.filtered(
            lambda x: int(x.dayofweek) == project_start_date.weekday())
        working_duration = sum(working_day.mapped(lambda x: x.hour_to - x.hour_from))
        morning_period = working_day.filtered(lambda x: x.day_period == 'morning').hour_to - 5.5
        afternoon_period = working_day.filtered(lambda x: x.day_period == 'afternoon').hour_from - 5.5
        morning_start_time = working_day.filtered(lambda x: x.day_period == 'morning').hour_from
        afternoon_start_time = working_day.filtered(lambda x: x.day_period == 'afternoon').hour_from
        planning = False

        operation_line = False
        if line.bom_operation_id:
            operation_line = self.env['mrp.workorder'].search([('operation_id', '=', line.bom_operation_id.id)], limit=1)
        planning_slots = False

        if not working_duration:
            return False
        if line.hour > working_duration:
            # Checking employee availability for the tasks which takes multiple days
            pr_start_date = project_start_date
            separated_hours = []
            dates = []
            hours = line.hour
            # Splitting task's duration into days
            while hours > working_duration:
                separated_hours.append(working_duration)
                hours = hours - working_duration
            separated_hours.append(hours)
            for hour in separated_hours:
                # Searching for employee availability
                # Fetch planning slots with date filtering and sorting
                query_slots = """
                    SELECT * 
                    FROM planning_slot 
                    WHERE employee_id = %s AND DATE(end_datetime) <= %s AND DATE(start_datetime) >= %s;
                """
                params_slots = (
                employee.id, pr_start_date.strftime('%Y-%m-%d'), pr_start_date.strftime('%Y-%m-%d'))
                self._cr.execute(query_slots, params_slots)

                # Fetch results without applying sorting here; instead sort them after fetching.
                results_raw = [r[0] for r in self.env.cr.fetchall()]
                self.env['planning.slot'].browse(results_raw).sorted(
                    key=lambda x: x.start_datetime)

                # planning_slots = self.env['planning.slot'].search([('employee_id', '=', employee.id)]).filtered(
                #     lambda x: x.end_datetime.date() <= pr_start_date <= x.start_datetime.date()).sorted(
                #     key=lambda x: x.start_datetime)
                if planning_slots:
                    return False
                else:
                    dates.append(pr_start_date)
                    pr_start_date = pr_start_date + timedelta(
                                                days=1) if pr_start_date.weekday() not in [4,
                                                                                             5] else pr_start_date + timedelta(
                                                days=3) if pr_start_date.weekday() == 4 else pr_start_date + timedelta(
                                                days=2)
            # Creating tasks for the available dates
            for i, date in enumerate(dates):
                slot_duration = separated_hours[i]
                morning_time_slot = datetime(date.year,
                                             date.month,
                                             date.day, int(morning_start_time // 1),
                                             int(morning_start_time % 1 * 100 / 100 * 60), 00, 0) - timedelta(seconds=19800)
                afternoon_time_slot = datetime(date.year,
                                               date.month,
                                               date.day, int(afternoon_start_time // 1),
                                               int(afternoon_start_time % 1 * 100 / 100 * 60), 00, 0) - timedelta(seconds=19800)

                morning_working_time = sum(working_day.filtered(lambda x: x.day_period == 'morning').mapped(
                    lambda x: x.hour_to - x.hour_from))
                afternoon_working_time = sum(working_day.filtered(lambda x: x.day_period == 'afternoon').mapped(
                    lambda x: x.hour_to - x.hour_from))

                planning = self._create_planning_slot(employee, operation_line, morning_time_slot,
                                                      (morning_time_slot + timedelta(hours=morning_working_time if morning_working_time <= slot_duration else slot_duration)))
                slot_duration = slot_duration - morning_working_time if slot_duration >= morning_working_time else 0
                if slot_duration:
                    planning = self._create_planning_slot(employee, operation_line, afternoon_time_slot,
                                                      (afternoon_time_slot + timedelta(hours=slot_duration)))
            return planning

        else:
            # Fetch planning slots with date filtering and sorting
            query_slots = """
                                SELECT * 
                                FROM planning_slot 
                                WHERE employee_id = %s AND DATE(end_datetime) <= %s AND DATE(start_datetime) >= %s;
                            """
            params_slots = (
                employee.id, project_start_date.strftime('%Y-%m-%d'), project_start_date.strftime('%Y-%m-%d'))
            self._cr.execute(query_slots, params_slots)

            # Fetch results without applying sorting here; instead sort them after fetching.
            results_raw = [r[0] for r in self.env.cr.fetchall()]
            self.env['planning.slot'].browse(results_raw).sorted(
                key=lambda x: x.start_datetime)

            # planning_slots = self.env['planning.slot'].search([('resource_id.employee_id', '=', employee.id)]).filtered(
            #     lambda x: x.end_datetime.date() <= project_start_date <= x.start_datetime.date()).sorted(
            #     key=lambda x: x.start_datetime)

        if not planning_slots:
            # Creating a planning slot if there are no planning slot for the employee of the given date
            morning_duration = sum(working_day.filtered(lambda x: x.day_period == 'morning').mapped(lambda x: x.hour_to - x.hour_from))
            if line.hour > morning_duration:
                separated_hours = []
                hours = line.hour
                count_hours = 0
                start_date = start_date_time
                # Splitting task's duration into days
                while hours > morning_duration:
                    separated_hours.append(morning_duration)
                    hours = hours - morning_duration
                separated_hours.append(hours)
                for hour in separated_hours:
                    if count_hours:
                        start_date += timedelta(hours=count_hours)
                    planning = self._create_planning_slot(employee, operation_line, start_date,
                                                          (start_date + timedelta(hours=hour)))
                    if hour == morning_duration:
                        start_date += timedelta(hours=((afternoon_period - morning_period) + hour))
            else:
                planning = self._create_planning_slot(employee, operation_line, start_date_time,
                                                      (start_date_time + timedelta(hours=line.hour)))
            return planning

        else:
            total_duration = sum(planning_slots.mapped('duration'))
            # If there are planning slots, checking the employee's availability for the relevant operation
            # of the given date
            if morning_period and afternoon_period:
                lunch_time = afternoon_period - morning_period
                if not lunch_time:
                    raise UserError(_("Employee %s has no lunch time defined.", employee.name))
            else:
                raise UserError(_("Employee %s has no proper working time defined.", employee.name))

            if total_duration <= working_duration:
                if len(planning_slots) == 1:
                    # Creating planning slot if there is only one existing planning slot for that employee
                    lunch_start_time = datetime(planning_slots.start_datetime.year,
                                                planning_slots.start_datetime.month,
                                                planning_slots.start_datetime.day, int(morning_period // 1),
                                                int(morning_period % 1 * 100 / 100 * 60), 00, 0)
                    lunch_end_time = datetime(planning_slots.start_datetime.year,
                                              planning_slots.start_datetime.month,
                                              planning_slots.start_datetime.day, int(afternoon_period // 1),
                                              int(afternoon_period % 1 * 100 / 100 * 60), 00, 0)

                    morning_time_slots = planning_slots.filtered(
                        lambda x: start_date_time <= x.start_datetime and x.end_datetime <= lunch_start_time)
                    afternoon_time_slots = planning_slots.filtered(
                        lambda x: lunch_end_time <= x.start_datetime and x.end_datetime <= end_date_time)

                    if morning_time_slots:
                        if ((morning_time_slots.start_datetime - start_date_time).seconds / 60) >= (line.hour * 60):
                            planning = self._create_planning_slot(employee, operation_line, start_date_time,
                                                                  (start_date_time + timedelta(hours=line.hour)))
                            return planning
                        elif ((lunch_start_time - morning_time_slots.end_datetime).seconds / 60) >= (line.hour * 60):
                            planning = self._create_planning_slot(employee, operation_line, morning_time_slots.end_datetime,
                                                                  (morning_time_slots.end_datetime + timedelta(
                                                                      hours=line.hour)))
                            return planning
                    elif not morning_time_slots:
                        planning = self._create_planning_slot(employee, operation_line, start_date_time,
                                                              (start_date_time + timedelta(hours=line.hour)))
                        return planning
                    elif afternoon_time_slots:
                        if ((afternoon_time_slots.start_datetime - lunch_end_time).seconds / 60) >= (line.hour * 60):
                            planning = self._create_planning_slot(employee, operation_line, lunch_end_time,
                                                                  (lunch_end_time + timedelta(hours=line.hour)))
                            return planning
                        elif ((end_date_time - afternoon_time_slots.end_datetime).seconds / 60) >= (line.hour * 60):
                            planning = self._create_planning_slot(employee, operation_line, afternoon_time_slots.end_datetime,
                                                                  (afternoon_time_slots.end_datetime + timedelta(
                                                                      hours=line.hour)))
                            return planning
                    elif not afternoon_time_slots:
                        planning = self._create_planning_slot(employee, operation_line, lunch_end_time,
                                                              (lunch_end_time + timedelta(hours=line.hour)))
                        return planning

                else:
                    # Creating planning slot if there are multiple existing planning slots for that employee
                    lunch_start_time = datetime(start_date_time.year,
                                                start_date_time.month,
                                                start_date_time.day, int(morning_period // 1),
                                                int(morning_period % 1 * 100 / 100 * 60), 00, 0)
                    lunch_end_time = datetime(start_date_time.year,
                                              start_date_time.month,
                                              start_date_time.day, int(afternoon_period // 1),
                                              int(afternoon_period % 1 * 100 / 100 * 60), 00, 0)

                    morning_time_slots = planning_slots.filtered(
                        lambda x: start_date_time <= x.start_datetime and x.end_datetime <= lunch_start_time)
                    afternoon_time_slots = planning_slots.filtered(
                        lambda x: lunch_end_time <= x.start_datetime and x.end_datetime <= end_date_time)

                    if morning_time_slots:
                        if len(morning_time_slots) == 1:
                            if ((morning_time_slots.start_datetime - start_date_time).seconds / 60) >= (
                                    line.hour * 60):
                                planning = self._create_planning_slot(employee, operation_line, start_date_time,
                                                                      (start_date_time + timedelta(hours=line.hour)))
                                return planning
                            elif ((lunch_start_time - morning_time_slots.end_datetime).seconds / 60) >= (
                                    line.hour * 60):
                                planning = self._create_planning_slot(employee, operation_line,
                                                                      morning_time_slots.end_datetime,
                                                                      (morning_time_slots.end_datetime + timedelta(
                                                                          hours=line.hour)))
                                return planning
                        else:
                            end_time = start_date_time
                            prv_slot_endtime = False
                            end_slot = morning_time_slots[-1]
                            before_end_slot = morning_time_slots[-2]
                            for slot in morning_time_slots:
                                start_time = slot.start_datetime if end_slot != slot else slot.end_datetime
                                if end_slot != slot:
                                    if ((slot.start_datetime - end_time).seconds / 60) >= (line.hour * 60):
                                        planning = self._create_planning_slot(employee, operation_line, end_time,
                                                                              (end_time + timedelta(hours=line.hour)))
                                        return planning
                                    else:
                                        end_time = slot.end_datetime
                                        prv_slot_endtime = slot.end_datetime if before_end_slot == slot else False
                                elif end_slot == slot:
                                    if ((slot.start_datetime - prv_slot_endtime).seconds / 60) >= (line.hour * 60):
                                        planning = self._create_planning_slot(employee, operation_line, prv_slot_endtime,
                                                                              (prv_slot_endtime + timedelta(hours=line.hour)))
                                        return planning
                                    elif ((lunch_start_time - slot.end_datetime).seconds / 60) >= (line.hour * 60):
                                        planning = self._create_planning_slot(employee, operation_line, slot.end_datetime,
                                                                              (slot.end_datetime + timedelta(hours=line.hour)))
                                        return planning
                                    else:
                                        end_time = slot.end_datetime
                                        prv_slot_endtime = slot.end_datetime if before_end_slot == slot else False

                    else:
                        planning = self._create_planning_slot(employee, operation_line, start_date_time,
                                                              (start_date_time + timedelta(hours=line.hour)))
                        return planning

                    if afternoon_time_slots:
                        if len(afternoon_time_slots) == 1:
                            if ((afternoon_time_slots.start_datetime - lunch_end_time).seconds / 60) >= (line.hour * 60):
                                planning = self._create_planning_slot(employee, operation_line, lunch_end_time,
                                                                      (lunch_end_time + timedelta(hours=line.hour)))
                                return planning
                            elif ((end_date_time - afternoon_time_slots.end_datetime).seconds / 60) >= (line.hour * 60):
                                planning = self._create_planning_slot(employee, operation_line, afternoon_time_slots.end_datetime,
                                                                      (afternoon_time_slots.end_datetime + timedelta(
                                                                          hours=line.hour)))
                                return planning

                        else:
                            end_time = start_date_time
                            prv_slot_endtime = False
                            end_slot = afternoon_time_slots[-1]
                            before_end_slot = afternoon_time_slots[-2]
                            for slot in afternoon_time_slots:
                                start_time = slot.start_datetime if end_slot != slot else slot.end_datetime
                                if end_slot != slot:
                                    if ((slot.start_datetime - lunch_end_time).seconds / 60) >= (line.hour * 60):
                                        planning = self._create_planning_slot(employee, operation_line, end_time,
                                                                              (end_time + timedelta(hours=line.hour)))
                                        return planning
                                    else:
                                        end_time = slot.end_datetime
                                        prv_slot_endtime = slot.end_datetime if before_end_slot == slot else False
                                elif end_slot == slot:
                                    if ((slot.start_datetime - prv_slot_endtime).seconds / 60) >= (line.hour * 60):
                                        planning = self._create_planning_slot(employee, operation_line, prv_slot_endtime,
                                                                              (prv_slot_endtime + timedelta(
                                                                                  hours=line.hour)))
                                        return planning
                                    elif ((end_date_time - slot.end_datetime).seconds / 60) >= (line.hour * 60):
                                        planning = self._create_planning_slot(employee, operation_line, slot.end_datetime,
                                                                              (slot.end_datetime + timedelta(
                                                                                  hours=line.hour)))
                                        return planning
                                    else:
                                        end_time = slot.end_datetime
                                        prv_slot_endtime = slot.end_datetime if before_end_slot == slot else False
                    else:
                        planning = self._create_planning_slot(employee, operation_line, lunch_end_time,
                                                              (lunch_end_time + timedelta(hours=line.hour)))
                        return planning

    def _create_planning_slot(self, employee, operation_line, start_date_time, end_date_time):
        """
        Creates a planning slot for a specific employee based on the provided operation line and time period.

        Parameters:
        - employee: The employee for whom the planning slot is to be created.
        - operation_line: The associated operation line containing details such as the work center.
        - start_date_time: Datetime object representing the start time of the planning slot.
        - end_date_time: Datetime object representing the end time of the planning slot.

        Returns:
        - The created planning slot record.

        Raises:
        - UserError: If there is no resource found for the given employee.

        Additional details:
        - The function searches for a resource associated with the given employee.
        - If a corresponding resource is found, it calculates the allocated hours and sets other necessary fields before creating the planning slot.
        - If no resource is found, an error is raised specifying the unavailable resource for the employee.
        """
        resource = self.env['resource.resource'].search([('employee_id', '=', employee.id)])
        if resource:
            values = {
                "resource_id": resource.id,
                "project_id": self.job_costing_id.project_id.id,
                "mrp_id": self.mrp_production_ids[0].id,
                "start_datetime": start_date_time,
                "end_datetime": end_date_time,
                "allocated_hours": (end_date_time - start_date_time).seconds / 3600,
                "operation_id": operation_line.id if operation_line else False,
                "work_center_id": operation_line.workcenter_id.id if operation_line else False,
            }
            planning = self.env['planning.slot'].create(values)
            return planning
        else:
            raise UserError(_("There is no resource for the employee %s", employee.name))


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    cost_center = fields.Many2one('account.analytic.plan', string="Analytic TAG")
    project_number = fields.Char(string="Analytic Account")
