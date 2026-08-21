###################################################################################################################
# ###########################################     Google Cloud APIs      ##########################################
###################################################################################################################

GL_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GL_AUTH_EXCODE_URL = 'https://oauth2.googleapis.com/token'
GL_SCOPE_BASE_URL = 'https://www.googleapis.com/auth/'
GL_BASE_URL = 'https://{{service}}.googleapis.com/'
GL_SERVICE_REPLACER = '{{service}}'
GL_REQ_TIMEOUT = 5

GL_SCOPES = ['gmail.modify', 'contacts', 'calendar', 'tasks', 'drive', 'userinfo.profile', 'userinfo.email']

CONTACT_USER_TYPE = 'Google'
RES_PARTNER_MODEL = 'res.partner'
RES_PARTNER_STASH_MODEL = 'res_partner'
RES_PARTNER_CATEGORY_MODEL = 'res.partner.category'
RES_PARTNER_TITLE_MODEL = 'res.partner.title'
RES_COUNTRY_MODEL = 'res.country'
RES_COUNTRY_STATE_MODEL = 'res.country.state'
RES_PARTNER_CATEGORY_REL_MODEL = 'res_partner_res_partner_category_rel'
CALENDAR_EVENT_MODEL = 'calendar.event'
CALENDAR_ALARM_MODEL = 'calendar.alarm'
MAIL_TEMPLATE_MODEL = 'mail.template'
CALENDAR_EVENT_STASH_MODEL = 'calendar_event'

MAIL_MAIL_MODEL = 'mail.mail'
MAIL_MESSAGE_MODEL = 'mail.message'
MAIL_MESSAGE_ATTACH_MODEL = 'message_attachment_rel'
IR_MODEL_MODEL = 'ir.model'
IR_CRON_MODEL = 'ir.cron'
IR_CRON_STASH_MODEL = 'ir_cron'

RES_USERS_MODEL = 'res.users'
MAIL_ACTIVITY_MODEL = 'mail.activity'
MAIL_ACTIVITY_STASH_MODEL = 'mail_activity'
MAIL_ACTIVITY_TYPE_MODEL = 'mail.activity.type'
MAIL_NOTIFICATION_MODEL = "mail.notification"
MAIL_RESEND_MESSAGE_MODEL = "mail.resend.message"
IR_ATTACHMENT_MODEL = 'ir.attachment'
DB_IR_ATTACHMENT_MODEL = 'ir_attachment'
CLASS_IR_ATTACHMENT_REL_MODEL = 'gd_class_ir_attachments_rel'

GOOGLE_CREDENTIALS_MODEL = 'google.credentials'
GOOGLE_CONNECTOR_MODEL = 'google.connector'
GOOGLE_IMPORT_STATS_MODEL = 'google.import.stats'
GOOGLE_EXPORT_STATS_MODEL = 'google.export.stats'
GOOGLE_CRON_SETTINGS_MODEL = 'google.cron.settings'

GOOGLE_CREDENTIALS_MODEL_DESC = 'Google Credentials Desc'
GOOGLE_CONNECTOR_MODEL_DESC = 'Google Connector Desc'
GOOGLE_IMPORT_STATS_MODEL_DESC = 'Google Import Stats Desc'
GOOGLE_EXPORT_STATS_MODEL_DESC = 'Google Export Stats Desc'
GOOGLE_CRON_SETTINGS_MODEL_DESC = 'Google Cron Settings Desc'

GOOGLE_IMPORT_CONTACTS_DEF = 'Google Contacts Import'
GOOGLE_EXPORT_CONTACTS_DEF = 'Google Contacts Export'
GOOGLE_IMPORT_CALENDAR_DEF = 'Google Calendar Import'
GOOGLE_EXPORT_CALENDAR_DEF = 'Google Calendar Export'
GOOGLE_IMPORT_DRIVE_DEF = 'Google Drive Import'
GOOGLE_EXPORT_DRIVE_DEF = 'Google Drive Export'
GOOGLE_IMPORT_TASKS_DEF = 'Google Tasks Import'
GOOGLE_EXPORT_TASKS_DEF = 'Google Tasks Export'
GOOGLE_IMPORT_MAILS_DEF = 'Google Mails Import'

