import appdirs
import os
import sys

DEBUG = "--debug" in sys.argv

SCOPES = ["openid", "https://mail.google.com/", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]
AUTH_SERVICE_URL = f"http://localhost:{os.environ.get('AUTH_SERVICE_PORT', '5000')}" if DEBUG else "http://auth.9tailedstudios.com"

SETTINGS_DEFAULTS = {
    "junk_folder": "Junk"
}

APP_NAME = "purgetool"
APP_AUTHOR = "9tailed Studios"

USER_CONFIG_DIR = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
USER_DATA_DIR = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
USER_CACHE_DIR = appdirs.user_cache_dir(APP_NAME, APP_AUTHOR)
USER_LOG_DIR = appdirs.user_log_dir(APP_NAME, APP_AUTHOR)

for app_dir in [
    USER_CONFIG_DIR,
    USER_DATA_DIR,
    USER_CACHE_DIR,
    USER_LOG_DIR
]:
    if not os.path.isdir(app_dir):
        os.makedirs(app_dir)
