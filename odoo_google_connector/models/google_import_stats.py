from odoo import models, fields, api
from . import constants


class GoogleImportStats(models.Model):
    _name = constants.GOOGLE_IMPORT_STATS_MODEL
    _description = constants.GOOGLE_IMPORT_STATS_MODEL_DESC

    connector = fields.Many2one(constants.GOOGLE_CONNECTOR_MODEL)
    new_contact = fields.Integer()
    new_calendar = fields.Integer()
    new_email = fields.Integer()
    new_task = fields.Integer()
    upd_contact = fields.Integer()
    upd_calendar = fields.Integer()
    upd_email = fields.Integer()
    upd_task = fields.Integer()
