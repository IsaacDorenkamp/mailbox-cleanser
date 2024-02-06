import json
import os
import re
import time
import typing
import warnings

from config import USER_CACHE_DIR


VALID_KEY_RE = r'^[a-zA-Z0-9_\-]+$'


def setvalue(key: str, value: typing.Any):
    if not re.match(VALID_KEY_RE, key):
        raise ValueError("key must contain only alphanumeric characters, underscores, and hyphens.")

    entry_data = {
        "modified": time.time(),
        "data": value
    }

    with open(os.path.join(USER_CACHE_DIR, "cache-%s.json" % key), "w", encoding="utf-8") as fp:
        json.dump(entry_data, fp)


def getvalue(key: str, expire_at: int | None = None) -> typing.Any | None:
    try:
        with open(os.path.join(USER_CACHE_DIR, "cache-%s.json" % key), "r", encoding="utf-8") as fp:
            cache_entry = json.load(fp)
        
        if not expire_at:
            return cache_entry["data"]
        else:
            if cache_entry["modified"] >= expire_at:
                return None
            else:
                return cache_entry["data"]
    except FileNotFoundError:
        return None
    except (json.decoder.JSONDecodeError, KeyError, TypeError) as exc:
        import traceback
        traceback.print_exc()
        warnings.warn("Cache entry for key '%s' exists, but the data is malformed. This could mean the data is not valid JSON, does not have the expected keys, or contains an invalid "
                      "'modified' value.")
        return None


def clear_all():
    values = os.listdir(USER_CACHE_DIR)
    for item in map(lambda value: os.path.join(USER_CACHE_DIR, value), values):
        if os.path.isfile(item) and item.endswith(".json"):
            os.unlink(item)