GOOGLE_CREDENTIALS_RDT_URI = '/google_success'
GOOGLE_CREDENTIALS_RDT_URI_ODOO = '/web'
GOOGLE_CREDENTIALS_RDT_URI_KEY = 'code='
GOOGLE_CREDENTIALS_RDT_URI_SPLITTER = '&'
GOOGLE_CREDENTIALS_RDT_URI_ERR = 'Oops, Given redirect url is not supported, Please try again'

RESPONSE_ERROR_KEY = 'error'
RESPONSE_ITEMS_KEY = 'items'
RESPONSE_MESSAGES_KEY = 'message'
RESPONSE_FILES_KEY = 'files'
RESPONSE_RESULTS_KEY = 'results'
RESPONSE_ERR_MESSAGE_KEY = 'err_message'

INITIAL_INDEX = 0
DEFAULT_INDEX = -1
ACCESS_TOKEN_ATTEMPT = 3
TOKEN_ERROR_CODE = '80049228'
TOKEN_ERR_STATUS_CODE = 401
DEFAULT_ATTACHMENT_PATH = '\\office_attachments\\'

###################################################################################################################
# ############################################     Contacts Section      ##########################################
###################################################################################################################

GL_CONTACT_PROFILE_VERSION = 'v1'

GL_CONTACT_GROUP_KEY = 'contactGroups'
GL_CONTACT_GROUP_CL_LINK = '/contactGroups'
GL_CONTACT_GROUP_GET_LINK = '/{{group_id}}'

GL_CONTACT_PROFILE_LINK = '/people/me'
GL_CONTACT_GET_LINK = '/people/{{people_id}}'
GL_CONTACT_CREATE_LINK = '/people:createContact'
GL_CONTACT_SEARCH_LINK = '/people:searchContacts'
GL_CONTACT_UPDATE_LINK = '/people/{{people_id}}:updateContact'
GL_CONTACT_DELETE_LINK = '/people/{{people_id}}:deleteContact'
GL_CONTACT_UPDATE_PHOTO_LINK = '/people/{{people_id}}:updateContactPhoto'
GL_CONTACT_DELETE_PHOTO_LINK = '/people/{{people_id}}:deleteContactPhoto'
GL_CONTACT_LIST_LINK = '/connections'
GL_CONTACT_SOURCE = 'GOOGLE_CONTACT'

GL_CONTACT_SEARCH_FLDS = [
    'names', 'emailAddresses', 'metadata', 'addresses', 'organizations', 'locations', 'phoneNumbers',
    'urls', 'memberships', 'relations', 'birthdays', 'userDefined', 'nicknames', 'occupations',
    'biographies', 'imClients', 'photos'
]
GL_CONTACT_UPDATE_FLDS = [
    'names', 'emailAddresses', 'addresses', 'organizations', 'phoneNumbers', 'urls', 'memberships',
    'relations', 'birthdays', 'userDefined', 'nicknames', 'occupations', 'biographies', 'imClients',
    'photos'
]
GL_CONTACT_UPDATE_ADDON_FLDS = [
    'names', 'emailAddresses', 'addresses', 'organizations', 'phoneNumbers', 'urls', 'memberships',
    'relations', 'birthdays', 'userDefined', 'nicknames', 'occupations', 'biographies', 'imClients'
]

GL_CONTACT_PROFILE_SERVICE = 'people'
GL_CONTACT_PROFILE_REQ_FLD_NAME = 'personFields'
GL_CONTACT_PROFILE_REQ_FLDS_SEP = ','

GL_PROFILE_EMAIL_FD = 'emailAddresses'
GL_PROFILE_EMAIL_FD_INTERNAL = 'value'
GL_PROFILE_NAME_FD = 'names'
GL_PROFILE_NAME_FD_INTERNAL = 'displayName'

GL_PROFILE_EXCEPT = "Oops, unable to get profile information, Please try again."

