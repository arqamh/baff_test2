from odoo import models,fields,api,_


class OnboardingChecklistItem(models.Model):
    _name = 'onboarding.checklist.item'
    _description = 'Onboarding Checklist Item'

    name = fields.Char(string="Checklist Item")
    need_to_map_with_job_position = fields.Boolean(string="Need to Map with Job Position")
    job_id = fields.Many2one('hr.job', string="Job Position")
    item_type_id = fields.Many2one('onboarding.checklist.item.type', string="Checklist Item Type")
    action_to_do = fields.Selection([('document_upload','Document Upload'),('schedule_meeting','Schedule Meeting')], related='item_type_id.action_to_do', string="Action to Do")

