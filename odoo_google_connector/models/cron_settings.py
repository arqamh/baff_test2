from odoo import models, fields, api
from . import calendar_service
from . import people_service
from . import gdrive_service
from . import gmail_service
from . import task_service
from . import constants
from . import utils
import logging
import base64


class GoogleCronSettings(models.Model):
    _name = constants.GOOGLE_CRON_SETTINGS_MODEL
    _description = constants.GOOGLE_CRON_SETTINGS_MODEL_DESC

    ####################################################################################################
    # ################################      For Contact Options      ###################################
    ####################################################################################################

    is_auto_import_contact = fields.Boolean(default=lambda self: self.get_auto_import_status_contact())
    import_interval_num_contact = fields.Integer(default=lambda self: self.get_import_interval_num_contact())
    import_call_num_contact = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_import_call_num_contact())
    import_interval_type_contact = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_import_interval_type_contact())

    is_auto_export_contact = fields.Boolean(default=lambda self: self.get_auto_export_status_contact())
    export_interval_num_contact = fields.Integer(default=lambda self: self.get_export_interval_num_contact())
    export_call_num_contact = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_export_call_num_contact())
    export_interval_type_contact = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_export_interval_type_contact())

    ####################################################################################################
    # ################################      For Calendar Options     ###################################
    ####################################################################################################

    is_auto_import_calendar = fields.Boolean(default=lambda self: self.get_auto_import_status_calendar())
    import_interval_num_calendar = fields.Integer(default=lambda self: self.get_import_interval_num_calendar())
    import_call_num_calendar = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_import_call_num_calendar())
    import_interval_type_calendar = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_import_interval_type_calendar())

    is_auto_export_calendar = fields.Boolean(default=lambda self: self.get_auto_export_status_calendar())
    export_interval_num_calendar = fields.Integer(default=lambda self: self.get_export_interval_num_calendar())
    export_call_num_calendar = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_export_call_num_calendar())
    export_interval_type_calendar = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_export_interval_type_calendar())

    ####################################################################################################
    # #################################       For Tasks Options      ###################################
    ####################################################################################################

    is_auto_import_task = fields.Boolean(default=lambda self: self.get_auto_import_status_task())
    import_interval_num_task = fields.Integer(default=lambda self: self.get_import_interval_num_task())
    import_call_num_task = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_import_call_num_task())
    import_interval_type_task = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_import_interval_type_task())

    is_auto_export_task = fields.Boolean(default=lambda self: self.get_auto_export_status_task())
    export_interval_num_task = fields.Integer(default=lambda self: self.get_export_interval_num_task())
    export_call_num_task = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_export_call_num_task())
    export_interval_type_task = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_export_interval_type_task())

    ####################################################################################################
    # ##################################      For GDrive Options     ###################################
    ####################################################################################################

    is_auto_import_drive = fields.Boolean(default=lambda self: self.get_auto_import_status_drive())
    import_interval_num_drive = fields.Integer(default=lambda self: self.get_import_interval_num_drive())
    import_call_num_drive = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_import_call_num_drive())
    import_interval_type_drive = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_import_interval_type_drive())

    is_auto_export_drive = fields.Boolean(default=lambda self: self.get_auto_export_status_drive())
    export_interval_num_drive = fields.Integer(default=lambda self: self.get_export_interval_num_drive())
    export_call_num_drive = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_export_call_num_drive())
    export_interval_type_drive = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_export_interval_type_drive())

    ####################################################################################################
    # ##################################      For GMail Options      ###################################
    ####################################################################################################

    is_auto_import_mail = fields.Boolean(default=lambda self: self.get_auto_import_status_mail())
    import_interval_num_mail = fields.Integer(default=lambda self: self.get_import_interval_num_mail())
    import_call_num_mail = fields.Selection(
        [('1', 'One Time'), ('-1', 'Unlimited Time')], default=lambda self: self.get_import_call_num_mail())
    import_interval_type_mail = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days')],
        default=lambda self: self.get_import_interval_type_mail())

    ####################################################################################################
    # ###########################      For Default Function Operations     #############################
    ####################################################################################################

    def import_contacts(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _contact = people_service.PeopleService(gl_access_token=db_ref_token[0], default_env=self.env)
            contact_response = _contact.import_contacts()
            if not contact_response["err_status"]:
                new_imp_contact = contact_response["success"]
                upd_imp_contact = contact_response["updated"]
                if new_imp_contact or upd_imp_contact:
                    self.env[constants.GOOGLE_IMPORT_STATS_MODEL].create({
                        'new_contact': new_imp_contact, 'upd_contact': upd_imp_contact
                    })
            else:
                _logging.error("Google Contact Import Error: " + contact_response["response"])
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    def export_contacts(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _contact = people_service.PeopleService(gl_access_token=db_ref_token[0], default_env=self.env)
            contact_response = _contact.export_contacts()
            if not contact_response["err_status"]:
                new_imp_contact = contact_response["success"]
                upd_imp_contact = contact_response["updated"]
                if new_imp_contact or upd_imp_contact:
                    self.env[constants.GOOGLE_EXPORT_STATS_MODEL].create({
                        'new_contact': new_imp_contact, 'upd_contact': upd_imp_contact
                    })
            else:
                _logging.error("Google Contact Export Error: " + contact_response["response"])
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    def import_calendar_events(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _calendar = calendar_service.CalenderService(
                gl_access_token=db_ref_token[0], self_env=self.env, default_profile=db_ref_token[1])
            calendar_response = _calendar.import_events()
            if not calendar_response["err_status"]:
                new_imp_calendar = calendar_response["success"]
                upd_imp_calendar = calendar_response["updated"]
                if new_imp_calendar or upd_imp_calendar:
                    self.env[constants.GOOGLE_IMPORT_STATS_MODEL].create({
                        'new_calendar': new_imp_calendar, 'upd_calendar': upd_imp_calendar
                    })
            else:
                _logging.error("Google Calendar Event Import Error: " + calendar_response["response"])
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    def export_calendar_events(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _calendar = calendar_service.CalenderService(
                gl_access_token=db_ref_token[0], self_env=self.env, default_profile=db_ref_token[1])
            calendar_response = _calendar.export_events()
            if not calendar_response["err_status"]:
                new_imp_calendar = calendar_response["success"]
                upd_imp_calendar = calendar_response["updated"]
                if new_imp_calendar or upd_imp_calendar:
                    self.env[constants.GOOGLE_EXPORT_STATS_MODEL].create({
                        'new_calendar': new_imp_calendar, 'upd_calendar': upd_imp_calendar
                    })
            else:
                _logging.error("Google Calendar Event Export Error: " + calendar_response["response"])
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    def import_tasks(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _task = task_service.TaskService(
                gl_access_token=db_ref_token[0], default_env=self.env, default_profile=db_ref_token[1])
            task_response = _task.import_tasks()
            if not task_response["err_status"]:
                new_imp_task = task_response["success"]
                upd_imp_task = task_response["updated"]
                if new_imp_task or upd_imp_task:
                    self.env[constants.GOOGLE_IMPORT_STATS_MODEL].create({
                        'new_task': new_imp_task, 'upd_task': upd_imp_task
                    })
            else:
                _logging.error("Google Tasks Import Error: " + task_response["response"])
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    def export_tasks(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _task = task_service.TaskService(
                gl_access_token=db_ref_token[0], default_env=self.env, default_profile=db_ref_token[1])
            task_response = _task.export_tasks()
            if not task_response["err_status"]:
                new_imp_task = task_response["success"]
                upd_imp_task = task_response["updated"]
                if new_imp_task or upd_imp_task:
                    self.env[constants.GOOGLE_EXPORT_STATS_MODEL].create({
                        'new_task': new_imp_task, 'upd_task': upd_imp_task
                    })
            else:
                _logging.error("Google Tasks Export Error: " + task_response["response"])
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    def import_drive(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _drive = gdrive_service.GDriveService(gl_access_token=db_ref_token[0], self_env=self.env)
            for partner in self.env[constants.RES_PARTNER_MODEL].search([('drive_sync', '=', True)]):
                drive_response = _drive.import_gdrive_documents(res_info=partner)
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    def export_drive(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _drive = gdrive_service.GDriveService(gl_access_token=db_ref_token[0], self_env=self.env)
            for partner in self.env[constants.RES_PARTNER_MODEL].search([('drive_sync', '=', True)]):
                partner_file_records = {'res_info': partner, 'files': []}
                for attachment in partner.google_attachment_ids:
                    try:
                        decoded_data = base64.b64decode(attachment.datas)
                        partner_file_records["files"].append({
                            "id": attachment.id,
                            "name": attachment.name,
                            "mimetype": attachment.mimetype,
                            "db_datas": decoded_data
                        })
                    except Exception as ex:
                        _logging.exception("Log >> Export OPT, File attachment Except: " + str(ex))
                drive_response = _drive.export_gdrive_documents(res_data=partner_file_records)
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    def import_mails(self):
        _logging = logging.getLogger(__name__)

        db_ref_token = utils.get_db_token(self_env=self.env)
        if db_ref_token and len(db_ref_token) > 0:
            _gmail = gmail_service.GMailService(gl_access_token=db_ref_token[0], self_env=self.env)
            mail_response = _gmail.import_mails()
            if not mail_response["err_status"]:
                new_imp_mail = mail_response["success"]
                upd_imp_mail = mail_response["updated"]
                if new_imp_mail or upd_imp_mail:
                    self.env[constants.GOOGLE_IMPORT_STATS_MODEL].create({
                        'new_email': new_imp_mail, 'upd_email': upd_imp_mail
                    })
            else:
                _logging.error("GMail Import Error: " + mail_response["response"])
        else:
            _logging.error(constants.GL_CONN_CRED_ACS_EXCEPT)

    ####################################################################################################
    # ###########################      End Default Function Operations     #############################
    ####################################################################################################

    def write(self, values):
        return super(GoogleCronSettings, self).write(values)

    ####################################################################################################
    # ###########################      Cron Import Function Operations     #############################
    ####################################################################################################

    def update_import_cron_contact(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_IMPORT_CONTACTS_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([
            ('name', '=', constants.GOOGLE_IMPORT_CONTACTS_DEF)
        ])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["import_call_num_contact"],
                'active': data["is_auto_import_contact"],
                'interval_number': data["import_interval_num_contact"],
                'interval_type': data["import_interval_type_contact"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_IMPORT_CONTACTS_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.import_contacts()',
                'numbercall': data["import_call_num_contact"],
                'active': data["is_auto_import_contact"],
                'interval_number': data["import_interval_num_contact"],
                'interval_type': data["import_interval_type_contact"],
                'priority': 2,
                'doall': 1
            })

    def update_import_cron_calendar(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_IMPORT_CALENDAR_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([
            ('name', '=', constants.GOOGLE_IMPORT_CALENDAR_DEF)
        ])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["import_call_num_calendar"],
                'active': data["is_auto_import_calendar"],
                'interval_number': data["import_interval_num_calendar"],
                'interval_type': data["import_interval_type_calendar"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_IMPORT_CALENDAR_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.import_calendar_events()',
                'numbercall': data["import_call_num_calendar"],
                'active': data["is_auto_import_calendar"],
                'interval_number': data["import_interval_num_calendar"],
                'interval_type': data["import_interval_type_calendar"],
                'priority': 2,
                'doall': 1
            })

    def update_import_cron_task(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_IMPORT_TASKS_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([('name', '=', constants.GOOGLE_IMPORT_TASKS_DEF)])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["import_call_num_task"],
                'active': data["is_auto_import_task"],
                'interval_number': data["import_interval_num_task"],
                'interval_type': data["import_interval_type_task"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_IMPORT_TASKS_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.import_tasks()',
                'numbercall': data["import_call_num_task"],
                'active': data["is_auto_import_task"],
                'interval_number': data["import_interval_num_task"],
                'interval_type': data["import_interval_type_task"],
                'priority': 2,
                'doall': 1
            })

    def update_import_cron_drive(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_IMPORT_DRIVE_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([('name', '=', constants.GOOGLE_IMPORT_DRIVE_DEF)])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["import_call_num_drive"],
                'active': data["is_auto_import_drive"],
                'interval_number': data["import_interval_num_drive"],
                'interval_type': data["import_interval_type_drive"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_IMPORT_DRIVE_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.import_drive()',
                'numbercall': data["import_call_num_drive"],
                'active': data["is_auto_import_drive"],
                'interval_number': data["import_interval_num_drive"],
                'interval_type': data["import_interval_type_drive"],
                'priority': 2,
                'doall': 1
            })

    def update_import_cron_mail(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_IMPORT_MAILS_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([('name', '=', constants.GOOGLE_IMPORT_MAILS_DEF)])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["import_call_num_mail"],
                'active': data["is_auto_import_mail"],
                'interval_number': data["import_interval_num_mail"],
                'interval_type': data["import_interval_type_mail"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_IMPORT_MAILS_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.import_mails()',
                'numbercall': data["import_call_num_mail"],
                'active': data["is_auto_import_mail"],
                'interval_number': data["import_interval_num_mail"],
                'interval_type': data["import_interval_type_mail"],
                'priority': 2,
                'doall': 1
            })

    ####################################################################################################
    # ###########################      Cron Export Function Operations     #############################
    ####################################################################################################

    def update_export_cron_contact(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_EXPORT_CONTACTS_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([
            ('name', '=', constants.GOOGLE_EXPORT_CONTACTS_DEF)
        ])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["export_call_num_contact"],
                'active': data["is_auto_export_contact"],
                'interval_number': data["export_interval_num_contact"],
                'interval_type': data["export_interval_type_contact"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_EXPORT_CONTACTS_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.export_contacts()',
                'numbercall': data["export_call_num_contact"],
                'active': data["is_auto_export_contact"],
                'interval_number': data["export_interval_num_contact"],
                'interval_type': data["export_interval_type_contact"],
                'priority': 2,
                'doall': 1
            })

    def update_export_cron_calendar(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_EXPORT_CALENDAR_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([
            ('name', '=', constants.GOOGLE_EXPORT_CALENDAR_DEF)
        ])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["export_call_num_calendar"],
                'active': data["is_auto_export_calendar"],
                'interval_number': data["export_interval_num_calendar"],
                'interval_type': data["export_interval_type_calendar"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_EXPORT_CALENDAR_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.export_calendar_events()',
                'numbercall': data["export_call_num_calendar"],
                'active': data["is_auto_export_calendar"],
                'interval_number': data["export_interval_num_calendar"],
                'interval_type': data["export_interval_type_calendar"],
                'priority': 2,
                'doall': 1
            })

    def update_export_cron_task(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_EXPORT_TASKS_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([('name', '=', constants.GOOGLE_EXPORT_TASKS_DEF)])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["export_call_num_task"],
                'active': data["is_auto_export_task"],
                'interval_number': data["export_interval_num_task"],
                'interval_type': data["export_interval_type_task"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_EXPORT_TASKS_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.export_tasks()',
                'numbercall': data["export_call_num_task"],
                'active': data["is_auto_export_task"],
                'interval_number': data["export_interval_num_task"],
                'interval_type': data["export_interval_type_task"],
                'priority': 2,
                'doall': 1
            })

    def update_export_cron_drive(self, data):
        _logging = logging.getLogger(__name__)

        delete_query = "delete from {0} where \"cron_name\"='{{\"{1}\":\"{2}\"}}'::jsonb;".format(
            constants.IR_CRON_STASH_MODEL, self.env.user.company_id.partner_id.lang,
            constants.GOOGLE_EXPORT_DRIVE_DEF
        )
        self.env.cr.execute(delete_query)

        chk_exist_cron = self.env[constants.IR_CRON_MODEL].search([('name', '=', constants.GOOGLE_EXPORT_DRIVE_DEF)])
        if chk_exist_cron and len(chk_exist_cron) > 0:
            chk_exist_cron[0].write({
                'numbercall': data["export_call_num_drive"],
                'active': data["is_auto_export_drive"],
                'interval_number': data["export_interval_num_drive"],
                'interval_type': data["export_interval_type_drive"],
            })
        else:
            self.env[constants.IR_CRON_MODEL].create({
                'name': constants.GOOGLE_EXPORT_DRIVE_DEF,
                'model_id': self.env[constants.IR_MODEL_MODEL].search([
                    ("model", "=", constants.GOOGLE_CRON_SETTINGS_MODEL)])[0].id,
                'code': 'model.export_drive()',
                'numbercall': data["export_call_num_drive"],
                'active': data["is_auto_export_drive"],
                'interval_number': data["export_interval_num_drive"],
                'interval_type': data["export_interval_type_drive"],
                'priority': 2,
                'doall': 1
            })

    ####################################################################################################
    # ###################      End Cron Import / Export Function Operations     ########################
    ####################################################################################################

    def save_config_mod(self):
        _logging = logging.getLogger(__name__)

        rep_message = ''
        data_db_struct = {
            'is_auto_import_contact': self.is_auto_import_contact,
            'import_interval_num_contact': self.import_interval_num_contact,
            'import_call_num_contact': self.import_call_num_contact,
            'import_interval_type_contact': self.import_interval_type_contact,
            'is_auto_export_contact': self.is_auto_export_contact,
            'export_interval_num_contact': self.export_interval_num_contact,
            'export_call_num_contact': self.export_call_num_contact,
            'export_interval_type_contact': self.export_interval_type_contact,

            'is_auto_import_calendar': self.is_auto_import_calendar,
            'import_interval_num_calendar': self.import_interval_num_calendar,
            'import_call_num_calendar': self.import_call_num_calendar,
            'import_interval_type_calendar': self.import_interval_type_calendar,
            'is_auto_export_calendar': self.is_auto_export_calendar,
            'export_interval_num_calendar': self.export_interval_num_calendar,
            'export_call_num_calendar': self.export_call_num_calendar,
            'export_interval_type_calendar': self.export_interval_type_calendar,

            'is_auto_import_task': self.is_auto_import_task,
            'import_interval_num_task': self.import_interval_num_task,
            'import_call_num_task': self.import_call_num_task,
            'import_interval_type_task': self.import_interval_type_task,
            'is_auto_export_task': self.is_auto_export_task,
            'export_interval_num_task': self.export_interval_num_task,
            'export_call_num_task': self.export_call_num_task,
            'export_interval_type_task': self.export_interval_type_task,

            'is_auto_import_drive': self.is_auto_import_drive,
            'import_interval_num_drive': self.import_interval_num_drive,
            'import_call_num_drive': self.import_call_num_drive,
            'import_interval_type_drive': self.import_interval_type_drive,
            'is_auto_export_drive': self.is_auto_export_drive,
            'export_interval_num_drive': self.export_interval_num_drive,
            'export_call_num_drive': self.export_call_num_drive,
            'export_interval_type_drive': self.export_interval_type_drive,

            'is_auto_import_mail': self.is_auto_import_mail,
            'import_interval_num_mail': self.import_interval_num_mail,
            'import_call_num_mail': self.import_call_num_mail,
            'import_interval_type_mail': self.import_interval_type_mail,
        }
        try:
            db_rows = self.env[self._name].search([])
            if db_rows and len(db_rows) > 0:
                _logging.info("Update Cron Job record")
                if db_rows[constants.INITIAL_INDEX]:
                    db_rows[constants.INITIAL_INDEX].write(data_db_struct)
                rep_message += constants.CRON_JOB_UPDATE
            else:
                _logging.info("Create Cron Job record")
                super().create(data_db_struct)
                rep_message += constants.CRON_JOB_CREATE

            self.update_import_cron_contact(data=data_db_struct)
            self.update_export_cron_contact(data=data_db_struct)
            self.update_import_cron_calendar(data=data_db_struct)
            self.update_export_cron_calendar(data=data_db_struct)
            self.update_import_cron_task(data=data_db_struct)
            self.update_export_cron_task(data=data_db_struct)
            self.update_import_cron_drive(data=data_db_struct)
            self.update_export_cron_drive(data=data_db_struct)
            self.update_import_cron_mail(data=data_db_struct)
        except Exception as ex:
            _logging.exception("Google CronJob Configuration Exception: " + str(ex))
            rep_message += constants.CRON_JOB_ERROR
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': constants.FAILURE_POP_UP_TITLE,
                'message': rep_message,
                'sticky': False,
            }
        }

    ####################################################################################################
    # ###########################      For Contact Default Operations      #############################
    ####################################################################################################

    @api.model
    def get_auto_import_status_contact(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_import_contact if len(db_rows) > 0 else False

    @api.model
    def get_auto_export_status_contact(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_export_contact if len(db_rows) > 0 else False

    @api.model
    def get_import_interval_num_contact(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].import_interval_num_contact) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_num_contact else 1

    @api.model
    def get_export_interval_num_contact(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].export_interval_num_contact) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_interval_num_contact else 1

    @api.model
    def get_import_call_num_contact(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_call_num_contact \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_call_num_contact else '1'

    @api.model
    def get_export_call_num_contact(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].export_call_num_contact \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_call_num_contact else '1'

    @api.model
    def get_import_interval_type_contact(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_interval_type_contact \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_type_contact else 'minutes'

    @api.model
    def get_export_interval_type_contact(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].export_interval_type_contact \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_interval_type_contact else 'minutes'

    ####################################################################################################
    # #######################      For Calendar Event Default Operations      ##########################
    ####################################################################################################

    @api.model
    def get_auto_import_status_calendar(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_import_calendar if len(db_rows) > 0 else False

    @api.model
    def get_auto_export_status_calendar(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_export_calendar if len(db_rows) > 0 else False

    @api.model
    def get_import_interval_num_calendar(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].import_interval_num_calendar) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_num_calendar else 1

    @api.model
    def get_export_interval_num_calendar(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].export_interval_num_calendar) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_interval_num_calendar else 1

    @api.model
    def get_import_call_num_calendar(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_call_num_calendar \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_call_num_calendar else '1'

    @api.model
    def get_export_call_num_calendar(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].export_call_num_calendar \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_call_num_calendar else '1'

    @api.model
    def get_import_interval_type_calendar(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_interval_type_calendar \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_type_calendar else 'minutes'

    @api.model
    def get_export_interval_type_calendar(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].export_interval_type_calendar \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_interval_type_calendar else 'minutes'

    ####################################################################################################
    # ###########################       For Tasks Default Operations       #############################
    ####################################################################################################

    @api.model
    def get_auto_import_status_task(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_import_task if len(db_rows) > 0 else False

    @api.model
    def get_auto_export_status_task(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_import_task if len(db_rows) > 0 else False

    @api.model
    def get_import_interval_num_task(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].import_interval_num_task) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_num_task else 1

    @api.model
    def get_export_interval_num_task(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].export_interval_num_task) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_interval_num_task else 1

    @api.model
    def get_import_call_num_task(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_call_num_task \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_call_num_task else '1'

    @api.model
    def get_export_call_num_task(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].export_call_num_task \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_call_num_task else '1'

    @api.model
    def get_import_interval_type_task(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_interval_type_task \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_type_task else 'minutes'

    @api.model
    def get_export_interval_type_task(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].export_interval_type_task \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_interval_type_task else 'minutes'

    ####################################################################################################
    # #############################      For Drive Default Operations      #############################
    ####################################################################################################

    @api.model
    def get_auto_import_status_drive(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_import_drive if len(db_rows) > 0 else False

    @api.model
    def get_auto_export_status_drive(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_export_drive if len(db_rows) > 0 else False

    @api.model
    def get_import_interval_num_drive(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].import_interval_num_drive) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_num_drive else 1

    @api.model
    def get_export_interval_num_drive(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].export_interval_num_drive) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_interval_num_drive else 1

    @api.model
    def get_import_call_num_drive(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_call_num_drive \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_call_num_drive else '1'

    @api.model
    def get_export_call_num_drive(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].export_call_num_drive \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_call_num_drive else '1'

    @api.model
    def get_import_interval_type_drive(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_interval_type_drive \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_type_drive else 'minutes'

    @api.model
    def get_export_interval_type_drive(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].export_interval_type_drive \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].export_interval_type_drive else 'minutes'

    ####################################################################################################
    # #############################      For GMail Default Operations      #############################
    ####################################################################################################

    @api.model
    def get_auto_import_status_mail(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].is_auto_import_mail if len(db_rows) > 0 else False

    @api.model
    def get_import_interval_num_mail(self):
        db_rows = self.env[self._name].search([])
        return int(db_rows[constants.INITIAL_INDEX].import_interval_num_mail) \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_num_mail else 1

    @api.model
    def get_import_call_num_mail(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_call_num_mail \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_call_num_mail else '1'

    @api.model
    def get_import_interval_type_mail(self):
        db_rows = self.env[self._name].search([])
        return db_rows[constants.INITIAL_INDEX].import_interval_type_mail \
            if len(db_rows) > 0 and db_rows[constants.INITIAL_INDEX].import_interval_type_mail else 'minutes'
