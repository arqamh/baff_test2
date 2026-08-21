from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
from datetime import datetime, timedelta


class InheritPlanningSlot(models.Model):
    _inherit = 'planning.slot'

    # def _domain_operation(self):
    #     if self.mrp_id:
    #         return [('production_id', '=', self.mrp_id.id)]
    #     else:
    #         return []

    prioritize = fields.Boolean(string="Prioritize")
    mrp_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    operation_id = fields.Many2one('mrp.workorder', string="Operation")
    work_center_id = fields.Many2one('mrp.workcenter', string="Work Center")
    loss_id = fields.Many2one('mrp.workcenter.productivity.loss', "Productivity", ondelete='restrict')
    locked = fields.Boolean(string="Locked", default=False)
    sales_rep_id = fields.Many2one('res.users', string='Sales Rep')
    color = fields.Integer("Color", compute='_compute_color')
    unlock = fields.Boolean(string="Unlock", default=False)
    project_id = fields.Many2one('project.project', string="Project")

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        """
        Triggered method when the operation_id field undergoes a change.
        This method updates the work_center_id field based on the value of operation_id.

        - If operation_id is set, work_center_id is updated to the corresponding workcenter_id of operation_id.
        - If operation_id is not set, work_center_id is reset to False.
        """
        if self.operation_id:
            self.work_center_id = self.operation_id.workcenter_id
        else:
            self.work_center_id = False

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """
        This method is triggered when there is a change in the value of the 'project_id' field. It performs the following actions:

        - Verifies if a `project_id` value exists.
        - Searches for manufacturing workorders (`mrp.workorder`) associated with the project's product name.
        - If a single workorder is found:
          - Assigns the workorder to the `operation_id` field.
        - If multiple workorders are found:
          - Clears the `operation_id` field.
          - Sets a dynamic domain on the `operation_id` field, limiting possible values to the found workorders' IDs.
        - If no workorders are found:
          - Clears the `operation_id` field.
          - Sets an empty domain on the `operation_id` field.
        """
        if self.project_id:
            workorders = self.env['mrp.workorder'].search([('product_id.name', '=', self.project_id.name)])
            if workorders:
                if len(workorders) == 1:
                    self.operation_id = workorders[0]
                else:
                    self.operation_id = False
                    return {
                       'domain': {'operation_id': [('id', 'in', workorders.ids)]},
                   }
            else:
                self.operation_id = False
                return {
                    'domain': {'operation_id': []},
                }
                
    @api.depends('role_id.color', 'resource_id.color', 'prioritize', 'sales_rep_id')
    def _compute_color(self):
        """
        Computes the color for the given slot based on various conditions.

        Dependencies:
        - role_id.color
        - resource_id.color
        - prioritize
        - sales_rep_id

        Logic:
        - Assigns a default color value to the `color` field based on specific conditions.
        - If `prioritize` is True, sets the color to 1.
        - If a `sales_rep_id` exists, sets the color to the color associated with the sales representative (`color_pick` from `sales_rep_id`).
        - Otherwise, falls back to the `color` from `role_id` or `resource_id`.
        """
        for slot in self:
            if slot.prioritize:
                slot.color = 1
            elif slot.sales_rep_id:
                slot.color = slot.sales_rep_id.color_pick
            else:
                slot.color = slot.role_id.color or slot.resource_id.color

    def write(self, vals):
        """
        Handles the write operation for the object while considering specific business rules.

        This method overrides the default write behavior to include additional logic based on certain conditions:
        - If the object is locked, prevents edits unless specific conditions are met.
        - Updates the planning based on the provided 'end_datetime' and 'start_datetime' values when applicable.
        - Validates overlapping slots when both 'start_datetime' and 'end_datetime' are provided.

        Parameters:
        vals (dict): Dictionary of values to update the object with.

        Returns:
        bool: Result of the write operation.

        Raises:
        AccessError: If an attempt is made to edit a locked task without proper conditions.
        """
        # Call the super method to perform the default write operation
        end_date = False
        if self.locked:
            if vals.get('locked') == False:
                if vals.get('end_datetime'):
                    end_date = self.end_datetime
                result = super(InheritPlanningSlot, self).write(vals)
                if vals.get('end_datetime') and not vals.get('start_datetime'):
                    self.update_planning(vals, end_date)
                elif not vals.get('end_datetime') and vals.get('start_datetime'):
                    self.update_planning(vals, end_date)
                if vals.get('end_datetime') and vals.get('start_datetime'):
                    self.overlapping_slots()
                return result
            else:
                AccessError(_("You can not edit locked tasks."))
        else:
            if vals.get('end_datetime'):
                end_date = self.end_datetime
            result = super(InheritPlanningSlot, self).write(vals)
            if vals.get('end_datetime') and not vals.get('start_datetime'):
                self.update_planning(vals, end_date)
            elif not vals.get('end_datetime') and vals.get('start_datetime'):
                self.update_planning(vals, end_date)
            if vals.get('end_datetime') and vals.get('start_datetime'):
                self.overlapping_slots()
            return result

    def overlapping_slots(self):
        """
        Check and manage overlapping time slots for scheduling purposes.

        This method identifies overlapping time slots for a given resource
        and adjusts the scheduling to avoid overlaps. If overlapping slots are found,
        the slots are rescheduled to create a non-conflicting allocation window.

        The process involves:
        1. Searching for slots with matching resource_id where time intervals overlap.
        2. Computing the adjusted start and end datetime for the time slot taking
           into account business hours constraints (e.g., 8 AM to 5 PM).
        3. Filtering and sorting relevant planning slots for the resource.
        4. Adjusting the allocation duration of the slot based on the overlapping slot details
           and updating the slot's start and end datetime to resolve the conflict.

        Restrictions applied include:
        - New start and end datetimes are set to adhere to specific working hours.
        - Time slots that extend beyond the end of the workday are adjusted to start from the
          beginning of the next permitted workday.
        """
        for slot in self:
            domain = [
                ('id', '!=', slot.id),
                ('start_datetime', '<', slot.end_datetime),
                ('end_datetime', '>', slot.start_datetime),
                ('resource_id', '=', slot.resource_id.id),
            ]
            overlapping_slots = self.search(domain)
            if overlapping_slots:
                end_date = overlapping_slots.end_datetime
                if end_date:
                    if end_date.hour >= 17:
                        end_date = datetime(end_date.year,
                                            end_date.month,
                                            (end_date.day + timedelta(days=1)), 8, 00, 00,
                                            0) - timedelta(seconds=19800)

                planning_slot = self.env['planning.slot'].search([('resource_id', '=', slot.resource_id.id),
                                                                  ('start_datetime', '<=', end_date)]).sorted(
                    key=lambda x: x.start_datetime)

                allocated_hrs = (slot.end_datetime - slot.start_datetime).seconds

                for planning in planning_slot:
                    duration = end_date - planning.start_datetime
                    if duration.total_seconds() >= allocated_hrs:
                        slot.end_datetime = end_date + timedelta(seconds=allocated_hrs)
                        slot.start_datetime = end_date
                        break
                    else:
                        if planning.end_datetime.time().hour >= 17:
                            end_date = datetime(planning.end_datetime.year,
                                                planning.end_datetime.month,
                                                (planning.end_datetime.day + timedelta(days=1)), 8, 00, 00,
                                                0) - timedelta(seconds=19800)

    def update_planning(self, vals, end_date):
        """
        Function to update the planning or scheduling of a task by adjusting its start and end datetime.

        Parameters:
        vals (dict): A dictionary containing updated values. It should include 'start_datetime' and 'end_datetime' if updates to the scheduling are required.
        end_date (datetime): The new end date for the task. May trigger adjustments to related slots and timings.

        Raises:
        UserError: Raised when attempting to adjust a prioritized task.

        Logic:
        - If the task is prioritized and both start and end datetime are provided, the function raises a UserError.
        - Computes the time difference between the current end datetime and the new end_date to determine whether the task timing is being moved forward or backward.
        - Checks for overlapping slots within the same resource and adjusts their timing accordingly, shifting their start and end datetime by the computed difference.
        - For tasks being moved backward, adjusts future planning slots related to the same resource to maintain consistency in scheduling.

        Dependencies:
        - Searches and modifies `planning.slot` records related to the same resource as the current task.

        Note:
        Ask and verify the logic behind the "Move_backward" variable for specific functionality clarity.
        """
        if self.prioritize and vals.get('start_datetime') and vals.get('end_datetime'):
            raise UserError(_("This is a prioritized task, you can't shift it."))
        difference = False
        overlapped_slot = False
        move_backward = False
        if end_date:
            if end_date > self.end_datetime:
                difference = (end_date - self.end_datetime).seconds
                move_backward = True
                