GL_CONTACTS_MEMBERSHIPS_GET_ERR = 'Oops, unable to get either local or server contact memberships. Please try again.'
GL_CONTACTS_MEMBERSHIPS_GET_EXCEPT = 'Oops, get contact memberships either local or server failed. Please try again.'
GL_CONTACTS_MEMBERSHIPS_CHK_ERR = 'Oops, unable to check either local or server contact memberships. Please try again.'
GL_CONTACTS_MEMBERSHIPS_CHK_EXCEPT = 'Oops, check contact memberships either local or server failed. Please try again.'
GL_CONTACTS_MEMBERSHIPS_CRT_ERR = 'Oops, unable to create either local or server contact memberships. Please try again.'
GL_CONTACTS_MEMBERSHIPS_CRT_EXCEPT = 'Oops, create contact memberships either local or server failed. Please try again.'
GL_CONTACTS_MEMBERSHIPS_UPD_ERR = 'Oops, unable to update either local or server contact memberships. Please try again.'
GL_CONTACTS_MEMBERSHIPS_UPD_EXCEPT = 'Oops, update contact memberships either local or server failed. Please try again.'

GL_CONTACTS_GET_ERR = 'Oops, unable to get either local or server contact. Please try again.'
GL_CONTACTS_GET_EXCEPT = 'Oops, get contact either local or server failed. Please try again.'
GL_CONTACTS_CHK_ERR = 'Oops, unable to check either local or server contact. Please try again.'
GL_CONTACTS_CHK_EXCEPT = 'Oops, check contact either local or server failed. Please try again.'
GL_CONTACTS_CRT_ERR = 'Oops, unable to create either local or server contact. Please try again.'
GL_CONTACTS_CRT_EXCEPT = 'Oops, create contact either local or server failed. Please try again.'
GL_CONTACTS_UPD_ERR = 'Oops, unable to update either local or server contact. Please try again.'
GL_CONTACTS_UPD_EXCEPT = 'Oops, create update either local or server failed. Please try again.'

GL_CONTACTS_IMP_NOT_FND = 'Oops, no contacts found from server. Please try again.'
GL_CONTACTS_IMP_EXCEPT = 'Oops, Import Contacts failed, Please try again.'
GL_CONTACTS_IMP_SERV_EXCEPT = 'Oops, Import Contacts from Server failed, Please try again.'
GL_CONTACTS_EXP_EXCEPT = 'Oops, Export Contacts failed, Please try again.'
GL_CONTACTS_EXP_SERV_EXCEPT = 'Oops, Export Contacts to Server failed, Please try again.'
GL_CONTACTS_EXP_NOT_FND = "Oops, Contacts are not found either according to date ranges"

GL_CONTACTS_IMAGE_DIMENSION = ['image_128', 'image_256', 'image_512','image_1024', 'image_1920']
GL_CONTACTS_USER_DEFINED_ID = "Odoo Database ID"

##################################################################################################################
# ############################################        Tasks Section         ######################################
##################################################################################################################

GL_TASKS_VERSION = 'v1'
GL_TASKS_SERVICE = 'tasks'
GL_TASKS_DEFAULT_FOLDER = 'My Tasks'
GL_TASKS_LIST_LINK = '/users/@me/lists'
GL_TASKS_GET_TASKS = '/lists'

GL_TASKS_IMP_EXCEPT = 'Oops, Import Tasks failed, Please try again.'
GL_TASKS_IMP_USER_NOT_FND = 'Oops, Unable to find required user info, Please try again.'
GL_TASKS_IMP_SERV_EXCEPT = 'Oops, Import Tasks from Server failed, Please try again.'
GL_TASKS_IMP_SERV_FOLD_NT = 'Oops, Import Tasks from Server, Folder Directory did not found, Please try again.'
GL_TASKS_IMP_SERV_REQ_ERR = 'Oops, Import Tasks from Server Request failed, Please try again.'
GL_TASKS_IMP_SERV_NOT_FND = 'Oops, Tasks not found, Please try again.'

GL_TASKS_EXP_EXCEPT = 'Oops, Export Tasks failed, Please try again.'
GL_TASKS_EXP_SERV_EXCEPT = 'Oops, Export Server Tasks Exception, Please try again.'
GL_TASKS_EXP_REC_NOT_FND = 'Oops, Export Tasks Records are not found, Please try again.'
GL_TASKS_EXP_REC_ERR = 'Oops, Export Tasks DLY Record Except, Please try again.'
GL_TASKS_EXP_REC_EXCEPT = 'Oops, Export Tasks DLY Record Except, Please try again.'

