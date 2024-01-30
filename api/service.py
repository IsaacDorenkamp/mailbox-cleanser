import email
import re

from .imap import GmailIMAP


def get_address_from_header(from_header: str) -> str:
    if '<' in from_header:
        return re.match(r"^.*?<(.+?)>$", from_header, re.DOTALL).group(1)
    else:
        return from_header


class CleanserService:
    __client: GmailIMAP

    class ServiceError(RuntimeError):
        def __init__(self, msg: str):
            super().__init__(msg)

    def __init__(self, client: GmailIMAP):
        self.__client = client
    
    def get_unique_senders(self) -> set[str]:
        client = self.__client

        client.imap.select()
        status, response = client.imap.search(None, "ALL")

        if status != "OK":
            raise CleanserService.ServiceError("Failed to fetch message list.")

        response = b",".join(response[0].split(b" "))

        status, response = client.imap.fetch(response, "(BODY.PEEK[HEADER.FIELDS (FROM)])")

        if status != "OK":
            raise CleanserService.ServiceError("Failed to fetch headers.")

        unique_senders = set()

        header_parser = email.parser.HeaderParser()
        for item in response:
            if isinstance(item, tuple):
                parsed = header_parser.parsestr(item[1].decode('utf-8'))
                unique_senders.add(get_address_from_header(parsed.get("From")))
        
        return unique_senders

    def find_emails_to_cleanse(self, senders: set[str], source_mailbox: str = 'Inbox') -> set[int]:
        self.__client.imap.select(source_mailbox)

        clauses = ["OR" for _ in range(max(0, len(senders) - 1))]

        for sender in senders:
            clauses.append("FROM '%s'" % sender)

        status, response = self.__client.imap.search(None, " ".join(clauses))

        if status != "OK":
            raise CleanserService.ServiceError("Search returned non-OK status: %s" % status)

        return {int(uid) for uid in response[0].decode('utf-8').split(' ')}
    
    def cleanse_emails(self, uids: set[int], source_mailbox: str = 'Inbox'):
        self.__client.move(uids, "Junk", source_mailbox=source_mailbox)
