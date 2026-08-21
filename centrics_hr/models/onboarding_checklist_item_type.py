from odoo import models,fields,api,_


class OnboardingChecklistItemType(models.Model):
    _name = 'onboarding.checklist.item.type'
    _description = 'Onboarding Checklist Item Type'

    name = fields.Char(string="Checklist Item Type")
    action_to_do = fields.Selection([('document_upload','Document Upload'),('schedule_meeting','Schedule Meeting')])