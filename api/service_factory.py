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
            warnings.warn("No IMAP class specified. Account data: %s" % str(data))
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


def create_service(service_config: dict[str, typing.Any], debug: bool = False) -> service.GenericIMAP | None:
    if not isinstance(service_config, dict):
        warnings.warn("Service configuration file exists and contains valid JSON, but is not a map.")
        return None
    
    version = service_config.pop("version", "1")

    try:
        return create_service_versioned(service_config, version=version, debug=debug)
    except Exception as exc:
        logging.exception(str(exc))
        return None


def save_service_config(data: dict[str, typing.Any]):
    with open(SERVICE_CONFIG_FILE, "w") as fp:
        json.dump(data, fp)
