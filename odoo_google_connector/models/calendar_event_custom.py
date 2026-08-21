from odoo import models, fields, api
from . import calendar_service
from . import constants
from . import utils
import logging


class CalendarEventExtend(models.Model):
    _inherit = constants.CALENDAR_EVENT_MODEL

    gc_id = fields.Char(string="Google-ID", readonly=True, copy=False, default=None)
    gc_etag = fields.Char(string="Google-eTag", readonly=True, copy=False, default=None)
    status = fields.Selection(
        [('confirmed', 'Confirmed'), ('tentative', 'Tentative'), ('cancelled', 'Cancelled')],
        string="Status", default="confirmed")
    organizer_id = fields.Many2one(constants.RES_PARTNER_MODEL, string="Organizer")
    meet_link = fields.Char(string="Meeting Link", readonly=True)
    meet_code = fields.Char(string="Meeting Code", readonly=True)

    @api.model_create_multi
    def create(self, values):
        create_rec = super(CalendarEventExtend, self).create(values)

        _logging = logging.getLogger(__name__)
        db_access_tokens = utils.get_db_token(self_env=self.env)
        if db_access_tokens and len(db_access_tokens) > 0:
            _calendar_sev = calendar_service.CalenderService(
                gl_access_token=db_access_tokens[0], self_env=self.env, default_profile=db_access_tokens[1])
            sr_resp = _calendar_sev.create_event(l2s_event=create_rec)
            if sr_resp["err_status"]:
                _logging.error("Create/Update Event Error: " + sr_resp["response"])
        else:
            _logging.error("Oops, Google credentials are not found. Please try again")

        return create_rec

    def write(self, values, addons=None):
        if 'gc_id' in values:
            chk_flag, chk_uniq_id = utils.validate_gc_id_value(
                self_env=self.env, res_model=constants.CALENDAR_EVENT_MODEL, res_id=self.id, new_gc_id=values["gc_id"])
            if chk_flag or chk_uniq_id:
                del values["gc_id"]
        save_rec = super(CalendarEventExtend, self).write(values)

        _logging = logging.getLogger(__name__)
        if addons is None:
            local_update_record = self.env[constants.CALENDAR_EVENT_MODEL].search([('id', '=', self.id)])
            db_access_tokens = utils.get_db_token(self_env=self.env)
            if db_access_tokens and len(db_access_tokens) > 0:
                _calendar_sev = calendar_service.CalenderService(
                    gl_access_token=db_access_tokens[0], self_env=self.env, default_profile=db_access_tokens[1])
                sr_resp = _calendar_sev.create_event(l2s_event=local_update_record[0])
                if sr_resp["err_status"]:
                    _logging.error("Create/Update Event Error: " + sr_resp["response"])
            else:
                _logging.error("Oops, Google credentials are not found. Please try again")

        return save_rec

    @api.model
    def unlink(self, values=None):
        unlink_rec = super(CalendarEventExtend, self).unlink()

        _logging = logging.getLogger(__name__)
        if values:
            for cid in values:
                try:
                    ref_event = self.env[constants.CALENDAR_EVENT_MODEL].search([('id', '=', cid)])
                    if ref_event and len(ref_event) > 0 and ref_event.gc_id:
                        db_access_tokens = utils.get_db_token(self_env=self.env)
                        if db_access_tokens and len(db_access_tokens) > 0:
                            _calendar_sev = calendar_service.CalenderService(
                                gl_access_token=db_access_tokens[0], self_env=self.env, default_profile=db_access_tokens[1])
                            sr_resp = _calendar_sev.delete_event(ref_event[0].gc_id)
                            if sr_resp["err_status"]:
                                _logging.error("Delete Event Error: " + sr_resp["response"])

                    self.env.cr.execute('delete from ' + constants.CALENDAR_EVENT_STASH_MODEL + ' where id=' + str(cid))
                except Exception as ex:
                    _logging.exception("Oops, unable to delete database contact: " + str(ex))

        return unlink_rec
