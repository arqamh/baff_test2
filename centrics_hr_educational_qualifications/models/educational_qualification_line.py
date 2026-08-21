from odoo import models,fields,api,_


class EducationalQualificationLine(models.Model):
    _name = 'educational.qualification.line'
    _description = 'Educational Qualification Line'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    certification_level_id = fields.Many2one('certification.level', string="Certification Level")
    study_field = fields.Char(string="Study Field")
    school_university = fields.Char(string="School/University")
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")
