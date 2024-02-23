import config
from . import imap
from . import service
import util

import json
import logging
import os
import typing
import warnings


CONFIG_VERSION = "2"
SERVICE_CONFIG_FILE = os.path.join(config.USER_CONFIG_DIR, "service_config.json")


@util.version("1")
def format_service_config(data: dict[str, typing.Any]):
    account = data.copy()
    if "id" not in data:
        account["id"] = 0
    
    return {
        "accounts": [account],
        "active": account["id"]
    }


@util.version("2")
def format_service_config(data: dict[str, typing.Any]):
    return data.copy()


@util.version("1")
def create_service_versioned(data: dict[str, typing.Any], debug: bool = False):
    try:
        imap_class_name = data.get("class")
        if not imap_class_name:
            return None

        imap_class = service.GenericIMAP[imap_class_name]
    except KeyError as ke:
        warnings.warn("Service configuration file exists, but references unknown IMAP service %s" % str(ke))
        return None
    
    if "data" not in data:
        warnings.warn("Service configuration file exists, but does not contain data to build IMAP service")
        return None

    imap_instance = imap_class.build(data["data"], debug=debug)

    if imap_instance is None:
        return None
    else:
        return imap_instance


@util.version("2")
def create_service_versioned(data: dict[str, typing.Any], debug: bool = False):
    accounts = data.get("accounts", [])
    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list")

    active = data["active"]
    use_data = next(filter(lambda entity: entity["id"] == active, accounts), None)
    if use_data:
        return create_service_versioned(use_data, version="1", debug=debug)
    else:
        raise ValueError("Could not find active account with id '%s'" % active)


def create_service(debug: bool = False) -> tuple[dict[str, typing.Any], service.GenericIMAP] | None:
    try:
        with open(SERVICE_CONFIG_FILE, "r") as fp:
            config_data = json.load(fp)
    except FileNotFoundError:
        warnings.warn("Service configuration file does not exist.")
        return None
    except json.decoder.JSONDecodeError:
        warnings.warn("Service configuration file exists, but is not valid JSON.")
        return None
    
    if not isinstance(config_data, dict):
        warnings.warn("Service configuration file exists and contains valid JSON, but is not a map.")
        return None
    
    version = config_data.pop("version", "1")

    try:
        service = create_service_versioned(config_data, version=version, debug=debug)
        if service is None:
            return None

        formatted = format_service_config(config_data, version=version)
        formatted["version"] = CONFIG_VERSION
        return formatted, service
    except Exception as exc:
        logging.exception(str(exc))
        return None


def save_service_config(data: dict[str, typing.Any]):
    with open(SERVICE_CONFIG_FILE, "w") as fp:
        json.dump(data, fp)
