import os
import sys

_root = os.path.join(os.path.dirname(__file__), "resources")

is_debug = "--debug" in sys.argv


def get_resource(*subpaths) -> str:
    global _root
    return os.path.join(_root, *subpaths)