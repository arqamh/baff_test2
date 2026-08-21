from odoo import models, fields, api
from . import calendar_service
from . import people_service
from . import gmail_service
from . import task_service
from . import connection
from . import constants
from datetime import *
import logging


class GoogleConnector(models.Model):
    _name = constants.GOOGLE_CONNECTOR_MODEL
    _description = constants.GOOGLE_CONNECTOR_MODEL_DESC

    import_contact = fields.Boolean(default=False)
    export_contact = fields.Boolean(default=False)
    import_calendar = fields.Boolean(default=False)
    export_calendar = fields.Boolean(default=False)

    import_task = fields.Boolean(default=False)
    export_task = fields.Boolean(default=False)
    import_email = fields.Boolean(default=False)

    import_data_stats = fields.One2many(constants.GOOGLE_IMPORT_STATS_MODEL, inverse_name="connector")
    export_data_stats = fields.One2many(constants.GOOGLE_EXPORT_STATS_MODEL, inverse_name="connector")
    custom_from_datetime = fields.Datetime(
        'From Date', default=lambda self: (fields.datetime.now() - timedelta(hours=1)))
    custom_to_datetime = fields.Datetime(
        'To Date', default=lambda self: (fields.datetime.now() + timedelta(hours=1)))

    def synchronize(self):
        _logging = logging.getLogger(__name__)

        pop_up_message, date_error_chk = "", False
        import_chk_status, export_chk_status = False, False

        new_imp_contact, new_imp_calendar, new_imp_task, new_imp_mail = 0, 0, 0, 0
        upd_imp_contact, upd_imp_calendar, upd_imp_task, upd_imp_mail = 0, 0, 0, 0
        new_exp_contact, new_exp_calendar, new_exp_task = 0, 0, 0
        upd_exp_contact, upd_exp_calendar, upd_exp_task = 0, 0, 0

        try:
            if self.custom_from_datetime > self.custom_to_datetime:
                date_error_chk = True

            if not date_error_chk:
                credentials = self.env[constants.GOOGLE_CREDENTIALS_MODEL].get_google_credentials()
                if constants.RESPONSE_ERROR_KEY not in credentials and \
                        constants.RESPONSE_ERR_MESSAGE_KEY not in credentials:
                    connect = connection.Connection(google_app_cred=credentials, default_env=self.env)
                    conn_response = connect.get_msv_access_token()
                    if not conn_response["err_status"]:

                        if self.import_contact or self.export_contact:
                            _contacts = people_service.PeopleService(
                                gl_access_token=conn_response["response"], default_env=self.env,
                                initial_date=self.custom_from_datetime, end_date=self.custom_to_datetime)

                            if self.import_contact:
                                contact_response = _contacts.import_contacts()
                                if not contact_response["err_status"]:
                                    new_imp_contact += contact_response["success"]
                                    upd_imp_contact += contact_response["updated"]
                            if self.export_contact:
                                contact_response = _contacts.export_contacts()
                                if not contact_response["err_status"]:
                                    new_exp_contact += contact_response["success"]
                                    upd_exp_contact += contact_response["updated"]

                        if self.import_calendar or self.export_calendar:
                            _calendar = calendar_service.CalenderService(
                                gl_access_token=conn_response["response"], self_env=self.env,
                                default_profile=conn_response["addons"], initial_date=self.custom_from_datetime,
                                end_date=self.custom_to_datetime)

                            if self.import_calendar:
                                calendar_response = _calendar.import_events()
                                if not calendar_response["err_status"]:
                                    new_imp_calendar += calendar_response["success"]
                                    upd_imp_calendar += calendar_response["updated"]
                            if self.export_calendar:
                                calendar_response = _calendar.export_events()
                                if not calendar_response["err_status"]:
                                    new_exp_calendar += calendar_response["success"]
                                    upd_exp_calendar += calendar_response["updated"]

                        if self.import_task or self.export_task:
                            _task = task_service.TaskService(
                                gl_access_token=conn_response["response"], default_env=self.env,
                                default_profile=conn_response["addons"], initial_date=self.custom_from_datetime,
                                end_date=self.custom_to_datetime)

                            if self.import_task:
                                task_response = _task.import_tasks()
                                if not task_response["err_status"]:
                                    new_imp_task += task_response["success"]
                                    upd_imp_task += task_response["updated"]
                            if self.export_task:
                                task_response = _task.export_tasks()
                                if not task_response["err_status"]:
                                    new_exp_task += task_response["success"]
                                    upd_exp_task += task_response["updated"]

                        if self.import_email:
                            _gmail = gmail_service.GMailService(
                                gl_access_token=conn_response["response"], self_env=self.env,
                                initial_date=self.custom_from_datetime, end_date=self.custom_to_datetime,
                                default_email=None)
                            gmail_response = _gmail.import_mails()
                            if not gmail_response["err_status"]:
                                new_imp_mail += gmail_response["success"]
                                upd_imp_mail += gmail_response["updated"]

                        if self.import_contact or self.import_calendar or self.import_email or self.import_task:
                            if new_imp_contact or new_imp_calendar or new_imp_task or new_imp_mail or \
                                    upd_imp_contact or upd_imp_calendar or upd_imp_task or upd_imp_mail:
                                self.env[constants.GOOGLE_IMPORT_STATS_MODEL].create({
                                    'new_contact': new_imp_contact,
                                    'new_calendar': new_imp_calendar,
                                    'new_task': new_imp_task,
                                    'new_email': new_imp_mail,
                                    'upd_contact': upd_imp_contact,
                                    'upd_calendar': upd_imp_calendar,
                                    'upd_task': upd_imp_task,
                                    'upd_email': upd_imp_mail,
                                    'connector': self.id
                                })
                            if pop_up_message == "":
                                pop_up_message += constants.SYNC_PROCESS_MSG
                            import_chk_status = True

                        if self.export_contact or self.export_calendar or self.export_task:
                            if new_exp_task or new_exp_calendar or new_exp_contact or upd_exp_contact or \
                                    upd_exp_calendar or upd_exp_task:
                                self.env[constants.GOOGLE_EXPORT_STATS_MODEL].create({
                                    'new_contact': new_imp_contact,
                                    'new_calendar': new_imp_calendar,
                                    'new_task': new_imp_task,
                                    'upd_contact': upd_exp_contact,
                                    'upd_calendar': upd_exp_calendar,
                                    'upd_task': upd_exp_task,
                                    'connector': self.id
                                })
                            if pop_up_message == "":
                                pop_up_message += constants.SYNC_PROCESS_MSG
                            export_chk_status = True

                        if not export_chk_status and not import_chk_status:
                            pop_up_message = constants.NO_OPT_SECTION_ERR
                    else:
                        pop_up_message += conn_response["response"]
                else:
                    pop_up_message += credentials["err_message"]
                    _logging.info("Error while Sync: " + credentials["error"])
            else:
                pop_up_message += constants.INVALID_DATE_RANGES
        except Exception as ex:
            _logging.exception("Google Sync Exception: " + str(ex))
            pop_up_message += constants.SYNC_REQ_ERROR
        return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "System Notification",
                    'message': pop_up_message,
                    'sticky': False,
                }
            }

    def import_history_action(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': constants.GOOGLE_IMPORT_STATS_MODEL,
            'view_mode': 'tree',
            'context': {'no_breadcrumbs': True}
        }

    def export_history_action(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': constants.GOOGLE_EXPORT_STATS_MODEL,
            'view_mode': 'tree',
            'context': {'no_breadcrumbs': True}
        }
