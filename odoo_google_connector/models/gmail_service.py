from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from . import constants
from datetime import *
import logging
import requests
import base64
import json


class GMailService:
    def __init__(self, gl_access_token, self_env, default_email=None, initial_date=None, end_date=None):
        self.__logging = logging.getLogger(__name__)

        self.__gl_access_token = gl_access_token
        self.__self_env = self_env
        self.__default_mail = default_email
        self.__initial_date = initial_date
        self.__end_date = end_date
        self.__req_version = constants.GL_MAILS_VERSION
        self.__req_timeout = constants.GL_REQ_TIMEOUT

        self.__base_endpoint = constants.GL_BASE_URL.replace(
            constants.GL_SERVICE_REPLACER, constants.GL_MAILS_SERVICE) + constants.GL_MAILS_SERVICE + '/'
        self.__sbase_endpoint = constants.GL_BASE_URL.replace(
            constants.GL_SERVICE_REPLACER, constants.GL_MAILS_SERVICE) + 'upload/' + constants.GL_MAILS_SERVICE + '/'

        self.__get_folder_api = constants.GL_MAILS_FOLDER.replace('{{google_id}}', 'me')
        self.__get_attachment_api = constants.GL_MAILS_ATTACHMENT.replace('{{google_id}}', 'me')
        self.__send_mail_api = constants.GL_MAILS_SEND_MAIL
        self.__max_page = constants.GL_MAILS_MAX_PAGES

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

    def send_mail(self, json_params, partner_id=None, mail_id=None):
        self.reset_response()
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__get_folder_api + self.__send_mail_api
            if len(json_params["attachments"]) > 0:
                self.__req_headers["Content-Type"] = "message/rfc822"

                message = MIMEMultipart()
                message['To'] = json_params["emails"][0]["email"]
                message['Subject'] = json_params["subject"]
                msg = MIMEText(json_params["content"], 'html')
                message.attach(msg)

                for attach_file in json_params["attachments"]:
                    main_type, sub_type = attach_file["mimetype"].split('/')
                    cfile = attach_file["db_datas"]

                    if main_type == 'text':
                        msg = MIMEText(cfile.decode('utf-8'), _subtype=sub_type)
                    elif main_type == 'image':
                        msg = MIMEImage(cfile, _subtype=sub_type)
                    elif main_type == 'audio':
                        msg = MIMEAudio(cfile, _subtype=sub_type)
                    elif main_type in ['zip', 'exe', 'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xlsx']:
                        msg = MIMEApplication(cfile, _subtype=sub_type)
                    else:
                        msg = MIMEBase(main_type, sub_type)
                        msg.set_payload(cfile)
                    msg.add_header('Content-Disposition', 'attachment', filename=attach_file["name"])
                    message.attach(msg)
            else:
                self.__req_headers["Content-Type"] = 'application/json'

                message = MIMEText(json_params["content"], 'html')
                message['to'] = json_params["emails"][0]["email"]
                message['subject'] = json_params["subject"]

            _params = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}
            sr_resp = requests.post(req_url, data=json.dumps(_params), headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                '''
                if mail_id and partner_id:
                    chk_exist_rec = self.__self_env[constants.MAIL_NOTIFICATION_MODEL].search([
                        '&', ('res_partner_id', '=', partner_id), ("mail_message_id", '=', mail_id.message_id)
                    ])
                    if chk_exist_rec and len(chk_exist_rec) > 0:
                        chk_exist_rec[0].write({"notification_status": "sent"})
                    else:
                        self.__logging.info("Mail Status: Unable to find object for status updation")
                '''
                self.__js_resp["response"] = sr_resp
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGES_KEY]
        except Exception as ex:
            self.__logging.exception("Mail send Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_MAILS_SEND_MAIL_EXCEPT
        return self.__js_resp

    def get_mail_detail_by_id(self, mail_id):
        gt_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__get_folder_api + '/' + mail_id
            if "Content-Type" not in self.__req_headers:
                self.__req_headers["Content-Type"] = 'application/json'
            mail_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in mail_resp:
                gt_resp["response"] = mail_resp
                gt_resp["err_status"] = False
            else:
                gt_resp["response"] = constants.GL_MAILS_IMP_SERV_MLD_ERR
        except Exception as ex:
            self.__logging.exception("Mails page exception found: " + str(ex))
            gt_resp["response"] = constants.GL_MAILS_IMP_SERV_MLD_EXCEPT
        return gt_resp

    def get_mails_by_next_page(self, ng_token=None):
        gt_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__get_folder_api
            if self.__initial_date and self.__end_date:
                req_url += "?q=after:" + str(int(datetime.timestamp(self.__initial_date))) + " before:" + \
                           str(int(datetime.timestamp(self.__end_date)))
            if ng_token:
                if '?' in req_url:
                    req_url += "&"
                else:
                    req_url += '?'
                req_url += 'pageToken=' + ng_token

            mail_fld_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in mail_fld_resp:
                gt_resp["response"] = mail_fld_resp
                gt_resp["err_status"] = False
            else:
                gt_resp["response"] = constants.GL_MAILS_IMP_SERV_PG_ERR
        except Exception as ex:
            self.__logging.exception("Mails page exception found: " + str(ex))
            gt_resp["response"] = constants.GL_MAILS_IMP_SERV_PG_EXCEPT
        return gt_resp

    def download_attachment(self, mail_id, attachment_id):
        dwn_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__get_attachment_api.replace(
                "{{message_id}}", mail_id).replace("{{attach_id}}", attachment_id)
            serv_attach_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in serv_attach_resp:
                dwn_resp["response"] = serv_attach_resp
                dwn_resp["err_status"] = False
            else:
                dwn_resp["response"] = constants.GL_MAILS_IMP_SERV_ATCH_ERR
        except Exception as ex:
            self.__logging.exception("Mails attachment exception: " + str(ex))
            dwn_resp["response"] = constants.GL_MAILS_IMP_SERV_ATCH_EXCEPT
        return dwn_resp

    def read_serv_mails(self):
        try:
            max_page, next_page_token = self.__max_page, None
            tmp_mail_ids, tmp_mail_details = [], []
            while max_page > 0:
                resp = self.get_mails_by_next_page(next_page_token)
                if not resp['err_status']:
                    if 'messages' in resp["response"]:
                        for ml_recd in resp["response"]["messages"]:
                            tmp_mail_ids.append(ml_recd)
                        if "nextPageToken" in resp["response"]:
                            next_page_token = resp["response"]["nextPageToken"]
                        else:
                            break
                max_page -= 1

            if len(tmp_mail_ids) > 0:
                for mail_id in tmp_mail_ids:
                    mail_resp = self.get_mail_detail_by_id(mail_id["id"])
                    if 'error' not in mail_resp:
                        if constants.GL_MAILS_FOLDER_NAME in mail_resp['response']['labelIds']:
                            mail_details, vld_range = {}, False
                            message_data = None

                            if 'parts' in mail_resp["response"]["payload"]:
                                for mail_prt in mail_resp["response"]["payload"]["parts"]:
                                    if mail_prt["mimeType"] == constants.GL_MAILS_MESSAGE_PART_TYPE\
                                            and mail_prt["filename"] == "":
                                        message_data = str(mail_prt["body"]["data"]).strip()
                                    elif mail_prt["filename"] != "":
                                        dn_resp = self.download_attachment(
                                            mail_id=mail_id["id"], attachment_id=mail_prt["body"]["attachmentId"])
                                        if not dn_resp["err_status"]:
                                            serv_file_object = {
                                                "filename": mail_prt["filename"],
                                                "mimetype": mail_prt["mimeType"],
                                                "body": dn_resp["response"]["data"],
                                                "size": dn_resp["response"]["size"],
                                            }
                                            if 'attachments' in mail_details:
                                                mail_details["attachments"].append(serv_file_object)
                                            else:
                                                mail_details["attachments"] = [serv_file_object]
                            else:
                                message_data = mail_resp["response"]["payload"]["body"]["data"]

                            if message_data and len(message_data) % 4 != 0:
                                reminder_val = message_data % 4
                                message_data = message_data[0: len(message_data) - reminder_val]

                            try:
                                if message_data:
                                    mail_details.setdefault(
                                        'message', base64.urlsafe_b64decode(
                                            message_data).decode("utf-8").replace('\r\n', ' '))
                                else:
                                    mail_details["message"] = ""
                            except Exception as ex:
                                self.__logging.exception("Gmail Params exception: " + str(ex))
                                mail_details.setdefault("message", "")

                            for header in mail_resp["response"]["payload"]["headers"]:
                                if header["name"] == "From":
                                    email_address = header["value"].encode('ascii').decode('unicode-escape')
                                    mail_details.setdefault("sender", email_address)

                                elif header["name"] == "Subject":
                                    mail_details.setdefault("subject", header["value"])
                            tmp_mail_details.append(mail_details)

                self.__js_resp["total"] = len(tmp_mail_details)
                self.__js_resp["response"] = tmp_mail_details
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = constants.GL_MAILS_IMP_SERV_NOTFND
        except Exception as ex:
            self.__logging.exception("Serv Mail Import Exception: "+str(ex))
            self.__js_resp["response"] = constants.GL_MAILS_IMP_EXCEPT

    def get_partner_id_by_mail(self, sr_mail):
        gt_resp = {"err_status": True, "response": None}
        try:
            sender_info = sr_mail["sender"].split('<')
            sender_name, sender_email = sender_info[0].strip(), ""

            if len(sender_info) > 1:
                sender_email += sender_info[1].split('>')[0]

            partner_id = self.__self_env[constants.RES_PARTNER_MODEL].search([('email', '=', sender_email)])
            if partner_id and len(partner_id) > 0:
                pass
            else:
                partner_id = self.__self_env[constants.RES_PARTNER_MODEL].create_contact(sender_email, sender_name)

            gt_resp["response"] = [sender_email, partner_id[0].id]
            gt_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Get PartnerID Exception: " + str(ex))
            gt_resp["response"] = constants.GL_MAILS_CHK_EXCEPT
        return gt_resp

    def check_mail(self, sr_mail):
        chk_resp = {"err_status": True, "response": None}
        try:
            db_partner_id, filter_params = [], []
            gt_partner_resp = self.get_partner_id_by_mail(sr_mail)
            if not gt_partner_resp["err_status"]:
                db_partner_id = gt_partner_resp["response"]

            if len(db_partner_id) > 0:
                filter_params.append('&')
                filter_params.append(('res_id', '=', db_partner_id[1]))
            filter_params.append(('subject', '=', sr_mail["subject"]))

            chk_db_mail_exist = self.__self_env[constants.MAIL_MESSAGE_MODEL].search(filter_params)
            if chk_db_mail_exist and len(chk_db_mail_exist) > 0:
                chk_resp["response"] = chk_db_mail_exist[0]
                chk_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Check Local Mail Exception: " + str(ex))
            chk_resp["response"] = constants.GL_MAILS_CHK_EXCEPT
        return chk_resp

    def create_update_local_mail(self, sr_mail, previous_mail=None):
        crt_resp = {"err_status": True, "response": None}
        try:
            partner_info = []
            gt_partner_id = self.get_partner_id_by_mail(sr_mail)
            if not gt_partner_id["err_status"]:
                partner_info = gt_partner_id["response"]

            db_params = {
                'subject': sr_mail["subject"],
                'author_id': self.__self_env.user.partner_id.id,
                'model': 'res.partner',
                'message_type': 'notification',
                'body': sr_mail["message"],
                'is_internal': True,
            }
            if len(partner_info) > 0:
                db_params["email_from"] = partner_info[0]
                db_params["res_id"] = partner_info[1]

            if previous_mail:
                previous_mail.write(db_params)
                current_mail_object = previous_mail
                self.__js_resp["updated"] += 1
            else:
                current_mail_object = self.__self_env[constants.MAIL_MESSAGE_MODEL].create(db_params)
                self.__js_resp["success"] += 1

            crt_resp["response"] = current_mail_object
            crt_resp["err_status"] = False

            if "attachments" in sr_mail and len(sr_mail["attachments"]) > 0:
                self.__self_env.cr.execute(
                    "delete from " + constants.MAIL_MESSAGE_ATTACH_MODEL + " where message_id=" +
                    str(current_mail_object.id)
                )

                for attachment in sr_mail["attachments"]:
                    save_rec = self.__self_env[constants.IR_ATTACHMENT_MODEL].create({
                        'name': attachment["filename"],
                        'datas': attachment["body"].replace("-", "+").replace("_", "/"),
                        'mimetype': attachment["mimetype"],
                        'type': 'binary',
                        'res_model': constants.RES_PARTNER_MODEL,
                        'res_id': 0,
                    })

                    self.__self_env.cr.execute(
                        "insert into " + constants.MAIL_MESSAGE_ATTACH_MODEL + " (message_id, attachment_id) values (" +
                        str(current_mail_object.id) + "," + str(save_rec.id) + ")"
                    )
        except Exception as ex:
            self.__logging.exception("Create Local Mail Exception: " + str(ex))
        return crt_resp

    def import_mails(self):
        self.reset_response()
        try:
            self.read_serv_mails()
            if not self.__js_resp["err_status"]:
                for serv_mail in self.__js_resp["response"]:
                    prev_mail_object = None

                    chk_mail_exist = self.check_mail(sr_mail=serv_mail)
                    if not chk_mail_exist["err_status"]:
                        prev_mail_object = chk_mail_exist["response"]

                    crt_resp = self.create_update_local_mail(sr_mail=serv_mail, previous_mail=prev_mail_object)
                    if crt_resp["err_status"]:
                        self.__js_resp["failed"] += 1
                        self.__logging.error("Create Mail Error: " + crt_resp["response"])
            else:
                self.__js_resp["response"] = constants.GL_MAILS_IMP_SERV_ERR
        except Exception as ex:
            self.__logging.exception("Outer Error Mail Import: " + str(ex))
            self.__js_resp["response"] = constants.GL_MAILS_IMP_EXCEPT
        return self.__js_resp
