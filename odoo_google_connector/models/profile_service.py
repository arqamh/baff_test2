from . import constants
import requests
import logging


class ProfileService:
    def __init__(self, gl_access_token):
        self.__logging = logging.getLogger(__name__)
        self.__req_version = constants.GL_CONTACT_PROFILE_VERSION
        self.__req_timeout = constants.GL_REQ_TIMEOUT
        self.__base_endpoint = constants.GL_BASE_URL

        self.__default_service = constants.GL_CONTACT_PROFILE_SERVICE
        self.__profile_me = constants.GL_CONTACT_PROFILE_LINK
        self.__gl_access_token = gl_access_token
        self.__req_headers = {"Authorization": "Bearer " + self.__gl_access_token}

        self.__js_resp = {
            "err_status": True,
            "response": "",
            "addons": None
        }

    def reset_response(self):
        self.__js_resp["err_status"] = True
        self.__js_resp["response"] = ""
        self.__js_resp["addons"] = None

    def get_profile(self):
        self.reset_response()
        try:
            req_url = self.__base_endpoint.replace('{{service}}', self.__default_service) + \
                      self.__req_version + self.__profile_me
            req_params = {
                constants.GL_CONTACT_PROFILE_REQ_FLD_NAME: constants.GL_CONTACT_PROFILE_REQ_FLDS_SEP.join(
                                                                constants.GL_CONTACT_SEARCH_FLDS
                                                            )
            }

            resp = requests.get(req_url, params=req_params, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in resp:
                self.__js_resp["response"] = resp
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = resp[constants.RESPONSE_ERROR_KEY]
        except Exception as ex:
            self.__logging.exception("Google Profile Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_PROFILE_EXCEPT
        return self.__js_resp
