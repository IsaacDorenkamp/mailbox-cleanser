import config
from . import imap
from . import service

import json
import os
import warnings


def create_service(debug: bool = False) -> service.GenericIMAP | None:
    service_config_file = os.path.join(config.USER_CONFIG_DIR, "service_config.json")

    try:
        with open(service_config_file, "r") as fp:
            config_data = json.load(fp)
    except FileNotFoundError:
        return None
    except json.decoder.JSONDecodeError:
        warnings.warn("Service configuration file exists, but is not valid JSON.")
        return None
    
    if not isinstance(config_data, dict):
        warnings.warn("Service configuration file exists and contains valid JSON, but is not a map.")
        return None
    
    try:
        imap_class_name = config_data.get("class")
        if not imap_class_name:
            return None

        imap_class = service.GenericIMAP[imap_class_name]
    except KeyError as ke:
        warnings.warn("Service configuration file exists, but references unknown IMAP service %s" % str(ke))
        return None
    
    if "data" not in config_data:
        warnings.warn("Service configuration file exists, but does not contain data to build IMAP service")
        return None

    imap_instance = imap_class.build(config_data["data"], debug=debug)

    if imap_instance is None:
        return None
    else:
        return imap_instance


def save_imap_service(imap_service: imap.GenericIMAP, target: str | None = None):
    build_data = imap_service.serialize()
    full_data = {
        "class": imap_service.__class__.__name__,
        "data": build_data
    }

    target = target or os.path.join(config.USER_CONFIG_DIR, "service_config.json")

    with open(target, "w") as fp:
        json.dump(full_data, fp)
