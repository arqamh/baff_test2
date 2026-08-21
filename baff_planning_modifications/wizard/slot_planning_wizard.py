from odoo import models, fields, api
from datetime import datetime


class SlotPlanningWizard(models.TransientModel):
    _name = 'slot.planning.wizard'
    _description = "Slot Planning Wizard"

    slot_id = fields.Many2one('planning.slot', string='Slot', invisible=True, domain="[('state', '=', 'open')]")
    resource_id = fields.Many2one('resource.resource', string='Resource')
    role_id = fields.Many2one('planning.role', string='Role')
    prioritize = fields.Boolean(string='Prioritize')
    project_id = fields.Many2one('project.project', string='Project')
    operation_id = fields.Many2one('mrp.workorder', string="Operation")
    work_center_id = fields.Many2one('mrp.workcenter', string="Work Center")
    start_datetime = fields.Datetime(string='Start Date')
    end_datetime = fields.Datetime(string='End Date')
    allocated_hours = fields.Float(string='Allocated Hours', compute='_compute_allocated_hours')
    task_lines = fields.One2many('planning.task.lines', 'task_line_id', string="Task Lines")

    @api.depends('start_datetime', 'end_datetime')
    def _compute_allocated_hours(self):
        """
        Computes the allocated hours for a record based on the start and end datetime fields.

        This method calculates the difference between `start_datetime` and `end_datetime`
        in hours and stores the result in the `allocated_hours` field. If either of the
        datetime fields is missing, the allocated hours will be set to 0.

        Dependencies:
        - start_datetime
        - end_datetime
        """
        for record in self:
            if record.start_datetime and record.end_datetime:
                record.allocated_hours = (record.end_datetime - record.start_datetime).total_seconds() / 3600
            else:
                record.allocated_hours = 0.0

    def write(self, vals):
        """
        Performs the write operation on the SlotPlanningWizard model and updates related slot records.

        Parameters:
        vals (dict): Dictionary of values to be written to the SlotPlanningWizard record.

        Returns:
        bool: True if the record is successfully updated, otherwise False.

        Behavior:
        - Calls the base `write` method to update the SlotPlanningWizard with the provided values.
        - If the record has a linked `slot_id`, updates the corresponding slot record with specific fields from the current SlotPlanningWizard instance.
        - Fields updated in the `slot_id` include:
          - resource_id
          - role_id
          - prioritize
          - project_id
          - end_datetime
          - start_datetime
          - allocated_hours
          - operation_id
          - work_center_id
        - Invokes the `create_shift` method to handle any additional shift creation logic after updating the slot.
        """

        result = super(SlotPlanningWizard, self).write(vals)
        if self.slot_id:
            self.slot_id.write({
                'resource_id': self.resource_id.id,
                'role_id': self.role_id.id,
                'prioritize': self.prioritize,
                'project_id': self.project_id.id,
                'end_datetime': self.end_datetime,
                'start_datetime': self.start_datetime,
                'allocated_hours': self.allocated_hours,
                'operation_id': self.operation_id.id,
                'work_center_id': self.work_center_id.id,
            })
            self.create_shift()
        return result

    def create_shift(self):
        """
        Creates planning slots for each task line in the current object.

        This method iterates over all task lines associated with the current object
        and constructs a dictionary of slot values for each line. The constructed
        slot values are then used to create new planning slot records in the
        'planning.slot' model.

        The slot values include:
        - Resource ID associated with the task line
        - Role ID associated with the task line
        - Project ID from the current object
        - Start and end datetime of the task line
        - Prioritization flag of the task line
        - Operation ID from the current object
        - Work center ID from the current object
        - Allocated hours from the task line
        """
        for line in self.task_lines:
            slot_vals = {
                'resource_id': line.resource_id.id,
                'role_id': line.role_id.id,
                'project_id': self.project_id.id,
                'end_datetime': line.end_datetime,
                'start_datetime': line.start_datetime,
                'prioritize': line.prioritize,
                'operation_id': self.operation_id.id,
                'work_center_id': self.work_center_id.id,
                'allocated_hours': line.allocated_hours,
            }
            self.env['planning.slot'].create(slot_vals)


class PlanningTaskLines(models.TransientModel):
    _name = 'planning.task.lines'
    _description = "Planning Task Lines"

    @api.model
    def default_get(self, fields):
        """
        Retrieve default values for the fields of the model.

        This method overrides the default_get method to populate certain fields with
        values derived from a planning slot record, if applicable. It checks the
        active record id in the context, fetches corresponding planning slot data,
        and updates the result dictionary with related field values.

        Parameters:
            fields (list): A list of field names for which default values are
                           expected.

        Returns:
            dict: A dictionary containing default values for the specified fields.
                  If a planning slot is found and matches the active context, the
                  dictionary will also include values from the planning slot for
                  resource_id, role_id, project_id, prioritize, start_datetime,
                  end_datetime, and allocated_hours.
        """
        result = super(PlanningTaskLines, self).default_get(fields)
        planning_slot = self.env['planning.slot'].search([]).filtered(lambda x: x.id == self.env.context.get('active_id'))
        if planning_slot:
            result['resource_id'] = planning_slot.resource_id.id
            result['role_id'] = planning_slot.role_id.id
            result['project_id'] = planning_slot.project_id.id
            result['prioritize'] = planning_slot.prioritize
            result['start_datetime'] = planning_slot.start_datetime
            result['end_datetime'] = planning_slot.end_datetime
            result['allocated_hours'] = planning_slot.allocated_hours
        return result

    task_line_id = fields.Many2one('slot.planning.wizard')
    resource_id = fields.Many2one('resource.resource', string='Resource')
    role_id = fields.Many2one('planning.role', string='Role')
    prioritize = fields.Boolean(string='Prioritize')
    project_id = fields.Many2one('project.project', string='Project')
    start_datetime = fields.Datetime(string='Start Date')
    end_datetime = fields.Datetime(string='End Date')
    allocated_hours = fields.Float(string='Allocated Hours', compute='_compute_allocated_hours')

    @api.depends('start_datetime', 'end_datetime')
    def _compute_allocated_hours(self):
        """
        Calculates the allocated hours for a record based on the start_datetime and end_datetime fields.

        This method is a computed field logic that evaluates the difference between the start and end datetimes
        in seconds, and then converts it to hours. If either start_datetime or end_datetime is not set,
        the allocated hours are set to zero.

        Dependencies:
        - start_datetime: The starting timestamp for the record.
        - end_datetime: The ending timestamp for the record.

        Sets:
        - allocated_hours: The computed value representing the number of hours between start_datetime and end_datetime.
        """
        for record in self:
            if record.start_datetime and record.end_datetime:
                record.allocated_hours = (record.end_datetime - record.start_datetime).total_seconds() / 3600
            else:
                record.allocated_hours = 0.0

