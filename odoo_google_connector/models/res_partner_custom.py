from odoo import models, fields, api
from . import people_service
from . import gdrive_service
from . import constants
from . import utils
import logging
import base64


class ResPartnerCategory(models.Model):
    _inherit = constants.RES_PARTNER_CATEGORY_MODEL

    gc_name = fields.Char('CMG Name')
    gc_res_id = fields.Char("Membership Group")


class ResPartnerExtend(models.Model):
    _inherit = constants.RES_PARTNER_MODEL

    gc_id = fields.Char(string='Google-ID', copy=False, readonly=True, default=None)
    gc_etag = fields.Char(string='Google-eTag', copy=False, readonly=True, default=None)
    drive_sync = fields.Boolean("GDrive Sync", default=False)
    source = fields.Char(string="Source", readonly=True)
    google_attachment_ids = fields.Many2many(
        constants.IR_ATTACHMENT_MODEL, constants.CLASS_IR_ATTACHMENT_REL_MODEL,
        'class_id', 'attachment_id', 'Attachments')

    def create_contact(self, contact_email, name=None):
        contact_rec = self.env[constants.RES_PARTNER_MODEL].create({
            'name': name if name else contact_email.split('@')[0],
            'email': contact_email,
            'source': constants.GL_CONTACT_SOURCE
        })
        return contact_rec

    def google_drive_upload_btn(self):
        _logging = logging.getLogger(__name__)

        pop_message = ""
        res_partner = self.env[constants.RES_PARTNER_MODEL].search([
            '&', ('id', '=', self.id), ('drive_sync', '=', True)
        ])
        if res_partner and len(res_partner):
            file_records = {'res_info': res_partner, 'files': []}

            for attachment in self.google_attachment_ids:
                try:
                    decoded_data = base64.b64decode(attachment.datas)
                    file_records["files"].append({
                        "id": attachment.id,
                        "name": attachment.name,
                        "mimetype": attachment.mimetype,
                        "db_datas": decoded_data
                    })
                except Exception as ex:
                    _logging.exception("Log >> Export OPT, File attachment Except: " + str(ex))

            db_ref_token = utils.get_db_token(self_env=self.env)
            if db_ref_token and len(db_ref_token) > 0:
                _onedrive = gdrive_service.GDriveService(gl_access_token=db_ref_token[0], self_env=self.env)
                _dr_response = _onedrive.export_gdrive_documents(res_data=file_records)

                if not _dr_response["err_status"]:
                    pop_message += "Files uploaded successfully: " + constants.GL_DRIVE_OPT_KEY
                else:
                    pop_message += _dr_response["response"]
            else:
                pop_message += "Oops, unable to find oauth credentials"
        else:
            pop_message += "Please enable GDrive Sync"

        if constants.GL_DRIVE_OPT_KEY in pop_message:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "System Notification",
                    'message': pop_message,
                    'sticky': False,
                }
            }

    def google_drive_download_btn(self):
        _log = logging.getLogger(__name__)

        pop_message = ""
        res_partner = self.env[constants.RES_PARTNER_MODEL].search([
            '&', ('id', '=', self.id), ('drive_sync', '=', True)
        ])
        if res_partner and len(res_partner) > 0:
            db_ref_token = utils.get_db_token(self_env=self.env)
            if db_ref_token and len(db_ref_token) > 0:
                _onedrive = gdrive_service.GDriveService(gl_access_token=db_ref_token[0], self_env=self.env)
                _dr_response = _onedrive.import_gdrive_documents(res_info=res_partner)
                if not _dr_response["err_status"]:
                    pop_message += "Files downloaded successfully: " + constants.GL_DRIVE_OPT_KEY
                else:
                    pop_message += str(_dr_response["response"])
            else:
                pop_message += "Oops, unable to find oauth credentials"
        else:
            pop_message += "Please enable GDrive Sync"

        if constants.GL_DRIVE_OPT_KEY in pop_message:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "System Notification",
                    'message': pop_message,
                    'sticky': False,
                }
            }

    def write(self, values):
        if 'gc_id' in values:
            chk_flag, chk_uniq_id = utils.validate_gc_id_value(
                self_env=self.env, res_model=constants.RES_PARTNER_MODEL, res_id=self.id, new_gc_id=values["gc_id"])
            if chk_flag or chk_uniq_id:
                del values["gc_id"]
        _db_updated_record = super(ResPartnerExtend, self).write(values)

        # Real Time Sync
        # This commented code being used either create or update a contact from Odoo to Google Contact
        _logging = logging.getLogger(__name__)
        _logging.info("> > > > > > > >> > > > > > RES PARTNER CALL > > > > > > > >  > > >")
        _logging.info(values)
        _logging.info("> > > > > > > >> > > > > > > > >  >> > > > > > > > > > > >  > > >")
        exclude_fields = ['credit_limit']
        if len(values) == 1 and any([True for key in exclude_fields if key in values]):
            pass
        else:
            try:
                local_update_record = self.env[constants.RES_PARTNER_MODEL].search([('id', '=', self.id)])
                db_access_tokens = utils.get_db_token(self_env=self.env)
                if db_access_tokens and len(db_access_tokens) > 0:
                    _people = people_service.PeopleService(gl_access_token=db_access_tokens[0], default_env=self.env)
                    sr_resp = _people.create_contact(l2s_contact=local_update_record[0])
                    _logging.info("> > > > > > > >> > > > > > GOOGLE PEOPLE CALL > > > > > > > >  > > >")
                    _logging.info(sr_resp)
                    _logging.info("> > > > > > > >> > > > > > > > >  >> > > > > > > > > > > >  > > > > >")
                    if sr_resp["err_status"]:
                        _logging.error("Create/Update Contact Error: " + sr_resp["response"])
                else:
                    _logging.error("Oops, Google credentials are not found. Please try again")
            except Exception as ex:
                _logging.exception("Oops, Google Contact updation exception found: " + str(ex))

        return _db_updated_record

    @api.model
    def unlink(self):
        _logging = logging.getLogger(__name__)

        ids_to_delete = self.ids
        for cid in ids_to_delete:
            try:
                ref_contact = self.env[constants.RES_PARTNER_MODEL].search([('id', '=', cid)])
                if ref_contact and len(ref_contact) > 0 and ref_contact.gc_id:
                    db_access_tokens = utils.get_db_token(self_env=self.env)
                    if db_access_tokens and len(db_access_tokens) > 0:
                        _people = people_service.PeopleService(
                            gl_access_token=db_access_tokens[0], default_env=self.env)
                        sr_resp = _people.delete_serv_contact_by_id(ref_contact[0].gc_id)
                        if sr_resp["err_status"]:
                            _logging.error("Delete Contact Error: " + str(sr_resp["response"]))

                self.env.cr.execute('delete from ' + constants.RES_PARTNER_STASH_MODEL + ' where id=' + str(cid))
            except Exception as ex:
                _logging.exception("Oops, unable to delete database contact: " + str(ex))

        return super(ResPartnerExtend, self).unlink()

    @api.model
    def update_params(self, values):
        _logging = logging.getLogger(__name__)

        try:
            if len(values) > 0:
                upd_query = "update " + constants.RES_PARTNER_STASH_MODEL + " set"
                for _field in values:
                    if type(values[_field]) == bool:
                        upd_query += " " + _field + "=" + str(values[_field]) + ","
                    elif type(values[_field]) == list:
                        for _fid in values[_field]:
                            upd_query += " " + _field + "= (6, 0, " + str(_fid) + "),"
                    else:
                        if _field == 'gc_id':
                            chk_flag, chk_uniq_id = utils.validate_gc_id_value(
                                self_env=self.env, res_model=constants.RES_PARTNER_MODEL,
                                res_id=self.id, new_gc_id=values["gc_id"])

                            if not chk_flag and not chk_uniq_id:
                                upd_query += " " + _field + "='" + str(values[_field]) + "',"
                        else:
                            upd_query += " " + _field + "='" + str(values[_field]) + "',"
                upd_query = upd_query[:-1] + " where id=" + str(self.id)
                self.env.cr.execute(upd_query)
                return True
            else:
                return False
        except:
            pass

    @api.model
    def update_categories_params(self, values):
        _logging = logging.getLogger(__name__)

        if len(values) > 0:
            del_query = "delete from  " + constants.RES_PARTNER_CATEGORY_REL_MODEL + " where partner_id=" + str(self.id)
            self.env.cr.execute(del_query)
            comb_query = ""
            for category_id in values:
                comb_query += "insert into " + constants.RES_PARTNER_CATEGORY_REL_MODEL + \
                              " (category_id, partner_id)" + " values (" + str(category_id) + ", " + str(self.id) + ");"
            if len(comb_query) > 0:
                self.env.cr.execute(comb_query)
            return True
        else:
            return False

    def force_update(self):
        _logging = logging.getLogger(__name__)

        try:
            local_update_record = self.env[constants.RES_PARTNER_MODEL].search([('id', '=', self.id)])
            if local_update_record and len(local_update_record) > 0:
                db_access_tokens = utils.get_db_token(self_env=self.env)
                if db_access_tokens and len(db_access_tokens) > 0:
                    _people = people_service.PeopleService(gl_access_token=db_access_tokens[0], default_env=self.env)
                    sr_resp = _people.create_contact(l2s_contact=local_update_record[0])
                    if sr_resp["err_status"]:
                        _logging.error("Force Update  >>>  Create/Update Contact Error: " + sr_resp["response"])
                else:
                    _logging.error("Force Update  >>>  Google Credentials fetch error found")
        except Exception as ex:
            _logging.exception("Force Update  >>>  Exception found: " + str(ex))

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        _logging = logging.getLogger(__name__)

        return super(ResPartnerExtend, self).search_read(domain, fields, offset, limit, order)
