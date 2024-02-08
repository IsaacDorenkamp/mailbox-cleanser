import email
import imaplib
import re

from .imap import GenericIMAP
import util


def get_address_from_header(from_header: str) -> str:
    if '<' in from_header:
        return re.match(r"^.*?<(.+?)>$", from_header, re.DOTALL).group(1).strip()
    else:
        return from_header


class CleanserService:
    __client: GenericIMAP
    
    __junk_folder: str | None

    class ServiceError(RuntimeError):
        """
        An error raised when service functions encounter errors.
        """

    def __init__(self, client: GenericIMAP, junk_folder: str | None = None):
        self.__client = client
        self.__junk_folder = junk_folder
    
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

        email_ids = set()

        # Servers don't seem to like extremely large search queries, so we'll break down large groups of
        # senders into smaller batches.
        for sender_batch in util.produce_batches(senders, 25):
            clauses = ["OR" for _ in range(max(0, len(sender_batch) - 1))]

            for sender in sender_batch:
                clauses.append("FROM \"%s\"" % sender)

            try:
                status, response = self.__client.imap.search(None, *clauses)
            except imaplib.IMAP4.error as err:
                raise CleanserService.ServiceError("Search returned error: %s" % str(err))

            if status != "OK":
                raise CleanserService.ServiceError("Search returned non-OK status: %s" % status)

            email_ids |= {int(uid) for uid in response[0].decode('utf-8').split(' ')}
        
        return email_ids
    
    def cleanse_emails(self, uids: set[int], source_mailbox: str = 'Inbox'):
        if self.__junk_folder:
            folder_exists = self.__client.check_folder(self.__junk_folder)
            if not folder_exists:
                raise GenericIMAP.OperationError("Folder '%s' does not exist" % self.__junk_folder)
            
            self.__client.move(uids, self.__junk_folder, source_mailbox=source_mailbox)
        else:
            self.__client.delete_messages(uids, source_mailbox=source_mailbox)

    @property
    def imap(self) -> GenericIMAP:
        return self.__client
    
    @property
    def junk_folder(self) -> str | None:
        return self.__junk_folder
    
    @junk_folder.setter
    def junk_folder(self, junk_folder: str):
        self.__junk_folder = junk_folder
