from odoo import models,fields,api,_


class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_overtime = fields.Boolean(string="Enable Overtime")
    consider_buffer_time = fields.Boolean(string="Consider Buffer Time")
    buffer_time = fields.Float(string="Buffer Time")
    need_to_approve = fields.Boolean(string="Need to Approve")
    enable_inline_approval = fields.Boolean(string="Enable Overtime Inline Approval")
    enable_bulk_approval = fields.Boolean(string="Enable Overtime Bulk Approval")
    enable_pre_approval = fields.Boolean(string="Enable Overtime Pre Approval")
    deduct_late_check_in = fields.Boolean(string="Deduct Late Check In ?")
    consider_early_check_in = fields.Boolean(string="Consider Early Check In ?")
    roundup_overtime = fields.Boolean(string="Roundup Overtime ?")
    roundup_overtime_interval = fields.Integer(string="Roundup Overtime Interval(Minutes)")