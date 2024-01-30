import appdirs
import os

SCOPES = ["openid", "https://mail.google.com/", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]

APP_NAME = "Mailbox Cleanser"
APP_AUTHOR = "Unorthodox Software"

USER_CONFIG_DIR = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)

if not os.path.isdir(USER_CONFIG_DIR):
    os.makedirs(USER_CONFIG_DIR)