GL_TASKS_GET_PARTNER_NOT_FND = 'Oop, no partner found from local. Please try again.'
GL_TASKS_GET_PARTNER_ERR = 'Oop, unable to get partner from local. Please try again.'
GL_TASKS_GET_PARTNER_EXCEPT = 'Oop, get partner from local failed. Please try again.'
GL_TASKS_GET_LIST_NOT_FND = 'Oop, no tasklist found from server. Please try again.'
GL_TASKS_GET_LIST_ERR = 'Oop, unable to get tasklist from server. Please try again.'
GL_TASKS_GET_LIST_EXCEPT = 'Oop, get tasklist from server failed. Please try again.'
GL_TASKS_CHK_ERR = 'Oop, unable to check task in local. Please try again.'
GL_TASKS_CHK_EXCEPT = 'Oop, check task in local failed. Please try again.'
GL_TASKS_UPD_ERR = 'Oop, unable to update task in local. Please try again.'
GL_TASKS_UPD_EXCEPT = 'Oop, update task in local failed. Please try again.'
GL_TASKS_CRT_ERR = 'Oop, unable to create task in local. Please try again.'
GL_TASKS_CRT_EXCEPT = 'Oop, create task in local failed. Please try again.'
GL_TASKS_DON_ERR = 'Oop, unable to done task in local. Please try again.'
GL_TASKS_DON_EXCEPT = 'Oop, delete done in local failed. Please try again.'
GL_TASKS_DEL_ERR = 'Oop, unable to delete task in local. Please try again.'
GL_TASKS_DEL_EXCEPT = 'Oop, delete task in local failed. Please try again.'

####################################################################################################################
# ############################################        Mails Section      ###########################################
####################################################################################################################

GL_MAILS_VERSION = 'v1'
GL_MAILS_SERVICE = 'gmail'
GL_MAILS_MAX_PAGES = 3
GL_MAILS_FOLDER = "/users/{{google_id}}/messages"
GL_MAILS_ATTACHMENT = '/users/{{google_id}}/messages/{{message_id}}/attachments/{{attach_id}}'
GL_MAILS_SEND_MAIL = '/send'
GL_MAILS_FOLDER_NAME = 'INBOX'
GL_MAILS_MESSAGE_PART_TYPE = "text/plain"
GL_MAILS_MESSAGE_DATETIME_FORMAT_GMT = '%a, %d %b %Y %H:%M:%S GMT'
GL_MAILS_MESSAGE_DATETIME_FORMAT = '%a, %d %b %Y %H:%M:%S'
GL_MAILS_MESSAGE_DATETIME_FORMAT_WO = '%d %b %Y %H:%M:%S'
GL_MAILS_READ_MESSAGE = "/messages"

MS_MAILS_DEFAULT_FOLDER = "Inbox"
MS_MAILS_SND_MAIL = '/me/sendMail'
MS_MAILS_EADDR_FILTER = '/?$filter=from/emailAddress/address+eq+%27{{email}}%27'

GL_MAILS_IMP_SERV_ATCH_EXCEPT = "Oops, Mails attachment fetching failure, Please try again"
GL_MAILS_IMP_SERV_ATCH_ERR = "Oops, Download mail attachment failed, Please try again"
GL_MAILS_IMP_SERV_PG_EXCEPT = "Oops, Mails page fetching failure, Please try again"
GL_MAILS_IMP_SERV_PG_ERR = "Oops, Mails page failed, Please try again"
GL_MAILS_IMP_SERV_MLD_EXCEPT = "Oops, Mail details fetching failure, Please try again"
GL_MAILS_IMP_SERV_MLD_ERR = "Oops, Mail details failed, Please try again"
GL_MAILS_IMP_SERV_NOTFND = "Oops, Mails are not found, Please try again"

