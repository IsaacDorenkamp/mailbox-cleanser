import appdirs
import os
import sys

DEBUG = "--debug" in sys.argv

SCOPES = ["openid", "https://mail.google.com/", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]
AUTH_SERVICE_URL = "http://localhost:5000/flows/google" if DEBUG else "https://auth-flow-provider-c1cc0d075dc3.herokuapp.com"

SETTINGS_DEFAULTS = {
    "junk_folder": "Junk"
}

APP_NAME = "Mailbox Cleanser"
APP_AUTHOR = "Unorthodox Software"

USER_CONFIG_DIR = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
USER_DATA_DIR = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
USER_CACHE_DIR = appdirs.user_cache_dir(APP_NAME, APP_AUTHOR)

for app_dir in [
    USER_CONFIG_DIR,
    USER_DATA_DIR,
    USER_CACHE_DIR
]:
    if not os.path.isdir(app_dir):
        os.makedirs(app_dir)
