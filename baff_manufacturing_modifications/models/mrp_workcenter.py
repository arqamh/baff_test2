from odoo import api, models, fields


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"
    _order = "sequence,id"

    employee_lines = fields.One2many('allocated.employee.lines', 'workceter_id', string="Employee Lines", copy=False)

    @api.onchange('employee_lines')
    def _onchange_employee_lines(self):
        """This function is to update employee_ids field when the employee lines are getting updated"""
        if self.employee_lines:
            employee_ids = self.employee_lines.mapped('employee_id')
            self.employee_ids = [(6, 0, employee_ids.ids)]
        else:
            self.employee_ids = [(5, 0, 0)]

    @api.model
    def create(self, vals):
        """ Overriding create method to add employee lines"""
        result = super(MrpWorkcenter, self).create(vals)
        if 'employee_lines' in vals:
            employee_ids = self.employee_lines.mapped('employee_id')
            vals['employee_ids'] = [(6, 0, employee_ids.ids)] if employee_ids else [(5, 0, 0)]

        if result.employee_ids and vals.get('employee_ids'):
            lines = [(5, 0, 0)]
            for employee in result.employee_ids:
                values = {
                    'sequence_no': 1,
                    'employee_id': employee.id
                }
                lines.append((0, 0, values))
            result.employee_lines = lines

        return result

    def write(self, vals):
        """ Overriding write method to add employee lines"""
        result = super(MrpWorkcenter, self).write(vals)
        if self.employee_ids and vals.get('employee_ids'):
            lines = [(5, 0, 0)]
            count = 1
            for employee in self.employee_ids:
                values = {
                    'sequence': count,
                    'employee_id': employee.id
                }
                lines.append((0, 0, values))
                count += 1
            self.employee_lines = lines

        return result


class AllocatedEmployeeLines(models.Model):
    _name = 'allocated.employee.lines'
    _description = "Allocated Employee Lines"
    _order = "sequence,id"

    workceter_id = fields.Many2one('mrp.workcenter', string="Employee Lines", copy=False)
    sequence = fields.Integer(string="Sequence")
    employee_id = fields.Many2one('hr.employee', string="Employee")
