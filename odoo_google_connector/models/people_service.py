from . import connection
from . import constants
from datetime import *
import requests
import logging
import base64
import pytz
import json
import re


class PeopleService:
    def __init__(self, gl_access_token, default_env, initial_date=None, end_date=None):
        self.__logging = logging.getLogger(__name__)

        self.__gl_access_token = gl_access_token
        self.__default_env = default_env
        self.__initial_date = initial_date
        self.__end_date = end_date

        self.__req_version = constants.GL_CONTACT_PROFILE_VERSION
        self.__req_timeout = constants.GL_REQ_TIMEOUT
        self.__default_service = constants.GL_CONTACT_PROFILE_SERVICE
        self.__base_endpoint = constants.GL_BASE_URL.replace(constants.GL_SERVICE_REPLACER, self.__default_service)

        self.__create_contact_api = constants.GL_CONTACT_CREATE_LINK
        self.__search_contact_api = constants.GL_CONTACT_SEARCH_LINK
        self.__update_contact_api = constants.GL_CONTACT_UPDATE_LINK
        self.__update_contact_photo_api = constants.GL_CONTACT_UPDATE_PHOTO_LINK
        self.__delete_contact_photo_api = constants.GL_CONTACT_DELETE_PHOTO_LINK
        self.__get_contact_api = constants.GL_CONTACT_PROFILE_LINK
        self.__get_contact_by_id_api = constants.GL_CONTACT_GET_LINK
        self.__get_contact_list_api = constants.GL_CONTACT_LIST_LINK
        self.__delete_contact_api = constants.GL_CONTACT_DELETE_LINK

        self.__contact_group_lc_api = constants.GL_CONTACT_GROUP_CL_LINK
        self.__get_contact_group_api = constants.GL_CONTACT_GROUP_GET_LINK

        self.__clean_tags_re = re.compile('<.*?>')
        self.__buffer_categories = {"call": False, "data": []}
        self.__google_api_credentials = {}
        self.__req_headers = {
            'Authorization': 'Bearer ' + self.__gl_access_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.__js_resp = {
            "err_status": True,
            "response": None,
            "total": 0,
            "success": 0,
            "failed": 0,
            "updated": 0
        }

    def reset_response(self):
        self.__js_resp["err_status"] = True
        self.__js_resp["response"] = None
        self.__js_resp["total"] = 0
        self.__js_resp["success"] = 0
        self.__js_resp["failed"] = 0
        self.__js_resp["updated"] = 0

    ##############################################################################################################
    # ########################       Google API Credential LifeCycle Adjustment       ############################
    ##############################################################################################################

    def check_auth_token(self):
        if len(self.__google_api_credentials) == 0:
            self.__google_api_credentials = self.__default_env[
                constants.GOOGLE_CREDENTIALS_MODEL].get_google_credentials()

        if constants.RESPONSE_ERROR_KEY not in self.__google_api_credentials and \
                constants.RESPONSE_ERR_MESSAGE_KEY not in self.__google_api_credentials:
            _connection_object = connection.Connection(google_app_cred=self.__google_api_credentials,
                                                       default_env=self.__default_env)
            ak_resp = _connection_object.get_quick_msv_access_token()
            if not ak_resp["err_status"]:
                new_wrk_token = ak_resp["response"]
                if new_wrk_token:
                    self.__req_headers['Authorization'] = 'Bearer ' + new_wrk_token

    ##############################################################################################################
    # #############################      People Memberships Labels Operations     ################################
    ##############################################################################################################

    def get_serv_category_by_id(self, label_resource):
        gt_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + '/' + label_resource
            sr_resp = requests.get(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp and len(sr_resp) > 0:
                gt_resp["err_status"] = False
            gt_resp["response"] = sr_resp
        except Exception as ex:
            self.__logging.exception("Get Server Label Exception: " + str(ex))
            gt_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_GET_EXCEPT
        return gt_resp

    def chk_serv_category(self, s2l_category=None, l2s_category=None, custom_fields=None):
        chk_resp = {"err_status": True, "response": None}
        try:
            if s2l_category:
                pass
            elif l2s_category or custom_fields:
                if not self.__buffer_categories["call"]:
                    self.__buffer_categories["call"] = True
                    gt_resp = self.get_membership_resource_list()
                    if not gt_resp["err_status"]:
                        self.__buffer_categories["data"] = gt_resp["response"]
                if l2s_category:
                    for sr_category in self.__buffer_categories["data"]:
                        if sr_category["formattedName"] == l2s_category.name:
                            chk_resp["response"] = sr_category
                            chk_resp["err_status"] = False
                            break
                elif custom_fields:
                    for sr_category in self.__buffer_categories["data"]:
                        if sr_category["formattedName"] == custom_fields["name"]:
                            chk_resp["response"] = sr_category
                            chk_resp["err_status"] = False
                            break
            else:
                chk_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_CHK_ERR
        except Exception as ex:
            self.__logging.exception("Check Server Contact Label Exception: " + str(ex))
            chk_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_CHK_EXCEPT
        return chk_resp

    def create_membership_resource(self, s2l_category=None, l2s_category=None, custom_fields=None):
        crt_resp = {"err_status": True, "response": None}
        try:
            if s2l_category:
                if "contactGroupMembership" in s2l_category:
                    gt_serv_resp = self.get_serv_category_by_id(
                        label_resource=s2l_category["contactGroupMembership"]["contactGroupResourceName"])
                    if not gt_serv_resp["err_status"]:
                        s2l_category = gt_serv_resp["response"]
                        chk_exist_category = self.__default_env[constants.RES_PARTNER_CATEGORY_MODEL].search([
                            ('name', '=', s2l_category['formattedName'])
                        ])
                        if chk_exist_category and len(chk_exist_category) > 0:
                            chk_exist_category[0].write({
                                'gc_name': s2l_category['name'],
                                'gc_res_id': s2l_category["resourceName"].split('/')[1]
                            })
                            crt_resp["response"] = chk_exist_category[0]
                        else:
                            crt_resp["response"] = self.__default_env[constants.RES_PARTNER_CATEGORY_MODEL].create({
                                'name': s2l_category['formattedName'],
                                'gc_name': s2l_category['name'],
                                'gc_res_id': s2l_category["resourceName"].split('/')[1]
                            })
                        crt_resp["err_status"] = False
            elif l2s_category or custom_fields:
                if l2s_category:
                    srv_params = {
                        "contactGroup": {
                            "name": l2s_category.name
                        }
                    }
                else:
                    srv_params = {
                        "contactGroup": {
                            "name": custom_fields['name']
                        }
                    }
                req_url = self.__base_endpoint + self.__req_version + self.__contact_group_lc_api
                sr_resp = requests.post(req_url, data=json.dumps(srv_params), headers=self.__req_headers,
                                        timeout=self.__req_timeout).json()
                if constants.RESPONSE_ERROR_KEY not in sr_resp:
                    crt_resp["response"] = sr_resp
                    crt_resp["err_status"] = False
                else:
                    crt_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_CRT_ERR
            else:
                crt_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_CRT_ERR
        except Exception as ex:
            self.__logging.exception("Create either Contact Category or Membership  Exception: " + str(ex))
            crt_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_CRT_EXCEPT
        return crt_resp

    def get_membership_resource_list(self):
        gt_mbr_resp = {"err_status": True, "response": None}
        try:
            tmp_membership_resource_list, next_page_token = [], None
            while True:
                req_url = self.__base_endpoint + self.__req_version + self.__contact_group_lc_api
                if next_page_token:
                    req_url += '?pageToken=' + next_page_token
                sr_resp = requests.get(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
                if constants.RESPONSE_ERROR_KEY not in sr_resp:
                    tmp_membership_resource_list += sr_resp[constants.GL_CONTACT_GROUP_KEY]
                    if 'nextPageToken' in sr_resp:
                        next_page_token = sr_resp['nextPageToken']
                    else:
                        break
                else:
                    break

            if len(tmp_membership_resource_list) > 0:
                gt_mbr_resp["response"] = tmp_membership_resource_list
                gt_mbr_resp["err_status"] = False
            else:
                gt_mbr_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_GET_ERR
        except Exception as ex:
            self.__logging.exception("Get Contact Membership Resource Lists: " + str(ex))
            gt_mbr_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_GET_EXCEPT
        return gt_mbr_resp

    ##############################################################################################################
    # ########################################      People Operations     ########################################
    ##############################################################################################################

    def delete_serv_contact_by_id(self, people_id):
        del_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__delete_contact_api.replace(
                '{{people_id}}', people_id)
            sr_resp = requests.delete(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                del_resp["err_status"] = False
            del_resp["response"] = sr_resp
        except Exception as ex:
            self.__logging.exception("Delete Contact Exception: " + str(ex))
            del_resp["response"] = constants.GL_CONTACTS_GET_EXCEPT
        return del_resp

    def delete_profile_image_by_contact(self, addon_id):
        del_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + \
                      self.__delete_contact_photo_api.replace("{{people_id}}", addon_id)
            sr_resp = requests.delete(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                del_resp["err_status"] = False
            del_resp["response"] = str(sr_resp)
        except Exception as ex:
            self.__logging.exception("Delete Contact Image Exception: " + str(ex))
            del_resp["response"] = constants.GL_CONTACTS_UPD_EXCEPT
        return del_resp

    def update_profile_image_by_contact(self, l2s_contact, addon_id=None):
        upd_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + \
                      self.__update_contact_photo_api.replace("{{people_id}}", addon_id)
            payload = {"photoBytes": l2s_contact.image_1920.decode()}
            sr_resp = requests.patch(req_url, data=json.dumps(payload), headers=self.__req_headers,
                                     timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                upd_resp["err_status"] = False
            upd_resp["response"] = str(sr_resp)
        except Exception as ex:
            self.__logging.exception("Update Contact Image Exception: " + str(ex))
            upd_resp["response"] = constants.GL_CONTACTS_UPD_EXCEPT
        return upd_resp

    def get_contact_detail_by_id(self, people_id):
        gt_resp = {"err_status": True, "response": None}
        try:
            if people_id and type(people_id) != bool:
                req_url = self.__base_endpoint + self.__req_version + self.__get_contact_by_id_api.replace(
                    '{{people_id}}', people_id) + '?personFields=names'
                sr_resp = requests.get(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
                if constants.RESPONSE_ERROR_KEY not in sr_resp:
                    gt_resp["err_status"] = False
                gt_resp["response"] = sr_resp
            else:
                gt_resp["response"] = constants.GL_CONTACTS_GET_ERR
        except Exception as ex:
            self.__logging.exception("Get Contact Detail Exception: " + str(ex))
            gt_resp["response"] = constants.GL_CONTACTS_GET_EXCEPT
        return gt_resp

    def get_default_membership(self):
        gt_resp = {"err_status": True, "response": None}
        try:
            custom_wid = None
            custom_fields = {'name': '# Odoo (Shared)'}

            chk_def_label = self.chk_serv_category(custom_fields=custom_fields)
            if not chk_def_label["err_status"]:
                custom_wid = chk_def_label["response"]["resourceName"].split('/')[1]
            else:
                crt_custom_fields_resp = self.create_membership_resource(custom_fields=custom_fields)
                if not crt_custom_fields_resp["err_status"]:
                    custom_wid = crt_custom_fields_resp["response"]["resourceName"].split('/')[1]

            if custom_wid:
                gt_resp["response"] = {
                    "contactGroupMembership": {
                        "contactGroupResourceName": constants.GL_CONTACT_GROUP_KEY + '/' + custom_wid
                    }
                }
                gt_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Get Default Membership Exception: " + str(ex))
        return gt_resp

    def create_membership_lists(self, s2l_contact=None, l2s_contact=None):
        crt_ms_resp = {"err_status": True, "response": None}
        try:
            if s2l_contact:
                tmp_local_categories = []
                if len(s2l_contact["memberships"]) > 0:
                    for sr_membership in s2l_contact["memberships"]:
                        chk_lc_resp = self.create_membership_resource(s2l_category=sr_membership)
                        if not chk_lc_resp["err_status"]:
                            tmp_local_categories.append(chk_lc_resp["response"].id)
                crt_ms_resp["response"] = tmp_local_categories
                crt_ms_resp["err_status"] = False
            elif l2s_contact:
                tmp_membership_listing = []
                prev_wid = [], None
                for _category in l2s_contact.category_id:
                    res_wid = None

                    chk_resp = self.chk_serv_category(l2s_category=_category)
                    if not chk_resp["err_status"]:
                        res_wid = chk_resp["response"]["resourceName"].split('/')[1]
                        _category.write({
                            'gc_res_id': res_wid,
                            'gc_name': chk_resp["response"]['name']
                        })
                    else:
                        crt_srv_resp = self.create_membership_resource(l2s_category=_category)
                        if not crt_srv_resp["err_status"]:
                            crt_lc_resp = self.create_membership_resource(s2l_category=crt_srv_resp["response"])
                            if not crt_lc_resp["err_status"]:
                                res_wid = crt_lc_resp["response"].gc_res_id

                    if res_wid and res_wid != prev_wid:
                        tmp_membership_listing.append({
                            "contactGroupMembership": {
                                "contactGroupResourceName": constants.GL_CONTACT_GROUP_KEY + '/' + res_wid
                            }
                        })
                        prev_wid = res_wid

                if len(tmp_membership_listing) > 0:
                    crt_ms_resp["response"] = tmp_membership_listing
                    crt_ms_resp["err_status"] = False
                else:
                    crt_ms_resp["err_status"] = constants.GL_CONTACTS_MEMBERSHIPS_CRT_ERR
            else:
                crt_ms_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_CRT_ERR
        except Exception as ex:
            self.__logging.exception("Create Contact Membership Listing Exception: " + str(ex))
            crt_ms_resp["response"] = constants.GL_CONTACTS_MEMBERSHIPS_CRT_EXCEPT
        return crt_ms_resp

    def create_update_serv_contact(self, db_contact, is_update=False, addon_info=None):
        crt_srv_resp = {"err_status": True, "response": None}
        try:
            # Add Real Update datetime when create or updating contact on Google server
            real_update_time = pytz.utc.localize(datetime.utcnow()).astimezone()
            updated_tz = db_contact.write_date
            if type(updated_tz) == str:
                updated_tz = datetime.strptime(db_contact.write_date, constants.DEFAULT_DATETIME_FORMAT)
            updated_tz = updated_tz.astimezone()

            gl_json_params = {
                "addresses": [
                    {
                        'type': "Work",
                        "streetAddress": db_contact.street if db_contact.street else "",
                        'extendedAddress': db_contact.street2 if db_contact.street2 else "",
                        'poBox': db_contact.state_id.name if db_contact.state_id else "",
                        "city": db_contact.city if db_contact.city else "",
                        "postalCode": db_contact.zip if db_contact.zip else "",
                        'country': db_contact.country_id.name if db_contact.country_id else ""
                    }
                ],
                "emailAddresses": [
                    {"value": db_contact.email if db_contact.email else "", "type": "Work"}
                ],
                "phoneNumbers": [
                    {"value": db_contact.mobile if db_contact.mobile else "", "type": "Mobile"},
                    {"value": db_contact.phone if db_contact.phone else "", "type": "Work"},
                ],
                "urls": [
                    {"value": db_contact.website if db_contact.website else "", "type": "homePage"}
                ],
                "memberships": [{
                    'contactGroupMembership': {
                        'contactGroupResourceName': 'contactGroups/myContacts'
                    }
                }],
                "userDefined": [
                    {"key": "Odoo Last Updated",
                     "value": str(updated_tz.strftime(constants.DEFAULT_RES_DATETIME_FORMAT))},
                    {"key": "Google Last Updated",
                     "value": str(real_update_time.strftime(constants.DEFAULT_RES_DATETIME_FORMAT))},
                    {"key": constants.GL_CONTACTS_USER_DEFINED_ID, "value": str(db_contact.id)}
                ],
                "biographies": [{
                    "value": re.sub(self.__clean_tags_re, '', db_contact.comment) if db_contact.comment else "Default",
                    "contentType": "TEXT_PLAIN"
                }]
            }

            #########################################################################################################
            # ##################################### Check Individual or Company #####################################
            #########################################################################################################

            if db_contact.is_company:
                gl_json_params["names"] = [{
                    "givenName": "#",
                    "familyName": db_contact.name,
                    "displayName": db_contact.name,
                }]
                gl_json_params["organizations"] = [{
                    "name": db_contact.commercial_company_name if db_contact.commercial_company_name else "",
                }]
                gl_json_params["imClients"] = [
                    {"protocol": "ID / Reg. #", "username": str(db_contact.vat) if db_contact.vat else ""}
                ]

            else:
                if db_contact.type == 'contact':
                    name_parts = db_contact.name.split(' ')
                    gl_json_params["names"] = [{
                        "displayName": db_contact.name,
                        "givenName": name_parts[0],
                        "familyName": name_parts[2] if len(name_parts) > 2 else "",
                        "middleName": name_parts[1] if len(name_parts) > 1 else ""
                    }]
                    gl_json_params["organizations"] = [{
                        "name": db_contact.commercial_company_name if db_contact.commercial_company_name else "",
                        "title": db_contact.function if db_contact.function else ""
                    }]
                else:
                    gl_json_params["names"] = [{
                        "givenName": "@",
                        "familyName": db_contact.name,
                        "displayName": db_contact.name,
                    }]
                    gl_json_params["organizations"] = [{
                        "name": db_contact.commercial_company_name if db_contact.commercial_company_name else "",
                        "title": db_contact.function if db_contact.function else ""
                    }]

            #########################################################################################################
            # ################################   End Check Individual or Company  ###################################
            #########################################################################################################

            gt_def_membership_resp = self.get_default_membership()
            if not gt_def_membership_resp["err_status"]:
                gl_json_params["memberships"].append(gt_def_membership_resp["response"])

            if db_contact.category_id and len(db_contact.category_id) > 0:
                listing_resp = self.create_membership_lists(l2s_contact=db_contact)
                if not listing_resp["err_status"]:
                    gl_json_params["memberships"] += listing_resp["response"]

            if not is_update:
                req_url = self.__base_endpoint + self.__req_version + self.__create_contact_api
                sr_resp = requests.post(req_url, data=json.dumps(gl_json_params), headers=self.__req_headers,
                                        timeout=self.__req_timeout).json()
            else:
                gc_id = db_contact.gc_id
                gl_json_params["etag"] = db_contact.gc_etag
                if not db_contact.gc_id and not db_contact.gc_etag:
                    gc_id = addon_info["gc_id"]
                    gl_json_params["etag"] = addon_info["gc_etag"]

                if gc_id and 'etag' in gl_json_params:
                    try:
                        del gl_json_params["names"][0]["displayName"]
                    except:
                        pass

                    req_url = self.__base_endpoint + self.__req_version + self.__update_contact_api.replace(
                        "{{people_id}}", gc_id) + "?updatePersonFields=" + ','.join(
                        constants.GL_CONTACT_UPDATE_ADDON_FLDS)
                    sr_resp = requests.patch(req_url, data=json.dumps(gl_json_params), headers=self.__req_headers,
                                             timeout=self.__req_timeout).json()
                    if constants.RESPONSE_ERROR_KEY in sr_resp:
                        gr_resp = self.get_contact_detail_by_id(people_id=gc_id)
                        is_serv_found = False
                        if gr_resp['err_status']:
                            gr_resp = self.get_contact_detail_by_id(people_id=addon_info["gc_id"])
                            is_serv_found = True

                        if not gr_resp["err_status"]:
                            gl_json_params["etag"] = gr_resp["response"]["etag"]
                            if is_serv_found:
                                req_url = self.__base_endpoint + self.__req_version + self.__update_contact_api.replace(
                                    "{{people_id}}", addon_info["gc_id"]) + "?updatePersonFields=" + ','.join(
                                    constants.GL_CONTACT_UPDATE_ADDON_FLDS)

                            sr_resp = requests.patch(req_url, data=json.dumps(gl_json_params),
                                                     headers=self.__req_headers,
                                                     timeout=self.__req_timeout).json()
                else:
                    sr_resp = {
                        constants.RESPONSE_ERROR_KEY: {
                            constants.RESPONSE_MESSAGES_KEY: constants.GL_CONTACTS_CRT_ERR
                        }
                    }

            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                resource_id = sr_resp["resourceName"].split('/')[1]
                # Update Google ID if newly created contact
                update_ref = {
                    'gc_id': resource_id,
                    'gc_etag': sr_resp["etag"],
                    'source': constants.GL_CONTACT_SOURCE
                }
                if not is_update:
                    db_contact.update_params(update_ref)

                if db_contact.gc_id:
                    if db_contact.gc_id != resource_id:
                        db_contact.update_params(update_ref)

                if is_update and not db_contact.gc_id:
                    db_contact.update_params(update_ref)

                if db_contact.image_1920:
                    upd_resp = self.update_profile_image_by_contact(l2s_contact=db_contact, addon_id=resource_id)
                    if upd_resp["err_status"]:
                        self.__logging.info("Update Contact Image: " + upd_resp["response"])
                    else:
                        get_detl_resp = self.get_contact_detail_by_id(people_id=resource_id)
                        if not get_detl_resp["err_status"]:
                            db_contact.update_params({'gc_etag': get_detl_resp["response"]["etag"]})
                else:
                    upd_resp = self.delete_profile_image_by_contact(addon_id=resource_id)
                    if upd_resp["err_status"]:
                        self.__logging.info("Update Contact Image: " + upd_resp["response"])
                    else:
                        get_detl_resp = self.get_contact_detail_by_id(people_id=resource_id)
                        if not get_detl_resp["err_status"]:
                            db_contact.update_params({'gc_etag': get_detl_resp["response"]["etag"]})

                crt_srv_resp["response"] = sr_resp
                crt_srv_resp["err_status"] = False
            else:
                crt_srv_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGES_KEY]
        except Exception as ex:
            self.__logging.exception("Create Server Contact Exception: " + str(ex))
            crt_srv_resp["response"] = constants.GL_CONTACTS_CRT_EXCEPT
        return crt_srv_resp

    def create_update_local_contact(self, sr_contact, previous_local_contact=None):
        crt_lc_resp = {"err_status": True, "response": None}
        try:
            title_id = None
            db_data_params = {
                'gc_etag': sr_contact["etag"],
                # 'name': sr_contact["names"][0]["displayName"],
                'source': constants.GL_CONTACT_SOURCE,
            }

            try:
                resource_id = sr_contact["resourceName"].split('/')[1]
                if previous_local_contact:
                    if not previous_local_contact.gc_id:
                        db_data_params['gc_id'] = resource_id
                else:
                    db_data_params['gc_id'] = resource_id
            except:
                pass

            if "names" in sr_contact:
                # Check for Title field for Many2one relationship
                if 'honorificPrefix' in sr_contact["names"][0] and sr_contact["names"][0]["honorificPrefix"]:
                    title_id = self.__default_env[constants.RES_PARTNER_TITLE_MODEL].search([
                        ('name', '=', str(sr_contact["names"][0]["honorificPrefix"]).capitalize())
                    ])
                    if title_id and len(title_id) > 0:
                        title_id = title_id[0].id
                    else:
                        title_id = self.__default_env[constants.RES_PARTNER_TITLE_MODEL].create({
                            'name': str(sr_contact["names"][0]["honorificPrefix"]).capitalize()
                        }).id

                # Check the First Name field for Many2one relationship
                full_name = ""
                if 'givenName' in sr_contact["names"][0] and sr_contact["names"][0]["givenName"]:
                    full_name += sr_contact["names"][0]["givenName"]
                if 'middleName' in sr_contact["names"][0] and sr_contact["names"][0]["middleName"]:
                    full_name += sr_contact["names"][0]["middleName"]
                if 'familyName' in sr_contact["names"][0] and sr_contact["names"][0]["familyName"]:
                    full_name += sr_contact["names"][0]["familyName"]

                db_data_params["name"] = full_name
                if title_id:
                    db_data_params["title"] = title_id

            elif "nicknames" in sr_contact:
                db_data_params["name"] = sr_contact["nicknames"][0]["value"]
            elif "emailAddresses" in sr_contact and len(sr_contact["emailAddresses"]) > 0:
                db_data_params["name"] = sr_contact["emailAddresses"][0]["value"].split('@')[0]
            else:
                crt_lc_resp["response"] = constants.GL_CONTACTS_CRT_ERR
                return crt_lc_resp

            if "emailAddresses" in sr_contact and len(sr_contact["emailAddresses"]) > 0:
                db_data_params["email"] = sr_contact["emailAddresses"][0]["value"]
            else:
                db_data_params["email"] = ""

            if 'organizations' in sr_contact and len(sr_contact["organizations"]) > 0:
                if "title" in sr_contact["organizations"][0]:
                    db_data_params["function"] = sr_contact["organizations"][0]["title"]
                try:
                    chk_company = self.__default_env[constants.RES_PARTNER_MODEL].search([
                        '&', ('name', '=', sr_contact["organizations"][0]["name"]), ('is_company', '=', True)
                    ])
                    if chk_company and len(chk_company) > 0:
                        db_data_params["parent_id"] = chk_company[0].id
                    else:
                        db_data_params["parent_id"] = self.__default_env[constants.RES_PARTNER_MODEL].create({
                            'name': sr_contact["organizations"][0]["name"],
                            'is_company': True,
                            'company_type': 'company'
                        }).id
                except:
                    self.__logging.exception("Unable to check company information")

            if 'phoneNumbers' in sr_contact and len(sr_contact["phoneNumbers"]) > 0:
                db_data_params["phone"] = sr_contact["phoneNumbers"][0]["value"]
                db_data_params["mobile"] = sr_contact["phoneNumbers"][1]["value"] if len(
                    sr_contact["phoneNumbers"]) > 1 else ""
            else:
                db_data_params["phone"] = ""
                db_data_params["mobile"] = ""

            if 'addresses' in sr_contact and len(sr_contact["addresses"]) > 0:
                db_data_params["street"] = sr_contact["addresses"][0]["streetAddress"] if 'streetAddress' in \
                                                                                          sr_contact["addresses"][
                                                                                              0] else ""
                db_data_params["street2"] = sr_contact["addresses"][0]["extendedAddress"] if 'extendedAddress' in \
                                                                                             sr_contact["addresses"][
                                                                                                 0] else ""
                db_data_params["city"] = sr_contact["addresses"][0]["city"] if 'city' in sr_contact["addresses"][
                    0] else ""
                db_data_params["zip"] = sr_contact["addresses"][0]["postalCode"] if 'postalCode' in \
                                                                                    sr_contact["addresses"][0] else ""

                try:
                    if 'country' in sr_contact["addresses"][0] and sr_contact["addresses"][0]["country"] and len(
                            sr_contact["addresses"][0]["country"]) > 0:
                        chk_country_exist = self.__default_env[constants.RES_COUNTRY_MODEL].search([
                            ('name', '=', sr_contact["addresses"][0]['country'])
                        ])
                        if chk_country_exist and len(chk_country_exist) > 0:
                            db_data_params["country_id"] = chk_country_exist[0].id
                        else:
                            db_data_params["country_id"] = self.__default_env[constants.RES_COUNTRY_MODEL].create({
                                'name': sr_contact["addresses"][0]['country']
                            }).id
                except Exception as ex:
                    self.__logging.exception("Unable to handle Work Address Country field: " + str(ex))

                try:
                    if 'poBox' in sr_contact["addresses"][0] and sr_contact["addresses"][0]["poBox"] and len(
                            sr_contact["addresses"][0]["poBox"]) > 0:
                        chk_state_exist = self.__default_env[constants.RES_COUNTRY_STATE_MODEL].search([
                            ('name', '=', sr_contact["addresses"][0]['poBox'])
                        ])
                        if chk_state_exist and len(chk_state_exist) > 0:
                            db_data_params["state_id"] = chk_state_exist[0].id
                        else:
                            db_data_params["state_id"] = self.__default_env[constants.RES_COUNTRY_STATE_MODEL].create({
                                'name': sr_contact["addresses"][0]['poBox'],
                                'country_id': db_data_params[
                                    "country_id"] if "country_id" in db_data_params else
                                self.__default_env[constants.RES_COUNTRY_MODEL].search([])[0].id,
                                'code': ''.join([w[0] for w in sr_contact["addresses"][0]['poBox'].split(' ')])
                            }).id
                except Exception as ex:
                    self.__logging.exception("Unable to handle Work Address State field: " + str(ex))
            else:
                db_data_params["street"] = ""
                db_data_params["street2"] = ""
                db_data_params["city"] = ""
                db_data_params["zip"] = ""

            if 'urls' in sr_contact and len(sr_contact["urls"]) > 0:
                db_data_params["website"] = sr_contact['urls'][0]["value"]
            else:
                db_data_params["website"] = ""

            if 'memberships' in sr_contact and len(sr_contact['memberships']) > 0:
                if previous_local_contact:
                    ct_mbrs_resp = self.create_membership_lists(s2l_contact=sr_contact)
                    if not ct_mbrs_resp["err_status"]:
                        previous_local_contact.update_categories_params(ct_mbrs_resp["response"])

            if 'biographies' in sr_contact and len(sr_contact['biographies']) > 0:
                db_data_params['comment'] = sr_contact['biographies'][0]['value']

            if previous_local_contact:
                previous_local_contact.update_params(db_data_params)
                crt_lc_resp["response"] = previous_local_contact
            else:
                db_data_params["gc_id"] = sr_contact["resourceName"].split('/')[1]
                contact_obj = self.__default_env[constants.RES_PARTNER_MODEL].create(db_data_params)

                if 'memberships' in sr_contact and len(sr_contact['memberships']) > 0:
                    ct_mbrs_resp = self.create_membership_lists(s2l_contact=sr_contact)
                    if not ct_mbrs_resp["err_status"]:
                        contact_obj.update_categories_params(ct_mbrs_resp["response"])

                crt_lc_resp["response"] = contact_obj
            current_local_contact = crt_lc_resp["response"]

            ##########################################################################################
            # ###########################   Custom Code for Profile Image   ##########################
            ##########################################################################################
            try:
                if 'photos' in sr_contact and len(sr_contact["photos"]) > 0:
                    byte_data = base64.b64encode(
                        requests.get(sr_contact["photos"][0]['url'], headers=self.__req_headers).content)

                    for img_dim in constants.GL_CONTACTS_IMAGE_DIMENSION:
                        chk_image_rec = self.__default_env[constants.IR_ATTACHMENT_MODEL].search([
                            '&', '&', ('res_field', '=', img_dim), ('res_model', '=', 'res.partner'),
                            ('res_id', '=', current_local_contact.id),
                        ])
                        if chk_image_rec and len(chk_image_rec) > 0:
                            chk_image_rec[0].write({'type': 'binary', 'datas': byte_data})
                        else:
                            self.__default_env[constants.IR_ATTACHMENT_MODEL].create({
                                'name': img_dim,
                                'res_model': 'res.partner',
                                'res_field': img_dim,
                                'res_id': current_local_contact.id,
                                'type': 'binary',
                                'datas': byte_data
                            })

            except Exception as ex:
                self.__logging.exception("Exception Profile Image Import: " + str(ex))

            crt_lc_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Create Local Contact Exception: " + str(ex))
            crt_lc_resp["response"] = constants.GL_CONTACTS_CRT_EXCEPT
        return crt_lc_resp

    ############################################################################################################
    # #########################################      Imports & Exports   #######################################
    ############################################################################################################

    def get_serv_contact_stat(self, l2s_contact):
        is_update, addons = False, None
        try:
            if l2s_contact.gc_id:
                gt_detail_resp = self.get_contact_detail_by_id(people_id=l2s_contact.gc_id)
                if not gt_detail_resp["err_status"]:
                    # exist_serv_contact = gt_detail_resp["response"]
                    addons = {'gc_id': l2s_contact.gc_id, 'db_exist': True, 'gc_etag': gt_detail_resp["response"]['etag']}
                    # if l2s_contact.gc_etag:
                    #     addons['gc_etag'] = l2s_contact.gc_etag
                    # else:
                    #     addons['gc_etag'] = gt_detail_resp["response"]['etag']
                    is_update = True

            if not is_update:
                chk_contact_resp = self.check_contact(l2s_contact=l2s_contact)
                if not chk_contact_resp["err_status"]:
                    exist_serv_contact = chk_contact_resp["response"][0]["person"]
                    resource_id = exist_serv_contact["resourceName"].split('/')[1]
                    addons = {'gc_id': resource_id, 'gc_etag': exist_serv_contact["etag"]}
                    is_update = True

            if is_update:
                inner_addon = {'gc_etag': addons["gc_etag"]}
                if not l2s_contact.gc_id:
                    inner_addon["gc_id"] = addons["gc_id"]
                    addons["db_exist"] = True
                l2s_contact.update_params(inner_addon)
        except Exception as ex:
            self.__logging.exception("Get Server Contact Status Exception: " + str(ex))
        return is_update, addons

    def check_contact(self, s2l_contact=None, l2s_contact=None):
        chk_resp = {"err_status": True, "response": None}
        try:
            if s2l_contact:
                is_found = False

                ####################################################################################
                # ##################   Check DB contact by Google Resource ID    ###################
                ####################################################################################
                sr_gid = s2l_contact["resourceName"].split('/')[1]
                chk_contact_by_gc_id = self.__default_env[constants.RES_PARTNER_MODEL].search([('gc_id', '=', sr_gid)])
                if chk_contact_by_gc_id and len(chk_contact_by_gc_id) > 0:
                    chk_resp["response"] = chk_contact_by_gc_id[0]
                    chk_resp["err_status"] = False
                    is_found = True

                ####################################################################################
                # ###################   Check DB contact by Odoo Contact ID    #####################
                ####################################################################################
                if not is_found and "userDefined" in s2l_contact and len(s2l_contact["userDefined"]) > 0:
                    odoo_cnt_id = None
                    for usr_def in s2l_contact["userDefined"]:
                        if usr_def["key"] == constants.GL_CONTACTS_USER_DEFINED_ID and usr_def["value"]:
                            odoo_cnt_id = usr_def["value"]
                            break

                    if odoo_cnt_id:
                        chk_contact_by_id = self.__default_env[constants.RES_PARTNER_MODEL].search(
                            [('id', '=', odoo_cnt_id)])
                        if chk_contact_by_id and len(chk_contact_by_id) > 0:
                            chk_resp["response"] = chk_contact_by_id[0]
                            chk_resp["err_status"] = False
                            is_found = True

                ####################################################################################
                # ################   Check DB contact by Name and Email Fields    ##################
                ####################################################################################

                if not is_found:
                    filter_query = []
                    if 'emailAddresses' in s2l_contact and len(s2l_contact["emailAddresses"]) > 0:
                        filter_query.append('&')
                        filter_query.append(('email', '=', s2l_contact["emailAddresses"][0]["value"]))

                    if "names" in s2l_contact:
                        filter_query.append(('name', '=', s2l_contact["names"][0]["displayName"]))
                    elif "nicknames" in s2l_contact and len(s2l_contact["nicknames"]) > 0:
                        filter_query.append(('name', '=', s2l_contact["nicknames"][0]["value"]))
                    elif 'emailAddresses' in s2l_contact and len(s2l_contact["emailAddresses"]) > 0:
                        filter_query.append(('name', '=', s2l_contact["emailAddresses"][0]["value"].split('@')[0]))

                    if len(filter_query) > 0:
                        chk_contact_exist = self.__default_env[constants.RES_PARTNER_MODEL].search(filter_query)
                        if chk_contact_exist and len(chk_contact_exist) > 0:
                            chk_resp["response"] = chk_contact_exist[0]
                            chk_resp["err_status"] = False

            elif l2s_contact:
                req_url = self.__base_endpoint + self.__req_version + self.__search_contact_api + \
                          "?query=" + l2s_contact.name

                if l2s_contact.email:
                    req_url += ',' + l2s_contact.email
                # if l2s_contact.phone:
                #     req_url += ',' + l2s_contact.phone
                # if l2s_contact.mobile:
                #     req_url += ',' + l2s_contact.mobile
                req_url += "&readMask=names,emailAddresses,phoneNumbers,organizations"
                req_url = req_url.replace(' ', '%20')
                sr_resp = requests.get(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
                if constants.RESPONSE_ERROR_KEY not in sr_resp and len(sr_resp) > 0:
                    chk_resp["response"] = sr_resp[constants.RESPONSE_RESULTS_KEY]
                    chk_resp["err_status"] = False
                else:
                    chk_resp["response"] = sr_resp
            else:
                chk_resp["response"] = constants.GL_CONTACTS_CHK_ERR
        except Exception as ex:
            self.__logging.exception("Check Contact Exception: " + str(ex))
            chk_resp["response"] = constants.GL_CONTACTS_CHK_EXCEPT
        return chk_resp

    def update_contact(self, local_contact=None, local_serv_contact=None, l2s_contact=None):
        upd_resp = {"err_status": True, "response": None}
        try:
            if local_contact and local_serv_contact:
                lc_upd_resp = self.create_update_local_contact(
                    sr_contact=local_serv_contact, previous_local_contact=local_contact)
                if not lc_upd_resp["err_status"]:
                    upd_resp["err_status"] = False
                upd_resp["response"] = lc_upd_resp["response"]
            elif l2s_contact:
                is_update, addons = self.get_serv_contact_stat(l2s_contact=l2s_contact)
                serv_resp = self.create_update_serv_contact(
                    db_contact=l2s_contact, is_update=is_update, addon_info=addons)
                if not serv_resp["err_status"]:
                    upd_resp["err_status"] = False
                upd_resp["response"] = serv_resp["response"]
            else:
                upd_resp["response"] = constants.GL_CONTACTS_UPD_ERR
        except Exception as ex:
            self.__logging.exception("Check Contact Exception: " + str(ex))
            upd_resp["response"] = constants.GL_CONTACTS_UPD_EXCEPT
        return upd_resp

    def create_contact(self, s2l_contact=None, l2s_contact=None):
        crt_resp = {"err_status": True, "response": None, "addon": None}
        try:
            if s2l_contact:
                lc_resp = self.create_update_local_contact(sr_contact=s2l_contact)
                if not lc_resp["err_status"]:
                    crt_resp["err_status"] = False
                crt_resp["response"] = lc_resp["response"]

            elif l2s_contact:
                is_update, addons = self.get_serv_contact_stat(l2s_contact=l2s_contact)
                serv_resp = self.create_update_serv_contact(
                    db_contact=l2s_contact, is_update=is_update, addon_info=addons)
                if not serv_resp["err_status"]:
                    crt_resp["err_status"] = False
                    crt_resp["addon"] = is_update
                crt_resp["response"] = serv_resp["response"]
            else:
                crt_resp["response"] = constants.GL_CONTACTS_CRT_ERR
        except Exception as ex:
            self.__logging.exception("Create Contact Exception: " + str(ex))
            crt_resp["response"] = constants.GL_CONTACTS_CRT_EXCEPT
        return crt_resp

    ##############################################################################################################
    # #################################    Baseline Cron & Manual Methods    #####################################
    ##############################################################################################################

    def read_serv_contacts(self):
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__get_contact_api + \
                      self.__get_contact_list_api + '?personFields=' + \
                      constants.GL_CONTACT_PROFILE_REQ_FLDS_SEP.join(constants.GL_CONTACT_SEARCH_FLDS)
            sr_resp = requests.get(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                tmp_contact_lists = []
                if self.__initial_date and self.__end_date:
                    for sr_contact in sr_resp["connections"]:
                        meta_info_sources = sr_contact["metadata"]["sources"]
                        update_date = None
                        for mt_info in meta_info_sources:
                            if mt_info['type'] == 'CONTACT':
                                update_date = mt_info["updateTime"]
                                break

                        if update_date:
                            try:
                                update_date = datetime.strptime(
                                    update_date.replace('T', ' ').split('.')[0], constants.DEFAULT_DATETIME_FORMAT)
                            except:
                                update_date = datetime.strptime(
                                    update_date.replace('T', ' ').split('.')[0], constants.DEFAULT_CS_DATETIME_FORMAT)

                            if self.__initial_date <= update_date <= self.__end_date:
                                tmp_contact_lists.append(sr_contact)

                elif "connections" in sr_resp:
                    tmp_contact_lists = sr_resp["connections"]
                else:
                    self.__js_resp["response"] = constants.GL_CONTACTS_IMP_NOT_FND

                if len(tmp_contact_lists) > 0:
                    self.__js_resp["response"] = tmp_contact_lists
                    self.__js_resp["total"] = len(tmp_contact_lists)
                    self.__js_resp["err_status"] = False
                else:
                    self.__js_resp["response"] = constants.GL_CONTACTS_IMP_NOT_FND
            else:
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGES_KEY]
        except Exception as ex:
            self.__logging.exception("Server Import Contacts Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CONTACTS_IMP_SERV_EXCEPT

    def import_contacts(self):
        self.reset_response()
        try:
            self.read_serv_contacts()
            if not self.__js_resp["err_status"]:
                for _contact in self.__js_resp["response"]:
                    try:
                        chk_contact_resp = self.check_contact(s2l_contact=_contact)
                        if chk_contact_resp["err_status"]:
                            crt_resp = self.create_contact(s2l_contact=_contact)
                            if not crt_resp["err_status"]:
                                self.__js_resp["success"] += 1
                            else:
                                self.__js_resp["failed"] += 1
                        else:
                            upd_resp = self.update_contact(
                                local_contact=chk_contact_resp["response"], local_serv_contact=_contact)
                            if upd_resp["err_status"]:
                                self.__logging.error("Update Odoo Contact Error: " + upd_resp["response"])
                            else:
                                self.__js_resp["updated"] += 1
                    except Exception as ex:
                        self.__logging.info(">> Import SGL Contact Exception: " + str(ex))
                        self.__js_resp["failed"] += 1
        except Exception as ex:
            self.__logging.exception("Import Contacts Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CONTACTS_IMP_EXCEPT
        return self.__js_resp

    def write_serv_contacts(self, db_contacts_data):
        self.reset_response()
        try:
            for _contact in db_contacts_data:
                self.check_auth_token()
                chk_serv_status = self.check_contact(l2s_contact=_contact)
                if chk_serv_status["err_status"]:
                    crt_resp = self.create_contact(l2s_contact=_contact)
                    if not crt_resp["err_status"]:
                        if crt_resp["addon"]:
                            self.__js_resp["updated"] += 1
                        else:
                            self.__js_resp["success"] += 1
                    else:
                        self.__logging.info("Internal Error Export Contact: " + crt_resp["response"])
                        self.__js_resp["failed"] += 1
                else:
                    upd_resp = self.update_contact(l2s_contact=_contact)
                    if upd_resp["err_status"]:
                        self.__logging.error("Update Google Contact Error: " + upd_resp["response"])
                    else:
                        self.__js_resp["updated"] += 1

        except Exception as ex:
            self.__logging.exception("Export Server Contact Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CONTACTS_EXP_SERV_EXCEPT

    def export_contacts(self):
        self.reset_response()
        try:
            filter_params = []
            if self.__initial_date and self.__end_date:
                filter_params.append('&')
                filter_params.append(('write_date', '>=', str(self.__initial_date)))
                filter_params.append(('write_date', '<=', str(self.__end_date)))

            _db_contacts = self.__default_env[constants.RES_PARTNER_MODEL].search(
                filter_params, order='write_date desc')
            if _db_contacts and len(_db_contacts) > 0:
                self.write_serv_contacts(db_contacts_data=_db_contacts)
                self.__js_resp["err_status"] = len(_db_contacts)
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = constants.GL_CONTACTS_EXP_NOT_FND
        except Exception as ex:
            self.__logging.exception("Export Contacts Exception: " + str(ex))
            self.__js_resp["response"] = constants.GL_CONTACTS_EXP_EXCEPT
        return self.__js_resp
