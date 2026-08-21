from odoo import models, fields, api
from . import gmail_service
from . import constants
from . import utils
import logging
import base64


class MailMailExtend(models.Model):
    _inherit = constants.MAIL_MAIL_MODEL

    def send_mail(self, js_data, partner_id, mail_id):
        snd_resp = {"err_status": True, "response": None}
        try:
            db_ref_token = utils.get_db_token(self_env=self.env)
            if db_ref_token and len(db_ref_token) > 0:
                _gmail = gmail_service.GMailService(gl_access_token=db_ref_token[0], self_env=self.env)
                serv_response = _gmail.send_mail(json_params=js_data, partner_id=partner_id, mail_id=mail_id)
                if not serv_response["err_status"]:
                    snd_resp["err_status"] = False
                else:
                    snd_resp["response"] = "Log >> " + str(serv_response["response"])
            else:
                snd_resp["response"] = "Log >> Unable to find credentials"
        except Exception as ex:
            snd_resp["response"] = "Log >> Oops, Mail could not be sent: " + str(ex)
        return snd_resp

    @api.model
    def create(self, values):
        mail_rec = super(MailMailExtend, self).create(values)

        _logging = logging.getLogger(__name__)
        pop_message = ""
        try:
            _serv_data = {
                "subject": values["subject"],
                "content": values["body_html"],
                "emails": [],
                "attachments": []
            }
            query = "select res_partner_id from mail_mail_res_partner_rel where mail_mail_id=" + str(mail_rec.id)
            self.env.cr.execute(query)
            partner = self.env.cr.fetchone()

            if partner or len(partner) > 0:
                contact = self.env[constants.RES_PARTNER_MODEL].search([("id", "=", partner[0])])
                if contact and len(contact) > 0:
                    _serv_data["emails"].append({"email": contact.email})

                    at_query = "select attachment_id from " + constants.MAIL_MESSAGE_ATTACH_MODEL +\
                               " where message_id=" + str(mail_rec.mail_message_id.id)
                    self.env.cr.execute(at_query)
                    mail_attachment = self.env.cr.fetchall()

                    if mail_attachment and len(mail_attachment) > 0:
                        for attachment in mail_attachment:
                            file_attach = self.env[constants.IR_ATTACHMENT_MODEL].search([("id", "=", attachment[0])])
                            decoded_data = base64.b64decode(file_attach.datas)
                            _serv_data["attachments"].append({
                                "id": file_attach.id,
                                "name": file_attach.name,
                                "mimetype": file_attach.mimetype,
                                "db_datas": decoded_data
                            })

                    _response = self.send_mail(js_data=_serv_data, partner_id=partner[0], mail_id=mail_rec)
                    if not _response["err_status"]:
                        self.env[constants.MAIL_RESEND_MESSAGE_MODEL].cancel_mail_action()
                        pop_message += "Log >> Mail sent successfully"
                    else:
                        pop_message += "Log >> " + str(_response["response"])
                else:
                    pop_message += "Log >> Oops, Unable to get sender information."
        except Exception as ex:
            pop_message += "Log >> Oops, Exception found, " + str(ex)
        return mail_rec