# ask from Kasun and verify "Move_backward"
            
            else:
                difference = (self.end_datetime - end_date).seconds
                overlapped_slot = self.env['planning.slot'].search(
                    [('resource_id', '=', self.resource_id.id), ('start_datetime', '<', self.end_datetime),
                     ('start_datetime', '>', self.end_datetime), ('id', '!=', self.id)]).sorted(key=lambda x: x.start_datetime)
            if difference:
                if overlapped_slot:
                    overlapped_slot.start_datetime = overlapped_slot.start_datetime - timedelta(
                        seconds=difference) if end_date > self.end_datetime else overlapped_slot.start_datetime + timedelta(
                        seconds=difference)
                    overlapped_slot.end_datetime = overlapped_slot.end_datetime - timedelta(
                        seconds=difference) if end_date > self.end_datetime else overlapped_slot.end_datetime + timedelta(
                        seconds=difference)
                if move_backward:
                    planning_slots = self.env['planning.slot'].search(
                        [('resource_id', '=', self.resource_id.id), ('start_datetime', '>=', self.end_datetime),
                         ('id', '!=', self.id)]).sorted(key=lambda x: x.start_datetime)
                    if planning_slots:
                        for planning in planning_slots[0]:
                            planning.start_datetime = planning.start_datetime - timedelta(
                                seconds=difference) if end_date > self.end_datetime else planning.start_datetime + timedelta(
                                seconds=difference)
                            planning.end_datetime = planning.end_datetime - timedelta(
                                seconds=difference) if end_date > self.end_datetime else planning.end_datetime + timedelta(
                                seconds=difference)

    def split_planning_slot(self):
        """
        Creates and opens a slot planning wizard for the current slot instance.

        This method initializes a new `slot.planning.wizard` record with the data from the current slot instance. It then returns an action dictionary to open the wizard in a form view.

        Returns:
            dict: An action dictionary that specifies the wizard to be opened in a form view.
        """
        wizard = self.env['slot.planning.wizard'].create({
            'slot_id': self.id,
            'resource_id': self.resource_id.id,
            'role_id': self.role_id.id,
            'prioritize': self.prioritize,
            'project_id': self.project_id.id,
            'operation_id': self.operation_id.id,
            'work_center_id': self.work_center_id.id,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'allocated_hours': self.allocated_hours,
        })
        return {
            'name': 'Slot Planning Wizard',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'slot.planning.wizard',
            'res_id': wizard.id,
            'target': 'new',
            'domain': [('slot_id', '=', self.id)],
        }

    def lock_planning_slot(self):
        """
        Locks the planning slot by validating and updating information related to the task, operation, work center, and employee allocation. Ensures data consistency and integrity for manufacturing operations.

        Iterates through each record and performs the following actions:
        - Validates whether the required fields such as `operation_id`, `loss_id`, and `employee_id` are provided.
        - Validates that the allocated employee is assigned to the correct work center for the task.
        - Updates the operation's work center if needed.
        - Appends the details of the employee, work center, loss, and time allocation into the operation's `time_ids`.
        - Marks the slot as locked once it is successfully processed.
        - Checks for other unlocked slots related to the same operation and processes `qty_producing` or finishes the operation if no other slots remain unlocked.
        - For multiple job types mapped to a work center, raises an error to prevent ambiguity in the job cost mapping.
        - Creates a job cost line for labor if a valid job type is found and mapped to the work center.
        - Provides relevant error messages to guide the user if validation fails due to missing data or configuration issues.
        """
        for record in self:
            lines = []
            if record.operation_id:
                if record.loss_id:
                    if record.employee_id:
                        work_center = record.work_center_id if record.work_center_id else record.operation_id.workcenter_id
                        workcenter_employees = self.env['mrp.workcenter'].search([('id', '=', work_center.id)]).mapped('employee_ids')
                        if workcenter_employees:
                            if record.employee_id.id not in workcenter_employees.ids:
                                raise ValidationError(_("The allocated employee %s for this task is not assigned into the work center %s.", record.employee_id.name, record.work_center_id.name))
                        if record.operation_id.workcenter_id.id == record.work_center_id.id or not record.work_center_id:
                            lines.append((0, 0, {
                                'employee_id': record.employee_id.id,
                                'workcenter_id': record.work_center_id.id,
                                'date_start': record.start_datetime,
                                'date_end': record.end_datetime,
                                'loss_id': record.loss_id.id,
                                'slot_id': record.id,
                            }))
                            record.operation_id.time_ids = lines
                            record.locked = True

                            slots = self.search([('operation_id', '=', record.operation_id.id),
                                                 ('id', '!=', record.id),
                                                 ('locked', '=', False)])
                            if not slots:
                                record.operation_id.qty_producing = record.operation_id.qty_production
                                record.operation_id.do_finish()
                        else:
                            record.operation_id.workcenter_id = record.work_center_id.id
                            record.operation_id.operation_id.workcenter_id = record.work_center_id.id

                            lines.append((0, 0, {
                                'employee_id': record.employee_id.id,
                                'workcenter_id': record.work_center_id.id,
                                'date_start': record.start_datetime,
                                'date_end': record.end_datetime,
                                'loss_id': record.loss_id.id,
                                'slot_id': record.id,
                            }))
                            record.operation_id.time_ids = lines
                            record.locked = True
                            slots = self.search([('operation_id', '=', record.operation_id.id),
                                                 ('id', '!=', record.id),
                                                 ('locked', '=', False)])

                            job_cost_sheet = record.operation_id.production_id.job_cost_id
                            job_type = self.env['job.type'].search([('work_center_ids', 'in', record.work_center_id.id)])
                            if not job_type:
                                raise UserError(_("This work center has no job type mapped."))
                            if len(job_type) > 1:
                                raise UserError(_("This work center is mapped to multiple job types."))
                            if job_type:
                                job_cost_labor_line = job_cost_sheet.job_cost_line_ids.create({
                                    'job_costing_id': job_cost_sheet.id,
                                    'job_type_id': job_type.id,
                                    'work_center_id': record.work_center_id.id,
                                    'description': job_type.name,
                                    'qty': 0,
                                    'hour': 0,
                                    'cost_price': record.work_center_id.costs_hour,
                                    'actual_hour': record.allocated_hours,
                                    'operation_id': record.operation_id.id,
                                    'slot_id': record.id,
                                    'job_type': 'labour'
                                })
                            if not slots:
                                record.operation_id.qty_producing = record.operation_id.qty_production
                                record.operation_id.do_finish()

                else:
                    raise UserError(_("Please add the productivity of the task %s", record.display_name))
            else:
                raise UserError(_("Please add the operation for the task %s", record.display_name))

    def unlock_planning_slot(self):
        """
        Unlocks the planning slot for the current record.

        This method performs the following actions for each record in the set:
        1. Checks if the record is locked.
        2. Identifies and unlinks any associated time records in the 'operation_id.time_ids' for the slot.
        3. Identifies and unlinks any associated job cost lines in 'job.cost.line' for the slot.
        4. Updates the 'locked' status of the record to False.
        """
        for record in self:
            if record.locked:
                time_record = record.operation_id.time_ids.filtered(lambda x: x.slot_id.id == record.id)
                job_line = self.env['job.cost.line'].search([('slot_id', '=', record.id)])
                if time_record:
                    time_record.unlink()
                if job_line:
                    job_line.unlink()
                record.locked = False
