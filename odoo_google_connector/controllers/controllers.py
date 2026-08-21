from ..models.connection import Connection
from urllib.parse import unquote
from ..models.constants import *
from odoo.http import request
from odoo import http
import werkzeug
import logging


class GoogleIntegration(http.Controller):
    @http.route(GOOGLE_CREDENTIALS_RDT_URI, auth='public')
    def index(self, **kw):
        _logging = logging.getLogger(__name__)

        conseq_record = request.env[GOOGLE_CREDENTIALS_MODEL].search([])[INITIAL_INDEX]
        try:
            if GOOGLE_CREDENTIALS_RDT_URI_KEY in str(http.request.httprequest.full_path):
                grant_code = str(http.request.httprequest.full_path).split(GOOGLE_CREDENTIALS_RDT_URI_KEY)[1]
                if GOOGLE_CREDENTIALS_RDT_URI_SPLITTER in grant_code:
                    grant_code = grant_code.split(GOOGLE_CREDENTIALS_RDT_URI_SPLITTER)[0]
                grant_code = unquote(grant_code)

                google_cloud_params = {
                    'redirect_url': conseq_record.redirect_url,
                    'client_id': conseq_record.client_id,
                    'client_secret': conseq_record.client_secret
                }

                conn = Connection(google_app_cred=google_cloud_params, default_env=request.env)
                _response = conn.generate_access_token(grant_code=grant_code)
                if not _response["err_status"]:
                    update_params = {
                        'grant_code': grant_code,
                        'access_token': conn.get_access_token(),
                        'refresh_token': conn.get_refresh_token()
                    }
                    conseq_record.write(update_params)
                    return werkzeug.utils.redirect(GOOGLE_CREDENTIALS_RDT_URI_ODOO)
                else:
                    return "Connection failed: " + str(_response["response"])
            else:
                return GRANT_CODE_ERR
        except Exception as ex:
            return "Internal Exception found: "+str(ex)
