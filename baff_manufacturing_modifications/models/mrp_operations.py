from odoo import models, fields, api
from odoo.exceptions import Warning
from odoo.tools import ustr
import base64


class MrpOperations(models.Model):
    _inherit = 'mrp.routing.workcenter'

    image = fields.Binary(string="Image")
    worksheet_type = fields.Selection(selection_add=[('image', 'Image')])
    operation_duration_hrs = fields.Float(string="Default Duration ")

    @api.onchange('operation_duration_hrs')
    def _onchange_operation_duration_hrs(self):
        """ Rounding duration in work operation """
        for record in self:
            if record.operation_duration_hrs:
                time_minutes = record.operation_duration_hrs * 60
                time = round(time_minutes)
                time = time / 30
                if time == 0.5:
                    time += 0.1
                rounded_time = round(time)
                record.time_cycle_manual = rounded_time * 30
                record.operation_duration_hrs = (rounded_time * 30) / 60
            else:
                record.time_cycle_manual = 0.0

    def attach_image_to_operation(self, attachment):
        # image as an attachment to the worksheets
        operation_id = self.env['mrp.routing.workcenter'].search([('id', '=', self.id)])
        if operation_id:
            attachment_id = self.env['ir.attachment'].create({
                'name': attachment.filename,
                'datas_fname': attachment.filename,
                'type': 'binary',
                'datas': base64.b64encode(attachment.read()),
                'res_model': 'mrp.routing.workcenter',
                'res_id': operation_id.id,
            })
            operation_id.write({'attachment_ids': [(4, attachment_id.id)]})

    def _write(self, vals):
        # update the record in the model
        res = super(MrpOperations, self).write(vals)
        if vals.get('image'):
            attachment = self.env['ir.attachment'].search([('name', '=', vals.get('image_name'))])
            for operation in self.operation_ids:
                operation.attach_image_to_operation(attachment)
        return res
