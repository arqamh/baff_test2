from . import get_auth_code_server
from . import profile_service
from . import constants
import logging


class Connection:
    def __init__(self, google_app_cred=None, default_env=None):
        self.__logging = logging.getLogger(__name__)

        self.__google_app_credentials = google_app_cred
        self.__default_env = default_env
        self.__grant_code = None
        self.__access_token = None
        self.__refresh_token = None

        self.__js_resp = {
            "err_status": True,
            "response": '',
            "addons": None
        }

    def reset_response(self):
        self.__js_resp["err_status"] = True
        self.__js_resp["response"] = ""
        self.__js_resp["addons"] = None

    def get_access_token(self):
        return self.__access_token

    def get_refresh_token(self):
        return self.__refresh_token

    def get_auth_url(self):
        self.reset_response()
        try:
            if self.__google_app_credentials is not None:
                auth_url = get_auth_code_server.generate_auth_url(self.__google_app_credentials)
                if auth_url != '':
                    self.__js_resp["response"] = auth_url
                    self.__js_resp["err_status"] = False
                else:
                    self.__js_resp["response"] = constants.GL_CONN_URL_FAILED
            else:
                self.__js_resp["response"] = constants.GL_CONN_CRED_NOTFND
        except Exception as ex:
            self.__logging.exception("Connection GEN URL Except: "+str(ex))
            self.__js_resp["response"] = constants.GL_CONN_URL_EXCEPT
        return self.__js_resp

    def generate_access_token(self, grant_code):
        self.reset_response()
        try:
            response = get_auth_code_server.get_authorize_token(grant_code, self.__google_app_credentials)
            if constants.RESPONSE_ERROR_KEY not in response:
                if 'access_token' in response:
                    self.__access_token = response["access_token"]
                if 'refresh_token' in response:
                    self.__refresh_token = response["refresh_token"]
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = constants.GL_CONN_CRED_ACS_FAILED
        except Exception as ex:
            self.__logging.exception("Google Connection Credential Failed: "+str(ex))
            self.__js_resp["response"] = constants.GL_CONN_CRED_ACS_EXCEPT
        return self.__js_resp

    def refresh_access_token(self, refresh_token):
        self.reset_response()
        try:
            resp = get_auth_code_server.get_refresh_authorize_token(refresh_token, self.__google_app_credentials)
            if constants.RESPONSE_ERROR_KEY not in resp:
                if 'access_token' in resp:
                    self.__access_token = resp['access_token']
                if 'refresh_token' in resp:
                    self.__refresh_token = resp["refresh_token"]
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = constants.GL_CONN_RAT_FAILED
        except Exception as ex:
            self.__logging.exception("Google Connection RAT Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CONN_RAT_EXCEPT
        return self.__js_resp

    def get_msv_access_token(self):
        self.reset_response()
        try:
            db_records = self.__default_env[constants.GOOGLE_CREDENTIALS_MODEL].search([])
            if db_records and len(db_records) > 0:
                _db_row = db_records[constants.INITIAL_INDEX]
                _resp_acc_token = _db_row.access_token

                if _resp_acc_token and _resp_acc_token != "":
                    max_attempt = constants.ACCESS_TOKEN_ATTEMPT
                    while max_attempt > 0:
                        _profile = profile_service.ProfileService(gl_access_token=_resp_acc_token)
                        p_response = _profile.get_profile()

                        if not p_response["err_status"]:
                            self.__js_resp["response"] = _resp_acc_token
                            self.__js_resp["addons"] = p_response["response"]
                            self.__js_resp["err_status"] = False
                            break

                        elif constants.TOKEN_ERR_STATUS_CODE == p_response["response"]["code"]:
                            rat_response = self.refresh_access_token(refresh_token=_db_row.refresh_token)
                            if not rat_response["err_status"]:
                                _resp_acc_token = self.get_access_token()

                                db_upd_credentials = {"access_token": self.get_access_token()}
                                if self.get_refresh_token():
                                    db_upd_credentials["refresh_token"] = self.get_refresh_token()
                                _db_row.write(db_upd_credentials)
                            else:
                                self.__js_resp["response"] = constants.ACCESS_TOKEN_ERR_REFRESH

                        else:
                            self.__js_resp["response"] = constants.ACCESS_TOKEN_INVALID
                        max_attempt -= 1
                else:
                    self.__js_resp["response"] = constants.ACCESS_TOKEN_NOT_FND
            else:
                self.__js_resp["response"] = constants.ACCESS_TOKEN_CRED_NOT_FND
        except Exception as ex:
            self.__logging.exception("Unable to get Google OAuth credentials: " + str(ex))
            self.__js_resp["response"] = constants.ACCESS_TOKEN_EXCEPT
        return self.__js_resp

    def get_quick_msv_access_token(self):
        self.reset_response()
        try:
            if "access_token" in self.__google_app_credentials and self.__google_app_credentials["access_token"]:
                max_attempt = constants.ACCESS_TOKEN_ATTEMPT
                _resp_acc_token = self.__google_app_credentials["access_token"]

                while max_attempt > 0:
                    _profile = profile_service.ProfileService(gl_access_token=_resp_acc_token)
                    p_response = _profile.get_profile()
                    if not p_response["err_status"]:
                        self.__js_resp["response"] = _resp_acc_token
                        self.__js_resp["addons"] = p_response["response"]
                        self.__js_resp["err_status"] = False
                        break

                    elif constants.TOKEN_ERR_STATUS_CODE == p_response["response"]["code"]:
                        rat_response = self.refresh_access_token(
                            refresh_token=self.__google_app_credentials["refresh_token"])
                        if not rat_response["err_status"]:
                            _resp_acc_token = self.get_access_token()
                        else:
                            self.__js_resp["response"] = constants.ACCESS_TOKEN_ERR_REFRESH

                    else:
                        self.__js_resp["response"] = constants.ACCESS_TOKEN_INVALID
                    max_attempt -= 1
            else:
                self.__js_resp["response"] = constants.ACCESS_TOKEN_NOT_FND
        except Exception as ex:
            self.__logging.exception("Unable to get Google OAuth credentials: " + str(ex))
            self.__js_resp["response"] = constants.ACCESS_TOKEN_EXCEPT
        return self.__js_resp
