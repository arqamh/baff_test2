from odoo import models, fields, api, _


class HrAttendanceImportConfiguration(models.Model):
    _name = "hr.attendance.import.configuration"
    _description = "Attendance Import Configuration"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Configuration Name", help="Name of the configuration", readonly=True,
                       store=True, compute="_compute_name", tracking=True)
    field_id = fields.Many2one('ir.model.fields', string="Field", domain=[('model', '=', 'hr.employee')],
                               help="Select the field to be used for importing attendance", tracking=True)
    column_name = fields.Char(string="Capturing Column Name",
                              help="Enter the column name of the field selected above", tracking=True)
    check_in_column_name = fields.Char(string="Check-In Column Name",
                                       help="Enter the column name that needs to map with Check-In", tracking=True)
    check_out_column_name = fields.Char(string="Check-Out Column Name",
                                        help="Enter the column name that needs to map with Check-Out", tracking=True)
    file_type = fields.Selection([('csv', 'CSV'), ('xls', 'Excel')], string="File Type", default='csv',
                                 help="Select the file type to be imported")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_field_id', 'unique(field_id,file_type)', 'The selected field for importing attendance must be unique.'),
    ]

    @api.depends('field_id')
    def _compute_name(self):
        # Dynamically compute the name based on the selected field's description
        for record in self:
            if record.field_id:
                record.name = "Import Through" + " - " + record.field_id.field_description + " - " + record.file_type
            else:
                record.name = False
                
    
    
