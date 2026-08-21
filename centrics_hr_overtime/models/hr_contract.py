from odoo import models,fields,api,_

from odoo.exceptions import UserError


class HrContract(models.Model):
    _inherit = 'hr.contract'



    enable_overtime = fields.Boolean(string="Enable Overtime", related='company_id.enable_overtime')
    is_eligible_for_overtime = fields.Boolean(string="Is Eligible for Overtime")
    overtime_rate = fields.Float(string="Overtime Rate")

    overtime_template_id = fields.Many2one(
        'hr.overtime.template',
        string="Overtime Template",
        )

    @api.onchange('is_eligible_for_overtime')
    def onchange_is_eligible_for_overtime(self):
        """
        Updates the overtime template based on eligibility and employee job position.

        This function checks if an employee is eligible for overtime based on the `is_eligible_for_overtime`
        attribute. If eligible, it attempts to find a suitable overtime template that matches the employee's
        job position. If no such template is found, it defaults to a global template.

        Raises
        ------
        UserError
            If no employee is selected when the `is_eligible_for_overtime` flag is set.

        Parameters
        ----------
        self : object
            The instance of the object invoking the method, typically representing an employee's data.

        Attributes
        ----------
        is_eligible_for_overtime : bool
            Indicates whether an employee is eligible for overtime.
        employee_id : int
            The ID of the selected employee.
        overtime_template_id : int
            The ID of the applied overtime template.

        Notes
        -----
        This method makes use of the `hr.employee` and `hr.overtime.template` models. It first checks
        for a job-position-specific overtime template and applies it if found. If no such template exists,
        it assigns a global overtime template as a fallback option.
        """
        if self.is_eligible_for_overtime:
            employee_id = self.employee_id.id
            if not employee_id:
                raise UserError(_("Please select an employee."))

            employee = self.env['hr.employee'].browse(employee_id)
            HrOvertimeTemplate = self.env['hr.overtime.template']
            job = self.job_id

            # Try to find a template matching the employee's job position
            template = HrOvertimeTemplate.search([
                ('job_position_ids', 'in', job.id)
            ], limit=1)

            if template:
                self.overtime_template_id = template.id
            else:
                # Fallback to global template
                self.overtime_template_id = HrOvertimeTemplate.search([('is_global', '=', True)], limit=1).id