from . import constants
import requests


def generate_auth_url(gl_credentials):
    auth_url = constants.GL_AUTH_URL + \
               '?prompt=consent&access_type=offline&include_granted_scopes=true&response_type=code' + \
               '&scope=' + '+'.join([constants.GL_SCOPE_BASE_URL + scope for scope in constants.GL_SCOPES]) + \
               '&redirect_uri=' + gl_credentials["redirect_url"] + '&client_id=' + gl_credentials["client_id"]
    return auth_url


def get_authorize_token(code, gl_credentials):
    params = {
        "code": code,
        "client_id": gl_credentials["client_id"],
        "client_secret": gl_credentials["client_secret"],
        "redirect_uri": gl_credentials["redirect_url"],
        "grant_type": "authorization_code"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(constants.GL_AUTH_EXCODE_URL, data=params, headers=headers).json()
    return response


def get_refresh_authorize_token(refresh_token, gl_credentials):
    params = {
        "client_id": gl_credentials["client_id"],
        "client_secret": gl_credentials["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(constants.GL_AUTH_EXCODE_URL, data=params, headers=headers).json()
    return response