GL_MAILS_IMP_SERV_ERR = 'Oops, Import Mails failed, Please try again.'
GL_MAILS_IMP_SERV_EXCEPT = 'Oops, Unable to fetch mails from server, Please try again.'
GL_MAILS_IMP_SERV_FLD_ERR = 'Oops, Unable to fetch folder information from server, Please try again.'
GL_MAILS_IMP_EXCEPT = 'Oops, Unable to fetch records from server, Please try again.'
GL_MAILS_SEND_MAIL_EXCEPT = 'Oops, Unable to send mail, Please try again.'

GL_MAILS_CHK_ERR = 'Oop, unable to check mail in local. Please try again.'
GL_MAILS_CHK_EXCEPT = 'Oop, check mail in local failed. Please try again.'
GL_MAILS_UPD_ERR = 'Oop, unable to update mail in local. Please try again.'
GL_MAILS_UPD_EXCEPT = 'Oop, update mail in local failed. Please try again.'
GL_MAILS_CRT_ERR = 'Oop, unable to create mail in local. Please try again.'
GL_MAILS_CRT_EXCEPT = 'Oop, create mail in local failed. Please try again.'
GL_MAILS_DEL_ERR = 'Oop, unable to delete mail in local. Please try again.'
GL_MAILS_DEL_EXCEPT = 'Oop, delete mail in local failed. Please try again.'

##################################################################################################################
# #####################################     Calendar Events Section      #########################################
##################################################################################################################

GL_CALENDAR_SERVICE_VERSION = 'v3'
GL_CALENDAR_DRIVE_SERVICE = 'www'
GL_CALENDAR_CRUD_LINK = '/calendar/{{version}}/calendars/{{google_id}}/events'

GL_CALENDAR_CHK_ERR = 'Oop, unable to check calendar event either server or local. Please try again'
GL_CALENDAR_CHK_EXCEPT = 'Oop, check calendar event either server or local failed. Please try again'
GL_CALENDAR_UPD_ERR = 'Oop, unable to update calendar event either server or local. Please try again'
GL_CALENDAR_UPD_EXCEPT = 'Oop, update calendar event either server or local failed. Please try again'
GL_CALENDAR_CRT_ERR = 'Oop, unable to create calendar event either server or local. Please try again'
GL_CALENDAR_CRT_EXCEPT = 'Oop, create calendar event either server or local failed. Please try again'
GL_CALENDAR_DEL_ERR = 'Oop, unable to delete calendar event either server or local. Please try again'
GL_CALENDAR_DEL_EXCEPT = 'Oop, delete calendar event either server or local failed. Please try again'

GL_CALENDAR_EXP_SERV_EXCEPT = 'Oops, Export Calendar Events Server failed, Please try again.'
GL_CALENDAR_EXP_EXCEPT = 'Oops, Export Calendar Events failed, Please try again.'
GL_CALENDAR_EXP_NT_RCD = 'Oops, Export Calendar Events are not found, Please try again.'
GL_CALENDAR_EXP_NT_DFN = 'Oops, Export Calendar Events records build not proceed, Please try again.'

GL_CALENDAR_IMP_SERV_EXCEPT = 'Oops, Import Calendar Events from Server failed, Please try again.'
GL_CALENDAR_IMP_SERV_NOT_FND = 'Oops, No events are found from Server Calendar Events, Please try again.'
GL_CALENDAR_IMP_EXCEPT = 'Oops, Import Calendar Events failed, Please try again.'
GL_CALENDAR_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
GL_CALENDAR_PARTNER_REL_ID = 4

##################################################################################################################
# #########################################         GDrive Section           #####################################
##################################################################################################################

GL_DRIVE_VERSION = 'v3'
GL_DRIVE_META_DATA = 'drive/'
GL_DRIVE_UPLOAD_SERVICE = 'upload/drive/'
GL_DRIVE_FILES = '/files'
GL_DRIVE_FOLDER_MTYPE = 'application/vnd.google-apps.folder'
GL_DRIVE_SPACE = 'drive'

GL_DRIVE_CREATE_DIR = '/me/drive/root/children'
GL_DRIVE_READ_DIR = '/me/drive/root:/{{path}}:/children'
MS_DRIVE_SEARCH_DIR = "/me/drive/root/search(q='{{search}}')"
MS_DRIVE_UPLOAD_CONTENT = '/me/drive/root:/{{path}}:/content'


