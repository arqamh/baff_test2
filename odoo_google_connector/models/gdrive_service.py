from . import constants
import requests
import logging
import base64
import json


class GDriveService:
    def __init__(self, gl_access_token, self_env, initial_date=None, end_date=None):
        self.__logging = logging.getLogger(__name__)

        self.__gl_access_token = gl_access_token
        self.__self_env = self_env
        self.__initial_date = initial_date
        self.__end_date = end_date

        self.__req_version = constants.GL_DRIVE_VERSION
        self.__req_timeout = constants.GL_REQ_TIMEOUT
        self.__base_endpoint = constants.GL_BASE_URL.replace('{{service}}', constants.GL_CALENDAR_DRIVE_SERVICE)
        self.__cr_directory_api = constants.GL_DRIVE_META_DATA
        self.__default_file_api = constants.GL_DRIVE_FILES
        self.__upload_file_api = constants.GL_DRIVE_UPLOAD_SERVICE

        self.__req_headers = {
            "Authorization": "Bearer " + self.__gl_access_token,
            "Content-Type": "application/json"
        }
        self.__js_resp = {
            "err_status": True,
            "response": None,
            "total": 0,
            "success": 0,
            "updated": 0,
            "failed": 0
        }

    def reset_response(self):
        self.__js_resp["err_status"] = True
        self.__js_resp["response"] = None
        self.__js_resp["total"] = 0
        self.__js_resp["success"] = 0
        self.__js_resp["updated"] = 0
        self.__js_resp["failed"] = 0

    def create_directory(self, res_name):
        crt_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__cr_directory_api + self.__req_version + self.__default_file_api
            req_server = requests.post(req_url, json={
                "name": res_name, "mimeType": "application/vnd.google-apps.folder"
            }, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in req_server:
                crt_resp["response"] = req_server["id"]
                crt_resp["err_status"] = False
            else:
                crt_resp["response"] = constants.GL_DRIVE_EXPORT_DIR_ERR
        except Exception as ex:
            self.__logging.exception("GDrive Create Directory Exception: " + str(ex))
            crt_resp["response"] = constants.GL_DRIVE_EXPORT_DIR_EXCEPT
        return crt_resp

    def search_directory(self, res_name):
        src_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__cr_directory_api + self.__req_version + self.__default_file_api
            query_params = {
                'q': "name = '" + res_name + "' and mimeType = '" + constants.GL_DRIVE_FOLDER_MTYPE + "'",
                'spaces': constants.GL_DRIVE_SPACE
            }

            req_server = requests.get(
                req_url, params=query_params, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in req_server:
                for _folder in req_server[constants.RESPONSE_FILES_KEY]:
                    if _folder["name"] == res_name and _folder["mimeType"] == constants.GL_DRIVE_FOLDER_MTYPE:
                        src_resp["response"] = _folder["id"]
                        src_resp["err_status"] = False
                        break
            else:
                src_resp["response"] = constants.GL_DRIVE_EXPORT_DIR_SERC_ERR
        except Exception as ex:
            self.__logging.exception("GDrive Search Directory Exception: " + str(ex))
            src_resp["response"] = constants.GL_DRIVE_EXPORT_DIR_SERC_EXCEPT
        return src_resp

    def upload_file(self, res_folder_id, file_):
        upl_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__upload_file_api + self.__req_version + \
                      self.__default_file_api + "?uploadType=resumable"
            json_params = {
                "name": file_["name"],
                "parents": [res_folder_id],
                'mimeType': file_["mimetype"]
            }

            loc_resp = requests.post(req_url, headers=self.__req_headers, data=json.dumps(json_params))
            location = loc_resp.headers['Location']
            resp_server = requests.put(location, headers=self.__req_headers, data=file_["db_datas"]).json()
            if constants.RESPONSE_ERROR_KEY in resp_server:
                upl_resp["response"] = "Upload file request could not be proceed, Please try again\n" +\
                                   resp_server['error']['message']
            else:
                upl_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Exception found while uploading file: " + str(ex))
            upl_resp["response"] = constants.GL_DRIVE_FILE_EXPORT_ERR
        return upl_resp

    ##############################################################################################################
    # #####################################       Export GDrive Operations       #################################
    ##############################################################################################################

    def get_fetch_export_dir(self, res_folder_id):
        rd_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__cr_directory_api + self.__req_version + self.__default_file_api
            query_params = {'q': "'" + res_folder_id + "' in parents"}
            req_server = requests.get(
                req_url, params=query_params, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in req_server:
                if len(req_server[constants.RESPONSE_FILES_KEY]) > 0:
                    rd_resp["response"] = req_server[constants.RESPONSE_FILES_KEY]
                    rd_resp["err_status"] = False
                else:
                    rd_resp["response"] = constants.GL_DRIVE_FILE_NOTFND
            else:
                rd_resp["response"] = constants.GL_DRIVE_EXPORT_DIR_ERR
        except Exception as ex:
            self.__logging.exception("GDrive Fetch Export Directory Exception: " + str(ex))
            rd_resp["response"] = constants.GL_DRIVE_IMP_SERV_EXCEPT
        return rd_resp

    def export_gdrive_documents(self, res_data):
        self.reset_response()
        try:
            sr_resp = self.search_directory(res_data["res_info"].name)
            if sr_resp["err_status"]:
                sr_resp = self.create_directory(res_data["res_info"].name)

            if not sr_resp["err_status"]:
                self.__js_resp["total"] = len(res_data["files"])
                folder_id = sr_resp["response"]
                serv_read_resp = self.get_fetch_export_dir(res_folder_id=folder_id)

                for file in res_data["files"]:
                    chk_file_exist = False
                    if not serv_read_resp["err_status"]:
                        for ex_file in serv_read_resp["response"]:
                            if ex_file["name"] == file["name"] and ex_file["mimeType"] == file["mimetype"]:
                                chk_file_exist = True
                                break

                    if not chk_file_exist:
                        up_resp = self.upload_file(folder_id, file)
                        if not up_resp["err_status"]:
                            self.__js_resp["success"] += 1
                        else:
                            self.__js_resp["failed"] += 1
                            
                    self.__js_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("GDrive Export Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_DRIVE_EXP_EXCEPT
        return self.__js_resp

    ################################################################################################################
    # #################################          Import GDrive Operation           #################################
    ################################################################################################################

    def check_db_file_exists(self, res_info, file):
        chk_eir_file = False
        try:
            self.__self_env.cr.execute(
                "select id from " + constants.DB_IR_ATTACHMENT_MODEL + " where name='" + file["name"] +
                "' and mimetype='" + file["mimeType"] + "'")

            file_recs = self.__self_env.cr.fetchall()
            if file_recs and len(file_recs) > 0:
                for db_file in file_recs:
                    query = "select * from " + constants.CLASS_IR_ATTACHMENT_REL_MODEL + \
                            " where class_id = " + str(res_info.id) + " and attachment_id = " + str(db_file[0])

                    self.__self_env.cr.execute(query)
                    chk_file_res = self.__self_env.cr.fetchone()
                    if chk_file_res and len(chk_file_res) > 0:
                        chk_eir_file = True
        except Exception as ex:
            self.__logging.exception("Database File Search Exception: " + str(ex))
        return chk_eir_file

    def read_server_dir(self, res_folder_id):
        try:
            req_url = self.__base_endpoint + self.__cr_directory_api + self.__req_version + \
                      self.__default_file_api
            query_params = {'q': "'" + res_folder_id + "' in parents"}
            req_server = requests.get(req_url, params=query_params, headers=self.__req_headers,
                                      timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in req_server:
                if len(req_server[constants.RESPONSE_FILES_KEY]) > 0:
                    self.__js_resp["total"] = len(req_server[constants.RESPONSE_FILES_KEY])
                    self.__js_resp["response"] = req_server[constants.RESPONSE_FILES_KEY]
                    self.__js_resp["err_status"] = False
                else:
                    self.__js_resp["response"] = constants.GL_DRIVE_FILE_NOTFND
            else:
                self.__js_resp["response"] = constants.GL_DRIVE_EXPORT_DIR_ERR
        except Exception as ex:
            self.__logging.exception("Read/Import GDrive Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_DRIVE_IMP_SERV_EXCEPT

    def import_gdrive_documents(self, res_info):
        self.reset_response()
        try:
            sr_resp = self.search_directory(res_name=res_info.name)
            if sr_resp["err_status"]:
                sr_resp = self.create_directory(res_name=res_info.name)
            if not sr_resp["err_status"]:
                self.read_server_dir(res_folder_id=sr_resp["response"])

                if not self.__js_resp["err_status"]:
                    for file_record in self.__js_resp["response"]:
                        try:
                            chk_status = self.check_db_file_exists(res_info=res_info, file=file_record)
                            if not chk_status:
                                req_file_url = self.__base_endpoint + self.__cr_directory_api + self.__req_version + \
                                               self.__default_file_api + '/' + file_record["id"]
                                file_dwn = requests.get(
                                    req_file_url + "?supportsAllDrives=true&alt=media", headers=self.__req_headers)
                                byte_data = base64.b64encode(file_dwn.content)

                                save_attach_rec = self.__self_env[constants.IR_ATTACHMENT_MODEL].create({
                                    'name': file_record["name"],
                                    'datas': byte_data,
                                    'mimetype': file_record["mimeType"],
                                    'type': 'binary',
                                    'res_model': constants.RES_PARTNER_MODEL,
                                    'res_id': 0,
                                })

                                self.__self_env.cr.execute(
                                    "insert into " + constants.CLASS_IR_ATTACHMENT_REL_MODEL +
                                    " (class_id, attachment_id) values (" + str(res_info.id) +
                                    "," + str(save_attach_rec.id) + ")")
                                self.__js_resp["success"] += 1

                        except Exception as ex:
                            self.__logging.info("Log >> Read Drive Internal Exception: " + str(ex))
                            self.__js_resp["failed"] += 1
                else:
                    self.__js_resp["response"] = constants.GL_DRIVE_FILE_FETCH_ERR
            else:
                self.__js_resp["response"] = constants.GL_DRIVE_DIR_FETCH_ERR
        except Exception as ex:
            self.__logging.exception("Import GDrive Files Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_DRIVE_IMP_EXCEPT
        return self.__js_resp
