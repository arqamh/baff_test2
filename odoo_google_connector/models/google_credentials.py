from odoo import models, fields, api
from . import connection
from . import constants
import logging


class GoogleCredentials(models.Model):
    _name = constants.GOOGLE_CREDENTIALS_MODEL
    _description = constants.GOOGLE_CREDENTIALS_MODEL_DESC

    redirect_url = fields.Char(string="Redirect URL", required=True, default=lambda self: self._get_default_url())
    client_id = fields.Char(string="Client ID", required=True, default=lambda self: self._get_default_client_id())
    client_secret = fields.Char(string="Client Secret", required=True,
                                default=lambda self: self._get_default_secret_id())
    access_token = fields.Char(string="Access Token", default=None)
    refresh_token = fields.Char(string="Refresh Token", default=None)
    grant_code = fields.Char(string="Grant Code", default=None)

    def connect(self):
        _logging = logging.getLogger(__name__)

        rep_message = ''
        val_struct = {
            'redirect_url': self.redirect_url,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        try:
            if constants.GOOGLE_CREDENTIALS_RDT_URI in self.redirect_url:
                db_rows = self.env[self._name].search([])
                if db_rows and len(db_rows) > 0:
                    _logging.info("Update CRD record")
                    db_rows[constants.INITIAL_INDEX].write(val_struct)
                else:
                    _logging.info("Create CRD record")
                    super().create(val_struct)

                conn = connection.Connection(google_app_cred=val_struct)
                _response = conn.get_auth_url()
                if not _response["err_status"]:
                    return {
                        'type': 'ir.actions.act_url',
                        'name': "grant_code",
                        'target': 'self',
                        'url': _response["response"],
                    }
                else:
                    rep_message += constants.AUTH_URL_CREATION_FAILED
            else:
                rep_message += constants.GOOGLE_CREDENTIALS_RDT_URI_ERR
        except Exception as ex:
            _logging.exception("Google Credential OAuth URL Exception: " + str(ex))
            rep_message += constants.AUTH_URL_CREATION_EXCEPT
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': constants.FAILURE_POP_UP_TITLE,
                'message': rep_message,
                'sticky': False,
            }
        }

    @api.model
    def _get_default_url(self):
        latest_record = self.env[self._name].search([])
        return latest_record[constants.INITIAL_INDEX].redirect_url if len(latest_record) > 0 else ''

    @api.model
    def _get_default_client_id(self):
        latest_record = self.env[self._name].search([])
        return latest_record[constants.INITIAL_INDEX].client_id if len(latest_record) > 0 else ''

    @api.model
    def _get_default_secret_id(self):
        latest_record = self.env[self._name].search([])
        return latest_record[constants.INITIAL_INDEX].client_secret if len(latest_record) > 0 else ''

    def get_google_credentials(self):
        cred_response = {}
        try:
            db_rows = self.env[self._name].search([])
            if db_rows and len(db_rows) > 0:
                cred_response["client_id"] = db_rows[constants.INITIAL_INDEX].client_id
                cred_response["client_secret"] = db_rows[constants.INITIAL_INDEX].client_secret
                cred_response["redirect_url"] = db_rows[constants.INITIAL_INDEX].redirect_url
                cred_response["access_token"] = db_rows[constants.INITIAL_INDEX].access_token
                cred_response["refresh_token"] = db_rows[constants.INITIAL_INDEX].refresh_token
            else:
                cred_response[constants.RESPONSE_ERROR_KEY] = "Credentials are not found"
                cred_response[constants.RESPONSE_ERR_MESSAGE_KEY] = constants.GL_CONN_CRED_NOTFND
        except Exception as ex:
            cred_response[constants.RESPONSE_ERROR_KEY] = str(ex)
            cred_response[constants.RESPONSE_ERR_MESSAGE_KEY] = constants.GL_CONN_CRED_ACS_EXCEPT
        return cred_response
