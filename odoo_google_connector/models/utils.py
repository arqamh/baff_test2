from . import connection
from . import constants
import logging


def get_db_token(self_env):
    _logging = logging.getLogger(__name__)

    try:
        credentials = self_env[constants.GOOGLE_CREDENTIALS_MODEL].get_google_credentials()
        if constants.RESPONSE_ERROR_KEY not in credentials and constants.RESPONSE_ERR_MESSAGE_KEY not in credentials:
            connect = connection.Connection(google_app_cred=credentials, default_env=self_env)
            conn_response = connect.get_msv_access_token()
            if not conn_response["err_status"]:
                return [conn_response["response"], conn_response["addons"]]
    except:
        pass
    return None


def validate_gc_id_value(self_env, res_model, res_id, new_gc_id):
    chk_res_flag, chk_uniq_gc_id_flag = False, False
    try:
        chk_gc_id_exist = self_env[res_model].search([('gc_id', '=', new_gc_id)])
        if chk_gc_id_exist and len(chk_gc_id_exist) > 0:
            chk_uniq_gc_id_flag = True
            for _res in chk_gc_id_exist:
                if _res.id == res_id:
                    chk_res_flag = True
                    break
        else:
            chk_res_by_id_exist = self_env[res_model].search([
                '&', ('id', '=', res_id), '&', ('gc_id', '!=', False), ('gc_id', '=', new_gc_id)
            ])
            if chk_res_by_id_exist and len(chk_res_by_id_exist) > 0:
                chk_res_flag = True
    except:
        pass
    return chk_res_flag, chk_uniq_gc_id_flag
