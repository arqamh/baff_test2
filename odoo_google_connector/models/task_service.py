from . import constants
from datetime import *
import requests
import logging
import json
import pytz
import re


class TaskService:
    def __init__(
            self, gl_access_token, default_env, default_profile, initial_date=None, end_date=None, folder=None):
        self.__logging = logging.getLogger(__name__)

        self.__gl_access_token = gl_access_token
        self.__default_env = default_env
        self.__default_profile = default_profile
        self.__initial_date = initial_date
        self.__end_date = end_date
        self.__folder = folder

        self.__user_tz = default_env.user.tz or pytz.utc
        self.__local_tz = pytz.timezone(self.__user_tz)

        self.__req_version = constants.GL_TASKS_VERSION
        self.__req_timeout = constants.GL_REQ_TIMEOUT
        self.__default_service = constants.GL_TASKS_SERVICE
        self.__default_folder = constants.GL_TASKS_DEFAULT_FOLDER
        self.__base_endpoint = constants.GL_BASE_URL.replace(
            '{{service}}', self.__default_service) + self.__default_service + '/'
        self.__tasks_list_api = constants.GL_TASKS_LIST_LINK
        self.__tasks_details_api = constants.GL_TASKS_GET_TASKS

        self.__db_activity_type_id = self.__default_env[constants.MAIL_ACTIVITY_TYPE_MODEL].search([
            ('name', '=', 'To Do')]).id

        self.__clean_tags_re = re.compile('<.*?>')
        self.__req_headers = {"Authorization": "Bearer " + self.__gl_access_token}
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

    def get_db_partner_id(self):
        gt_resp = {"err_status": True, "response": None}
        try:
            if type(self.__default_profile) == tuple:
                self.__default_profile = self.__default_profile[0]
            ur_email = self.__default_profile[constants.GL_PROFILE_EMAIL_FD][0][constants.GL_PROFILE_EMAIL_FD_INTERNAL]
            ur_name = self.__default_profile[constants.GL_PROFILE_NAME_FD][0][constants.GL_PROFILE_NAME_FD_INTERNAL]

            partner = self.__default_env[constants.RES_PARTNER_MODEL].search([('email', '=', ur_email)])
            if partner and len(partner) > 0:
                pass
            else:
                partner = self.__default_env[constants.GOOGLE_CONNECTOR_MODEL].create_contact(ur_email, ur_name)

            gt_resp["response"] = partner[0].id
            gt_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Get DB Partner-ID Exception:" + str(ex))
            gt_resp["response"] = constants.GL_TASKS_GET_LIST_EXCEPT
        return gt_resp

    def get_serv_task_list_id(self):
        gt_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__tasks_list_api
            sr_resp = requests.get(req_url, headers=self.__req_headers).json()
            if len(sr_resp) > 0 and constants.RESPONSE_ERROR_KEY not in sr_resp:
                _task_list_id = None
                for each_lt in sr_resp[constants.RESPONSE_ITEMS_KEY]:
                    if (self.__folder is None and each_lt["title"] == self.__default_folder) or \
                            (self.__folder and each_lt["title"] == self.__folder):
                        _task_list_id = each_lt["id"]
                        break

                if _task_list_id is None:
                    _task_list_id = sr_resp[constants.RESPONSE_ITEMS_KEY][0]["id"]
                if _task_list_id:
                    gt_resp["response"] = _task_list_id
                    gt_resp["err_status"] = False
                else:
                    gt_resp["response"] = constants.GL_TASKS_GET_LIST_NOT_FND
            else:
                gt_resp["response"] = constants.GL_TASKS_GET_LIST_ERR
        except Exception as ex:
            self.__logging.exception("Get Server TaskList Exception: " + str(ex))
            gt_resp["response"] = constants.GL_TASKS_GET_LIST_EXCEPT
        return gt_resp

    def done_task_by_id(self, db_task):
        done_resp = {"err_status": True, "response": None}
        try:
            tl_task_resp = self.get_serv_task_list_id()
            if not tl_task_resp["err_status"]:
                json_params = {
                    "id": db_task.gc_id,
                    "title": db_task.summary,
                    "notes": re.sub(self.__clean_tags_re, '', db_task.note) if db_task.note else "default",
                    "status": "completed"
                }
                if "date_deadline" in db_task:
                    if len(str(db_task["date_deadline"])) == 10:
                        json_params['due'] = str(db_task["date_deadline"]) + 'T00:00:00Z'
                    else:
                        json_params['due'] = str(db_task["date_deadline"]).replace(' ', 'T')

                req_url = self.__base_endpoint + self.__req_version + self.__tasks_details_api + \
                          '/' + tl_task_resp["response"] + '/' + self.__default_service + '/' + db_task.gc_id
                sr_resp = requests.put(req_url, data=json.dumps(json_params), headers=self.__req_headers).json()
                if constants.RESPONSE_ERROR_KEY not in sr_resp:
                    done_resp["response"] = sr_resp
                    done_resp["err_status"] = False
                else:
                    done_resp["response"] = constants.GL_TASKS_DON_ERR
            else:
                done_resp["response"] = constants.GL_TASKS_DEL_ERR
        except Exception as ex:
            self.__logging.exception("Done Task Server Exception: " + str(ex))
            done_resp["response"] = constants.GL_TASKS_DON_EXCEPT
        return done_resp

    def delete_task_by_id(self, gc_id):
        del_resp = {"err_status": True, "response": None}
        try:
            tl_task_resp = self.get_serv_task_list_id()
            if not tl_task_resp["err_status"]:
                req_url = self.__base_endpoint + self.__req_version + self.__tasks_details_api + \
                          '/' + tl_task_resp["response"] + '/' + self.__default_service + '/' + gc_id
                sr_resp = requests.delete(req_url, headers=self.__req_headers).json()
                if constants.RESPONSE_ERROR_KEY not in sr_resp:
                    del_resp["response"] = sr_resp
                    del_resp["err_status"] = False
                else:
                    del_resp["response"] = constants.GL_TASKS_DEL_ERR
            else:
                del_resp["response"] = constants.GL_TASKS_DEL_ERR
        except Exception as ex:
            self.__logging.exception("Delete Server Task Exception: " + str(ex))
            del_resp["response"] = constants.GL_TASKS_DEL_EXCEPT
        return del_resp

    def check_task(self, s2l_task=None, l2s_task=None, l2s_req_link=None):
        chk_resp = {"err_status": True, "response": None}
        try:
            if s2l_task:
                chk_db_task = self.__default_env[constants.MAIL_ACTIVITY_MODEL].search([
                    '&', ('activity_type_id', '=', self.__db_activity_type_id), ('summary', '=', s2l_task["title"])
                ])
                if chk_db_task and len(chk_db_task) > 0:
                    chk_resp["response"] = chk_db_task[0]
                    chk_resp["err_status"] = False
                else:
                    chk_resp["response"] = constants.GL_TASKS_CHK_ERR

            elif l2s_task:
                req_url = l2s_req_link
                if l2s_task.gc_id:
                    req_url += "/" + l2s_task.gc_id
                    sr_resp = requests.get(req_url, headers=self.__req_headers).json()
                    if constants.RESPONSE_ERROR_KEY not in sr_resp:
                        chk_resp["response"] = sr_resp
                        chk_resp["err_status"] = False

                if chk_resp["err_status"]:
                    sr_resp = requests.get(l2s_req_link, headers=self.__req_headers).json()
                    if constants.RESPONSE_ERROR_KEY not in sr_resp:
                        if constants.RESPONSE_ITEMS_KEY in sr_resp and len(sr_resp[constants.RESPONSE_ITEMS_KEY]) > 0:
                            for each in sr_resp[constants.RESPONSE_ITEMS_KEY]:
                                if each["title"] == l2s_task.summary:
                                    chk_resp["response"] = each
                                    chk_resp["err_status"] = False
                                    break
            else:
                chk_resp["response"] = constants.GL_TASKS_CHK_ERR
        except Exception as ex:
            self.__logging.exception("Check Local/Server Task Exception: " + str(ex))
            chk_resp["response"] = constants.GL_TASKS_CHK_EXCEPT
        return chk_resp

    def create_update_local_task(self, sr_task, previous_task=None):
        crt_resp = {"err_status": True, "response": None}
        try:
            get_partner_resp = self.get_db_partner_id()
            if not get_partner_resp["err_status"]:
                db_data = {
                    'gc_id': sr_task["id"],
                    'gc_etag': sr_task["etag"],
                    'res_id': get_partner_resp["response"],
                    'res_model_id': self.__default_env[constants.IR_MODEL_MODEL].search([
                        ('model', '=', constants.RES_PARTNER_MODEL)]).id,
                    'user_id': self.__default_env.user.id,
                    'summary': sr_task["title"],
                    'activity_type_id': self.__db_activity_type_id,
                }

                if 'due' in sr_task:
                    _due_date = sr_task["due"].split('.')[0]
                    _dte = datetime.strptime(_due_date, '%Y-%m-%dT%H:%M:%S')
                    _due_datetime = self.__local_tz.localize(_dte)
                    db_data['date_deadline'] = _due_datetime
                if "notes" in sr_task and sr_task["notes"]:
                    db_data['note'] = sr_task["notes"]

                if previous_task:
                    if previous_task.gc_id:
                        del db_data["gc_id"]
                    self.__default_env[constants.MAIL_ACTIVITY_MODEL].write(db_data, addons=db_data)
                    crt_resp["response"] = previous_task
                    self.__js_resp["updated"] += 1
                else:
                    crt_resp["response"] = self.__default_env[constants.MAIL_ACTIVITY_MODEL].create(db_data)
                    self.__js_resp["success"] += 1

                crt_resp["err_status"] = False
            else:
                crt_resp["response"] = constants.GL_TASKS_GET_PARTNER_NOT_FND
        except Exception as ex:
            self.__logging.exception("Create/Update Local Task Exception: " + str(ex))
            crt_resp["response"] = constants.GL_TASKS_CRT_EXCEPT
        return crt_resp

    def create_update_server_task(self, req_link, db_task, is_update=False, addons=None):
        crt_resp = {"err_status": True, "response": None}
        try:
            json_params = {
                "title": db_task.summary,
                "notes": re.sub(self.__clean_tags_re, '', db_task.note) if db_task.note else "default"
            }
            if "date_deadline" in db_task:
                if len(str(db_task["date_deadline"])) == 10:
                    json_params['due'] = str(db_task["date_deadline"]) + 'T00:00:00Z'
                else:
                    json_params['due'] = str(db_task["date_deadline"]).replace(' ', 'T')

            if is_update:
                gc_id = addons["id"]
                if db_task.gc_id:
                    gc_id = db_task.gc_id
                json_params["id"] = gc_id

                sr_resp = requests.put(
                    str(req_link + '/' + gc_id), data=json.dumps(json_params), headers=self.__req_headers).json()
                if constants.RESPONSE_ERROR_KEY in sr_resp:
                    json_params["id"] = addons["id"]
                    sr_resp = requests.put(
                        str(req_link + '/' + addons["id"]), data=json.dumps(json_params),
                        headers=self.__req_headers).json()

            else:
                sr_resp = requests.post(req_link, data=json.dumps(json_params), headers=self.__req_headers).json()

            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                upd_params = {"gc_etag": sr_resp["etag"], "gc_id": sr_resp["id"]}

                if is_update:
                    if db_task.gc_id:
                        del upd_params["gc_id"]

                    self.__js_resp["updated"] += 1
                else:
                    self.__js_resp["success"] += 1
                db_task.write(upd_params, addons=upd_params)
                crt_resp["response"] = sr_resp
                crt_resp["err_status"] = False

            else:
                crt_resp["response"] = constants.GL_TASKS_EXP_REC_ERR
        except Exception as ex:
            self.__logging.exception("Create/Update Server Task Exception: " + str(ex))
            crt_resp["response"] = constants.GL_TASKS_EXP_REC_EXCEPT
        return crt_resp

    def create_task(self, s2l_task=None, l2s_task=None):
        crt_resp = {"err_status": True, "response": None}
        try:
            if s2l_task:
                previous_tk_object = None
                chk_resp = self.check_task(s2l_task=s2l_task)
                if not chk_resp["err_status"]:
                    previous_tk_object = chk_resp["response"]
                crt_tmp_resp = self.create_update_local_task(sr_task=s2l_task, previous_task=previous_tk_object)
                if not crt_tmp_resp["err_status"]:
                    crt_resp["err_status"] = False
                crt_resp["response"] = crt_tmp_resp["response"]

            elif l2s_task:
                gt_tl_list_resp = self.get_serv_task_list_id()
                if not gt_tl_list_resp["err_status"]:
                    is_update, addons = False, None
                    req_url = self.__base_endpoint + self.__req_version + self.__tasks_details_api + '/' + \
                              gt_tl_list_resp["response"] + '/' + self.__default_service
                    chk_task_resp = self.check_task(l2s_task=l2s_task, l2s_req_link=req_url)
                    if not chk_task_resp["err_status"]:
                        is_update = True
                        addons = chk_task_resp["response"]

                    crt_tmp_resp = self.create_update_server_task(
                        req_link=req_url, db_task=l2s_task, is_update=is_update, addons=addons)
                    if not crt_tmp_resp["err_status"]:
                        crt_resp["err_status"] = False
                    crt_resp["response"] = crt_tmp_resp["response"]
                else:
                    crt_resp["response"] = constants.GL_TASKS_CRT_ERR
            else:
                crt_resp["response"] = constants.GL_TASKS_CRT_ERR
        except Exception as ex:
            self.__logging.exception("Create/Update either Server/Local Exception: " + str(ex))
            crt_resp["response"] = constants.GL_TASKS_CRT_EXCEPT
        return crt_resp

    def read_serv_tasks(self):
        self.reset_response()
        try:
            tl_task_resp = self.get_serv_task_list_id()
            if not tl_task_resp["err_status"]:
                tmp_task_items = []
                req_url = self.__base_endpoint + self.__req_version + self.__tasks_details_api +\
                          '/' + tl_task_resp["response"] + '/' + self.__default_service
                sr_resp = requests.get(req_url, headers=self.__req_headers).json()

                if len(sr_resp) > 0 and constants.RESPONSE_ERROR_KEY not in sr_resp:
                    if self.__initial_date and self.__end_date:
                        for each_task in sr_resp[constants.RESPONSE_ITEMS_KEY]:
                            conv_serv_dt = datetime.strptime(
                                str(each_task["updated"]).replace('T', ' ').split('.')[0],
                                constants.DEFAULT_DATETIME_FORMAT)

                            if self.__initial_date <= conv_serv_dt <= self.__end_date:
                                tmp_task_items.append(each_task)
                    else:
                        tmp_task_items = sr_resp[constants.RESPONSE_ITEMS_KEY]

                    if len(tmp_task_items) > 0:
                        self.__js_resp["response"] = tmp_task_items
                        self.__js_resp["total"] = len(tmp_task_items)
                        self.__js_resp["err_status"] = False
                    else:
                        self.__js_resp["response"] = constants.GL_TASKS_IMP_SERV_NOT_FND
                else:
                    self.__logging.info("Google Task Import Server Failed: " + str(sr_resp[constants.RESPONSE_ERROR_KEY
                                                                             ][constants.RESPONSE_MESSAGES_KEY]))
                    self.__js_resp["response"] = constants.GL_TASKS_IMP_SERV_REQ_ERR
            else:
                self.__js_resp["response"] = constants.GL_TASKS_IMP_SERV_FOLD_NT
        except Exception as ex:
            self.__logging.exception("Google Task Server Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_TASKS_IMP_SERV_EXCEPT

    def import_tasks(self):
        try:
            self.read_serv_tasks()
            if not self.__js_resp["err_status"]:
                for sr_task in self.__js_resp["response"]:
                    crt_resp = self.create_task(s2l_task=sr_task)
                    if crt_resp["err_status"]:
                        self.__js_resp["failed"] += 1
                        self.__logging.error("Unable to create/update task to Local: " + crt_resp["response"])

        except Exception as ex:
            self.__logging.exception("Task Import Exception: "+str(ex))
            self.__js_resp["response"] = constants.GL_TASKS_IMP_EXCEPT
        return self.__js_resp

    def export_serv_tasks(self, db_tasks):
        try:
            for _task in db_tasks:
                crt_resp = self.create_task(l2s_task=_task)
                if crt_resp["err_status"]:
                    self.__js_resp["failed"] += 1
                    self.__logging.exception("Create Server Task Error: " + crt_resp["response"])

        except Exception as ex:
            self.__logging.exception("Google Server Tasks Export Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_TASKS_EXP_SERV_EXCEPT

    def export_tasks(self):
        self.reset_response()
        try:
            filter_params = []
            get_partner_resp = self.get_db_partner_id()
            if not get_partner_resp["err_status"]:
                if self.__initial_date or self.__end_date:
                    filter_params.append('&')
                    filter_params.append('&')
                    filter_params.append(('write_date', '>=', str(self.__initial_date).replace('T', ' ')))
                    filter_params.append(('write_date', '<=', str(self.__end_date).replace('T', ' ')))
                filter_params.append(('res_id', '=', get_partner_resp["response"]))

                _db_tasks_data = self.__default_env[constants.MAIL_ACTIVITY_MODEL].search(
                    filter_params, order='write_date desc')
                if _db_tasks_data and len(_db_tasks_data) > 0:
                    self.export_serv_tasks(_db_tasks_data)
                    self.__js_resp["total"] = len(_db_tasks_data)
                    self.__js_resp["err_status"] = False
                else:
                    self.__js_resp["response"] = constants.GL_TASKS_EXP_REC_NOT_FND
            else:
                self.__js_resp["response"] = constants.GL_TASKS_GET_PARTNER_NOT_FND
        except Exception as ex:
            self.__logging.exception("Google Task Export Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_TASKS_EXP_EXCEPT
        return self.__js_resp
