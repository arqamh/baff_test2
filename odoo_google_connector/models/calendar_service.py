from . import constants
from dateutil import tz
from datetime import *
import requests
import logging
import random
import string
import json
import re


class CalenderService:
    def __init__(self, gl_access_token, self_env, default_profile, initial_date=None, end_date=None):
        self.__logging = logging.getLogger(__name__)

        self.__gl_access_token = gl_access_token
        self.__initial_date = initial_date
        self.__end_date = end_date
        self.__self_env = self_env
        self.__from_zone = tz.tzutc()
        self.__to_zone = tz.tzlocal()

        self.__default_profile = default_profile
        if type(self.__default_profile) == tuple:
            self.__default_profile = self.__default_profile[0]

        self.__req_version = constants.GL_CALENDAR_SERVICE_VERSION
        self.__req_timeout = constants.GL_REQ_TIMEOUT
        self.__calendar_service = constants.GL_CALENDAR_DRIVE_SERVICE
        self.__calendar_version = constants.GL_CALENDAR_SERVICE_VERSION

        self.__base_endpoint = constants.GL_BASE_URL.replace('{{service}}', self.__calendar_service)
        self.__crud_events_link = constants.GL_CALENDAR_CRUD_LINK.replace(
            '{{version}}', self.__calendar_version).replace(
            '{{google_id}}',
            self.__default_profile[constants.GL_PROFILE_EMAIL_FD][0][constants.GL_PROFILE_EMAIL_FD_INTERNAL])

        self.__clean_tags_re = re.compile('<.*?>')
        self.__req_headers = {
            "Authorization": "Bearer " + self.__gl_access_token,
            "Content-Type": 'application/json'
        }
        self.__buffer_events = []
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

    def get_organizer_id(self, serv_organizer):
        organizer_id = self.__self_env[constants.RES_PARTNER_MODEL].search([
            ("email", '=', serv_organizer["email"])
        ])
        if organizer_id and len(organizer_id) > 0:
            organizer_id = organizer_id[0].id
        else:
            organizer_id = self.__self_env[constants.RES_PARTNER_MODEL].create_contact(serv_organizer["email"]).id
        return organizer_id

    def get_datetime_conv_format(self, sr_start_date, sr_end_date):
        start_date_ob, end_date_ob = sr_start_date, sr_end_date
        try:
            if 'date' in start_date_ob:
                start_date_ob = datetime.strptime(
                    start_date_ob["date"], constants.DEFAULT_DATETIME_FORMAT.split(' ')[0])
                end_date_ob = datetime.strptime(
                    end_date_ob["date"], constants.DEFAULT_DATETIME_FORMAT.split(' ')[0])
            else:
                if '+' in start_date_ob["dateTime"]:
                    post = str(start_date_ob["dateTime"]).split('+')[1]

                    start_date_ob = str(start_date_ob["dateTime"]).replace('T', ' ').split('+')[0]
                    end_date_ob = str(end_date_ob["dateTime"]).replace('T', ' ').split('+')[0]
                    start_date_ob = datetime.strptime(
                        start_date_ob, constants.DEFAULT_DATETIME_FORMAT) - timedelta(
                        hours=int(post[:2]), minutes=int(post[2:4]) if ':' not in post[2:4] else
                        int(post[3:5]))
                    end_date_ob = datetime.strptime(
                        end_date_ob, constants.DEFAULT_DATETIME_FORMAT) - timedelta(
                        hours=int(post[:2]), minutes=int(post[2:4]) if ':' not in post[2:4] else
                        int(post[3:5]))

                elif '-' in start_date_ob["dateTime"]:
                    negative = str(start_date_ob["dateTime"]).split('-')[1]

                    start_date_ob = str(start_date_ob["dateTime"]).replace('T', ' ').split('-')[0]
                    end_date_ob = str(end_date_ob["dateTime"]).replace('T', ' ').split('-')[0]

                    start_date_ob = datetime.strptime(
                        start_date_ob, constants.DEFAULT_DATETIME_FORMAT) + timedelta(
                        hours=int(negative[:2]), minutes=int(negative[2:4]) if ':' not in
                                                                               negative[2:4] else
                        int(negative[3:5]))
                    end_date_ob = datetime.strptime(
                        end_date_ob, constants.DEFAULT_DATETIME_FORMAT) + timedelta(
                        hours=int(negative[:2]), minutes=int(negative[2:4]) if ':' not in
                                                                               negative[2:4] else
                        int(negative[3:5]))
                else:
                    start_date_ob = str(start_date_ob["dateTime"]).replace('T', ' ').split('.')[0]
                    end_date_ob = str(end_date_ob["dateTime"]).replace('T', ' ').split('.')[0]

                    start_date_ob = datetime.strptime(
                        start_date_ob, constants.DEFAULT_DATETIME_FORMAT)
                    end_date_ob = datetime.strptime(
                        end_date_ob, constants.DEFAULT_DATETIME_FORMAT)
        except Exception as ex:
            self.__logging.exception("Datetime Format Conversion Exception: " + str(ex))
        return start_date_ob, end_date_ob

    def delete_event(self, gc_id):
        del_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__crud_events_link + '/' + gc_id
            sr_resp = requests.delete(req_url, headers=self.__req_headers, timeout=self.__req_timeout)
            if sr_resp.content == '':
                del_resp["err_status"] = False
            else:
                del_resp["response"] = sr_resp.json()[constants.RESPONSE_ERROR_KEY]
        except Exception as ex:
            self.__logging.exception("Delete Calendar Event Exception: " + str(ex))
            del_resp["response"] = constants.GL_CALENDAR_DEL_EXCEPT
        return del_resp

    def get_serv_event_by_id(self, gc_id):
        get_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__crud_events_link + '/' + gc_id
            sr_resp = requests.get(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                get_resp["response"] = sr_resp
                get_resp["err_status"] = False
            else:
                get_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY]
        except Exception as ex:
            self.__logging.exception("Get Calendar Event Exception: " + str(ex))
            get_resp["response"] = constants.GL_CALENDAR_DEL_EXCEPT
        return get_resp

    def check_event(self, s2l_event=None, l2s_event=None):
        chk_resp = {
            "err_status": True,
            "response": None,
            "addons": None
        }
        try:
            if s2l_event:
                calendar_rec = self.__self_env[constants.CALENDAR_EVENT_MODEL].search([
                    ('name', '=', s2l_event["summary"])
                ])
                if calendar_rec and len(calendar_rec) > 0:
                    chk_resp["response"] = calendar_rec[0]
                    chk_resp["err_status"] = False
            elif l2s_event:
                if l2s_event.gc_id:
                    chk_tmp_resp = self.get_serv_event_by_id(gc_id=l2s_event.gc_id)
                    if not chk_tmp_resp["err_status"]:
                        chk_resp["response"] = chk_tmp_resp["response"]
                        chk_resp["addons"] = chk_tmp_resp["response"]
                        chk_resp["err_status"] = False

                if chk_resp["err_status"]:
                    req_url = self.__base_endpoint + self.__crud_events_link
                    filter_params = {'orderBy': 'updated', 'q': l2s_event.name}
                    sr_resp = requests.get(req_url, params=filter_params, headers=self.__req_headers).json()
                    if constants.RESPONSE_ERROR_KEY not in sr_resp:
                        if constants.RESPONSE_ITEMS_KEY in sr_resp and len(sr_resp[constants.RESPONSE_ITEMS_KEY]) > 0:
                            chk_resp["response"] = sr_resp[constants.RESPONSE_ITEMS_KEY][0]
                            chk_resp["addons"] = sr_resp[constants.RESPONSE_ITEMS_KEY][0]
                            chk_resp["err_status"] = False
                        else:
                            chk_resp["response"] = "No events found"
                    else:
                        chk_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGES_KEY]
                else:
                    chk_resp["response"] = constants.GL_CALENDAR_CHK_ERR

            else:
                chk_resp["response"] = constants.GL_CALENDAR_CHK_ERR
        except Exception as ex:
            self.__logging.exception("Check Calendar Event Exception: " + str(ex))
            chk_resp["response"] = constants.GL_CALENDAR_CHK_EXCEPT
        return chk_resp

    def create_update_local_event(self, sr_event, previous_event):
        crt_resp = {"err_status": True, "response": None}
        try:
            partner_ids = []
            if 'attendees' in sr_event and len(sr_event["attendees"]) > 0:
                for ev_user in sr_event["attendees"]:
                    partner = self.__self_env[constants.RES_PARTNER_MODEL].search([("email", '=', ev_user["email"])])
                    if partner and len(partner) > 0:
                        partner_ids.append((constants.GL_CALENDAR_PARTNER_REL_ID, partner.id))
                    else:
                        partner = self.__self_env[constants.RES_PARTNER_MODEL].create_contact(ev_user["email"])
                        partner_ids.append((constants.GL_CALENDAR_PARTNER_REL_ID, partner.id))

            start_date_ob, end_date_ob = self.get_datetime_conv_format(
                sr_start_date=sr_event["start"], sr_end_date=sr_event["end"])

            db_params = {
                "name": sr_event["summary"],
                "description": sr_event["description"] if "description" in sr_event else "",
                "start": start_date_ob,
                "stop": end_date_ob,
                "location": sr_event["location"] if "location" in sr_event else "",
                "partner_ids": partner_ids if len(partner_ids) > 0 else [],
                "gc_id": sr_event["id"],
                "gc_etag": sr_event["etag"],
                "status": sr_event["status"],
                "organizer_id": self.get_organizer_id(sr_event["organizer"]),
            }

            if "conferenceData" in sr_event:
                db_params["meet_link"] = sr_event["conferenceData"]["entryPoints"][0]["uri"],
                db_params["videocall_location"] = sr_event["conferenceData"]["entryPoints"][0]["uri"],
                db_params["meet_code"] = sr_event["conferenceData"]["conferenceId"]

            if previous_event:
                if previous_event.gc_id:
                    del db_params["gc_id"]
                previous_event.write(values=db_params, addons=db_params)
                crt_resp["response"] = previous_event
                self.__js_resp["updated"] += 1
            else:
                crt_resp["response"] = self.__self_env[constants.CALENDAR_EVENT_MODEL].create(db_params)
                self.__js_resp["success"] += 1

            try:
                if "reminders" in sr_event and sr_event["reminders"] and "overrides" in sr_event["reminders"]:
                    tmp_alarm_ids = []
                    mail_template_id = self.__self_env[constants.MAIL_TEMPLATE_MODEL].search([])[0].id

                    for remind in sr_event["reminders"]["overrides"]:
                        filter_params = [
                            '&', '&', '&', ('interval', '=', 'minutes'),
                            ('duration', '=', remind["minutes"]), ('mail_template_id', '=', mail_template_id)
                        ]
                        if remind["method"] == "popup":
                            filter_params.append(('alarm_type', '=', 'notification'))
                            sel_type = "notification"
                        elif remind["method"] == "email":
                            filter_params.append(('alarm_type', '=', 'email'))
                            sel_type = "email"
                        else:
                            filter_params.append(('alarm_type', '=', 'sms'))
                            sel_type = "sms"

                        chk_exist_resp = self.__self_env[constants.CALENDAR_ALARM_MODEL].search(filter_params)
                        if chk_exist_resp and len(chk_exist_resp):
                            tmp_alarm_ids.append(chk_exist_resp[0].id)
                        else:
                            crt_alarm_id = self.__self_env[constants.CALENDAR_ALARM_MODEL].create({
                                'interval': 'minutes',
                                'duration': remind["minutes"],
                                'mail_template_id': mail_template_id,
                                'alarm_type': sel_type
                            }).id
                            tmp_alarm_ids.append(crt_alarm_id)

                    if len(tmp_alarm_ids) > 0:
                        self.__self_env[constants.CALENDAR_EVENT_MODEL].write(
                            values=(1, crt_resp["response"].id, {"alarm_ids": tmp_alarm_ids}), addons=crt_resp["response"].id
                        )
            except Exception as ex:
                self.__logging.exception("Local Calendar Event Reminder Exception: " + str(ex))

            crt_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Create/Update Calendar Event Local Exception : " + str(ex))
            crt_resp["response"] = constants.GL_CALENDAR_CRT_EXCEPT
        return crt_resp

    def create_update_server_event(self, db_event, is_update=False, addons=None):
        crt_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__crud_events_link
            default_app_sam = [{
                "displayName": self.__default_profile[constants.GL_PROFILE_NAME_FD][0][
                    constants.GL_PROFILE_NAME_FD_INTERNAL],
                "email": self.__default_profile[constants.GL_PROFILE_EMAIL_FD][0][
                    constants.GL_PROFILE_EMAIL_FD_INTERNAL]
            }]

            tmp_event_attends = []
            for attend in db_event.partner_ids:
                tmp_event_attends.append({
                    "displayName": attend.name,
                    "email": attend.email
                })

            json_params = {
                "summary": db_event.name,
                "location": db_event.location,
                "description": re.sub(self.__clean_tags_re, '', str(db_event.description)) if db_event.description else "",
                "start": {"dateTime": str(db_event.start).replace(' ', 'T') + 'Z'},
                "end": {"dateTime": str(db_event.stop).replace(' ', 'T') + 'Z'},
                "attendees": tmp_event_attends if len(tmp_event_attends) > 0 else default_app_sam,
                "status": db_event.status,
                "conferenceData": {
                    "createRequest": {
                        "requestId": ''.join(random.choice(string.ascii_letters) for i in range(12)),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                        "status": {"statusCode": "success"}
                    }
                },
            }

            try:
                if db_event.alarm_ids and len(db_event.alarm_ids) > 0:
                    json_params["reminders"] = {
                        "useDefault": False,
                        "overrides": []
                    }
                    for _alarm in db_event.alarm_ids:
                        if _alarm.alarm_type == "notification":
                            method_type = "popup"
                        elif _alarm.alarm_type == "email":
                            method_type = "email"
                        else:
                            method_type = "sms"

                        duration_mins = _alarm.duration
                        if _alarm.interval == "hours":
                            duration_mins *= 60
                        elif _alarm.interval == "days":
                            duration_mins *= (60 * 24)
                        json_params["reminders"]["overrides"].append({
                            "method": method_type,
                            "minutes": duration_mins
                        })
            except Exception as ex:
                self.__logging.exception("Server Event Reminder Exception: " + str(ex))

            req_query_params = {"conferenceDataVersion": 1}
            if is_update:
                # del json_params["conferenceData"]
                json_params["etag"] = db_event.gc_etag
                if not db_event.gc_etag:
                    json_params["etag"] = addons["etag"]

                if db_event.gc_id:
                    req_url += "/" + db_event.gc_id
                else:
                    req_url += "/" + addons["id"]

                sr_resp = requests.put(req_url, params=req_query_params, data=json.dumps(json_params),
                                       headers=self.__req_headers).json()
            else:
                sr_resp = requests.post(req_url, params=req_query_params, data=json.dumps(json_params),
                                        headers=self.__req_headers).json()

            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                if is_update:
                    self.__js_resp["updated"] += 1
                else:
                    self.__js_resp["success"] += 1
                crt_resp["err_status"] = False
                crt_resp["response"] = sr_resp

                update_params = {
                    "gc_id": sr_resp["id"],
                    "gc_etag": sr_resp["etag"],
                    "status": sr_resp["status"],
                    "organizer_id": self.get_organizer_id(sr_resp["organizer"]),
                    "meet_link": sr_resp["conferenceData"]["entryPoints"][0]["uri"] if "conferenceData" in sr_resp else "",
                    "videocall_location": sr_resp["conferenceData"]["entryPoints"][0]["uri"] if "conferenceData" in sr_resp else "",
                    "meet_code": sr_resp["conferenceData"]["conferenceId"] if "conferenceData" in sr_resp else ""
                }
                if db_event.gc_id:
                    del update_params["gc_id"]
                db_event.write(values=update_params, addons=update_params)

            else:
                crt_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY]
        except Exception as ex:
            self.__logging.exception("Create/Update Calendar Event Server Exception : " + str(ex))
            crt_resp["response"] = constants.GL_CALENDAR_CRT_EXCEPT
        return crt_resp

    def create_event(self, s2l_event=None, l2s_event=None):
        crt_resp = {"err_status": True, "response": None}
        try:
            if s2l_event:
                tmp_previous_event = None
                chk_resp = self.check_event(s2l_event=s2l_event)
                if not chk_resp["err_status"]:
                    tmp_previous_event = chk_resp["response"]
                crt_tmp_resp = self.create_update_local_event(sr_event=s2l_event, previous_event=tmp_previous_event)
                if not crt_tmp_resp["err_status"]:
                    crt_resp["response"] = crt_tmp_resp["response"]
                    crt_resp["err_status"] = False
                else:
                    crt_resp["response"] = constants.GL_CALENDAR_CRT_ERR

            elif l2s_event:
                is_update, addons = False, None
                chk_resp = self.check_event(l2s_event=l2s_event)
                if not chk_resp["err_status"]:
                    is_update = True
                    addons = chk_resp["addons"]
                crt_tmp_resp = self.create_update_server_event(db_event=l2s_event, is_update=is_update, addons=addons)
                if not crt_tmp_resp["err_status"]:
                    crt_resp["response"] = crt_tmp_resp["response"]
                    crt_resp["err_status"] = False
                else:
                    crt_resp["response"] = constants.GL_CALENDAR_CRT_ERR

            else:
                crt_resp["response"] = constants.GL_CALENDAR_CRT_ERR
        except Exception as ex:
            self.__logging.exception("Create Calendar Event Local/Server Exception : " + str(ex))
            crt_resp["response"] = constants.GL_CALENDAR_CRT_EXCEPT
        return crt_resp

    def read_serv_events(self):
        try:
            tmp_calendar_events = []
            filter_params = {'orderBy': 'updated'}
            req_url = self.__base_endpoint + self.__crud_events_link

            while True:
                sr_resp = requests.get(req_url, params=filter_params, headers=self.__req_headers).json()
                if constants.RESPONSE_ERROR_KEY not in sr_resp:
                    if constants.RESPONSE_ITEMS_KEY in sr_resp and len(sr_resp[constants.RESPONSE_ITEMS_KEY]) > 0:
                        if self.__initial_date and self.__end_date:
                            for sr_event in sr_resp[constants.RESPONSE_ITEMS_KEY]:
                                event_crt_date = str(sr_event["updated"]).replace('T', ' ').split('.')[0]
                                convert_dt = datetime.strptime(event_crt_date, constants.DEFAULT_DATETIME_FORMAT)
                                if self.__initial_date <= convert_dt <= self.__end_date:
                                    tmp_calendar_events.append(sr_event)
                        else:
                            tmp_calendar_events += sr_resp[constants.RESPONSE_ITEMS_KEY]
                    else:
                        self.__js_resp["response"] = constants.GL_CALENDAR_IMP_SERV_NOT_FND
                        break

                    if "nextPageToken" in sr_resp:
                        filter_params["pageToken"] = sr_resp["nextPageToken"]
                    else:
                        break
                else:
                    break

            if len(tmp_calendar_events) > 0:
                self.__js_resp["total"] = len(tmp_calendar_events)
                self.__js_resp["response"] = tmp_calendar_events
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGES_KEY]
        except Exception as ex:
            self.__logging.exception("Calendar Server Read Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CALENDAR_IMP_SERV_EXCEPT

    def import_events(self):
        self.reset_response()
        try:
            self.read_serv_events()
            if not self.__js_resp["err_status"]:
                for sr_event in self.__js_resp["response"]:
                    crt_resp = self.create_event(s2l_event=sr_event)
                    if crt_resp["err_status"]:
                        self.__js_resp["failed"] += 1
                        self.__logging.info("Unable to create/update Local event: " + crt_resp["response"])
        except Exception as ex:
            self.__logging.exception("Calendar Event Import Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CALENDAR_IMP_EXCEPT
        return self.__js_resp

    def write_serv_events(self, db_data):
        try:
            for db_event in db_data:
                crt_resp = self.create_event(l2s_event=db_event)
                if crt_resp["err_status"]:
                    self.__js_resp["failed"] += 1
                    self.__logging.info("Unable to create/update Server event: " + crt_resp["response"])
        except Exception as ex:
            self.__logging.exception("Calendar Export Server Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CALENDAR_EXP_SERV_EXCEPT

    def export_events(self):
        self.reset_response()
        try:
            filter_params = []
            if self.__initial_date and self.__end_date:
                filter_params.append('&')
                filter_params.append(('write_date', '>=', str(self.__initial_date).replace('T', ' ')))
                filter_params.append(('write_date', '<=', str(self.__end_date).replace('T', ' ')))

            _db_calendar_recs = self.__self_env[constants.CALENDAR_EVENT_MODEL].search(filter_params)
            if _db_calendar_recs and len(_db_calendar_recs) > 0:
                self.write_serv_events(db_data=_db_calendar_recs)
                self.__js_resp["total"] = len(_db_calendar_recs)
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = constants.GL_CALENDAR_EXP_NT_RCD
        except Exception as ex:
            self.__logging.exception("Export Calendar Events Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CALENDAR_EXP_EXCEPT
        return self.__js_resp
