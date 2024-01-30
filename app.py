import argparse
import typing

import credentials
from api import *
import api.imap
import util


def gather_elimination_candidates(senders: typing.Iterable[str]) -> set[str]:
    all_candidates = sorted(senders)
    to_eliminate = set()
    for candidate in all_candidates:
        should_eliminate = util.get_yes_no("Should eliminate %s (y/N)? " % candidate, default=False)
        if should_eliminate:
            to_eliminate.add(candidate)
    
    return to_eliminate


def main(options: argparse.Namespace):
    gmail_credentials = credentials.get_credentials(force=options.force_authorize)
    imap_client = GmailIMAP(api.imap.get_user_email(gmail_credentials), gmail_credentials.token)

    imap_client.authenticate()

    service = CleanserService(imap_client)

    if not options.remove:
        to_eliminate = gather_elimination_candidates(service.get_unique_senders())
    else:
        to_eliminate = set([option.strip() for option in options.remove.split(',')])

    print("Senders to eliminate:", ", ".join(to_eliminate))

    to_cleanse = service.find_emails_to_cleanse(to_eliminate)
    
    try:
        service.cleanse_emails(to_cleanse)
        print("Emails cleansed.")
    except (CleanserService.ServiceError, GmailIMAP.OperationError) as exc:
        print("Cleansing did not complete. Reason:", str(exc))

    imap_client.logout()
