from typing import Any


def get_sender(message: dict[str, Any]) -> str | None:
    header_entry = [header["value"] for header in message["payload"]["headers"] if header["name"].lower() == "to"]
    if header_entry:
        return header_entry[0]
    else:
        return None


def get_unique_senders(threads: list[dict[str, Any]]) -> set[str]:
    all_senders = set()
    for thread in threads:
        all_senders |= {get_sender(message) for message in thread["messages"]}
    
    return all_senders


def get_yes_no(question: str, default: bool = True):
    result = None
    while result not in ["y", "n", ""]:
        if result is not None:
            print("Invalid response '%s'. Please input a 'y' or 'n'. %s" % (result, question))

        result = input(question).strip().lower()
    
    if result == "y":
        return True
    elif result == "n":
        return False
    else:
        return default
