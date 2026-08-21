# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BufferTimeConfiguration(models.Model):
    _name = 'buffer.time.configuration'
    _description = 'Buffer Time Configuration'

    employee_type = fields.Selection(
        selection=lambda self: self.env['hr.employee'].fields_get(['employee_type'])['employee_type']['selection'],
        string='Employee Type', required=True)
    avoid_buffer_time = fields.Boolean(string='Avoid Buffer Time', default=False)
    buffer_time = fields.Integer(string='Buffer Time (Minutes)', required=True)

    @api.constrains('buffer_time', 'avoid_buffer_time')
    def _check_buffer_time(self):
        for record in self:
            if not record.avoid_buffer_time and record.buffer_time <= 0:
                raise ValidationError(_('Buffer Time must be greater than zero if Avoid Buffer Time is not enabled.'))

    _sql_constraints = [
        ('unique_employee_type', 'unique(employee_type)', 'A record for this Employee Type already exists.')
    ]