GL_DRIVE_EXP_SERV_EXCEPT = 'Oops, Export OneDrive Server failed, Please try again.'
GL_DRIVE_EXP_SERV_DIR_ERR = 'Oops, Unable to get directory in Export OneDrive Server, Please try again.'
GL_DRIVE_EXP_EXCEPT = 'Oops, Export OneDrive failed, Please try again.'
GL_DRIVE_EXPORT_DIR_ERR = 'Oops, Unable to create directory in OneDrive, Please try again.'
GL_DRIVE_EXPORT_DIR_EXCEPT = 'Oops, Unable to handle export directory creation in OneDrive, Please try again.'
GL_DRIVE_EXPORT_DIR_SERC_ERR = 'Oops, Unable to search directory in OneDrive, Please try again.'
GL_DRIVE_EXPORT_DIR_SERC_EXCEPT = 'Oops, Unable to handle search directory in OneDrive, Please try again.'

GL_DRIVE_FILE_EXPORT_ERR = 'Oops, Unable to export file to OneDrive, Please try again.'
GL_DRIVE_FILE_NOTFND = 'Oops, No data files found.'
GL_DRIVE_FILE_FETCH_ERR = "Oops, Unable to fetch internal files"
GL_DRIVE_DIR_FETCH_ERR = "Oops, Unable fetch server directory"

GL_DRIVE_IMP_SERV_EXCEPT = 'Oops, Import Drive from Server failed, Please try again.'
GL_DRIVE_IMP_EXCEPT = 'Oops, Import Drive failed, Please try again.'
GL_DRIVE_OPT_KEY = 'SUC'


###################################################################################################################
# ########################################         Connection Section         #####################################
###################################################################################################################

GL_CONN_URL_FAILED = "Oops, unable to generate authorization link."
GL_CONN_URL_EXCEPT = "Oops, unable to generate authorize link, Please try again."
GL_CONN_CRED_NOTFND = "Oops, unable to find credentials. Please try again."
GL_CONN_CRED_ACS_FAILED = "Oops, unable to generate access credentials, Please try again."
GL_CONN_CRED_ACS_EXCEPT = "Oops, unable to request for access credentials, Please try again."
GL_CONN_RAT_FAILED = "Oops, unable to refresh authorization information."
GL_CONN_RAT_EXCEPT = "Oops, unable to request for refresh authorize info, Please try again."


# System Messages
FAILURE_POP_UP_TITLE = 'System Alert'
AUTH_URL_CREATION_FAILED = 'Oops, system unable to create authorize link'
AUTH_URL_CREATION_EXCEPT = 'Oops, system found exception while creating authorize link'

SYNC_REQ_ERROR = 'Oops, unable to process given request, Please try again'
ACCESS_TOKEN_ERR_REFRESH = 'Oops, unable to refresh authorization information, Please try again'
ACCESS_TOKEN_EXCEPT = 'Oops, unable to get credentials information, Please try again'
ACCESS_TOKEN_CRED_NOT_FND = 'Oops, credentials information not found, Please save credentials before usage'
ACCESS_TOKEN_NOT_FND = 'Oops, authorization information not found, Please authorize account before usage'
ACCESS_TOKEN_INVALID = 'Oops, authorization information is invalid, Please authorize account again'
GRANT_CODE_ERR = 'Unable to get authorization code information, Please try again.'

CRON_JOB_CREATE = 'Google CronJob settings created successfully.'
CRON_JOB_UPDATE = 'Google CronJob settings updated successfully.'
CRON_JOB_ERROR = 'Oops, unable to save Google CronJob Settings. Please try again.'

NO_OPT_SECTION_ERR = 'Oops, no operation is not being selected, Please some operation to proceed.'
SYNC_PROCESS_MSG = "Synchronization process completed"
# DateTime Format
DEFAULT_DATETIME = '2020-01-01 07:00:00'
DEFAULT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_TZ_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
DEFAULT_CS_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_CS_DATE_FORMAT = '%Y-%m-%d'
INVALID_DATE_RANGES = "Invalid date ranges found, Please correct date ranges."
DEFAULT_RES_DATETIME_FORMAT = '%d/%m/%Y - %H:%M:%S'
