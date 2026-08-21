from odoo import models, fields, api
from . import task_service
from . import constants
from . import utils
import logging


class MailActivityExtend(models.Model):
    _inherit = constants.MAIL_ACTIVITY_MODEL

    gc_id = fields.Char(string='Google-ID', copy=False, readonly=True, default=None)
    gc_etag = fields.Char(string='Google-eTag', copy=False, readonly=True, default=None)

    def write(self, values, addons=None):
        if 'gc_id' in values:
            chk_flag, chk_uniq_id = utils.validate_gc_id_value(
                self_env=self.env, res_model=constants.MAIL_ACTIVITY_MODEL, res_id=self.id, new_gc_id=values["gc_id"])
            if chk_flag or chk_uniq_id:
                del values["gc_id"]
        _db_updated_record = super(MailActivityExtend, self).write(values)

        _logging = logging.getLogger(__name__)
        try:
            if addons is None:
                local_update_record = self.env[constants.MAIL_ACTIVITY_MODEL].search([('id', '=', self.id)])
                db_access_tokens = utils.get_db_token(self_env=self.env)
                if db_access_tokens and len(db_access_tokens) > 0:
                    _task = task_service.TaskService(
                        gl_access_token=db_access_tokens[0], default_env=self.env, default_profile=db_access_tokens[1])
                    sr_resp = _task.create_task(l2s_task=local_update_record[0])
                    if sr_resp["err_status"]:
                        _logging.error("Create/Update Task Error: " + sr_resp["response"])
                else:
                    _logging.error("Oops, Google credentials are not found. Please try again")
        except Exception as ex:
            _logging.exception("Oops, Google Task Updation Exception: " + str(ex))

        return _db_updated_record

    @api.model
    def unlink(self, values=None):
        _logging = logging.getLogger(__name__)

        if values:
            for cid in values:
                try:
                    ref_task = self.env[constants.MAIL_ACTIVITY_MODEL].search([('id', '=', cid)])
                    if ref_task and len(ref_task) > 0 and ref_task[0].gc_id:
                        db_access_tokens = utils.get_db_token(self_env=self.env)
                        if db_access_tokens and len(db_access_tokens) > 0:
                            _task = task_service.TaskService(
                                gl_access_token=db_access_tokens[0], default_env=self.env,
                                default_profile=db_access_tokens[1])
                            sr_resp = _task.delete_task_by_id(ref_task[0].gc_id)
                            if sr_resp["err_status"]:
                                _logging.error("Delete Task Error: " + str(sr_resp["response"]))

                    self.env.cr.execute('delete from ' + constants.MAIL_ACTIVITY_STASH_MODEL + ' where id=' + str(cid))
                except Exception as ex:
                    _logging.exception("Oops, unable to delete database contact: " + str(ex))

        return super(MailActivityExtend, self).unlink()

    @api.model
    def action_close_dialog(self, values):
        create_rec = super(MailActivityExtend, self).action_close_dialog()

        _logging = logging.getLogger(__name__)

        ref_task = self.env[constants.MAIL_ACTIVITY_MODEL].search([('id', '=', values[0])])
        if ref_task and len(ref_task) > 0:
            db_access_tokens = utils.get_db_token(self_env=self.env)
            if db_access_tokens and len(db_access_tokens) > 0:
                _task = task_service.TaskService(
                    gl_access_token=db_access_tokens[0], default_env=self.env,
                    default_profile=db_access_tokens[1])
                sr_resp = _task.create_task(l2s_task=ref_task[0])
                if sr_resp["err_status"]:
                    _logging.error("Create Task Error: " + str(sr_resp["response"]))
            else:
                _logging.error("Create Task Error: Oops, credentials not found")
        else:
            _logging.error("Create Task Error: Oops, schedule activity is not found")
        return create_rec

    def action_feedback(self, feedback=None, attachment_ids=None):
        _logging = logging.getLogger(__name__)

        ref_task = self.env[constants.MAIL_ACTIVITY_MODEL].search([('id', '=', self.id)])
        if ref_task and len(ref_task) > 0 and ref_task[0].gc_id:
            db_access_tokens = utils.get_db_token(self_env=self.env)
            if db_access_tokens and len(db_access_tokens) > 0:
                _task = task_service.TaskService(
                    gl_access_token=db_access_tokens[0], default_env=self.env,
                    default_profile=db_access_tokens[1])
                sr_resp = _task.done_task_by_id(db_task=ref_task[0])
                if sr_resp["err_status"]:
                    _logging.error("Done Task Error: " + str(sr_resp["response"]))
            else:
                _logging.error("Done Task Error: Oops, credentials not found")
        else:
            _logging.error("Done Task Error: Oops, schedule activity is not found")

        try:
            return super(MailActivityExtend, self).action_feedback(feedback, attachment_ids)
        except:
            return self.id
