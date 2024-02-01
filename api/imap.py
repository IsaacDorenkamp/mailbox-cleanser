from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import functools
import imaplib


def get_user_email(credentials: Credentials) -> str:
    userinfo_service = build(
        serviceName="oauth2", version="v2", credentials=credentials
    )

    response = userinfo_service.userinfo().get().execute()

    return response["email"]


def gmail_auth_cbk(user: str, token: str, server_response: bytes) -> bytes:
    if not server_response:
        # initial data
        return (f'user={user}\u0001auth=Bearer {token}\u0001\u0001').encode()
    else:
        return b''


class GmailIMAP:
    __user: str
    __token: str
    __client: imaplib.IMAP4
    __authenticated: bool

    def __init__(self, user: str, token: str):
        self.__user = user
        self.__token = token
        self.__client = imaplib.IMAP4_SSL("imap.gmail.com")
        self.__authenticated = False
    
    def authenticate(self):
        self.__client.authenticate("XOAUTH2", functools.partial(gmail_auth_cbk, self.__user, self.__token))
        self.__authenticated = True

    def logout(self):
        self.__require_auth()
        self.__client.logout()
        self.__authenticated = False

    def __require_auth(self):
        if not self.__authenticated:
            raise GmailIMAP.StateError("Must be authenticated first.")
    
    def move(self, messages: set[int], mailbox: str, source_mailbox: str = 'Inbox'):
        self.imap.select(source_mailbox)

        message_set = ",".join([str(message) for message in messages])

        try:
            status, _ = self.imap.copy(message_set, mailbox)
            if status != "OK":
                raise GmailIMAP.OperationError("Move failed: could not copy messages to mailbox '%s'" % mailbox)
            
            status, _ = self.imap.store(message_set, "+FLAGS", "\\Deleted")
            if status != "OK":
                raise GmailIMAP.OperationError("Move failed: could not mark messages as deleted.")
            
            status, _ = self.imap.expunge()
            if status != "OK":
                raise GmailIMAP.OperationError("Expunge failed: could not expunge deleted messages")
        except imaplib.IMAP4.error as err:
            raise GmailIMAP.OperationError("Move failed: IMAP error. Message: " + str(err))
    
    def has_capability(self, capability: str) -> bool:
        return capability in self.__client.capabilities
    
    @property
    def user(self) -> str:
        return self.__user

    @property
    def authenticated(self):
        return self.__authenticated
    
    @property
    def imap(self) -> imaplib.IMAP4:
        self.__require_auth()
        return self.__client
    
    class StateError(Exception):
        def __init__(self, msg):
            super().__init__(msg)
    
    class OperationError(Exception):
        def __init__(self, msg):
            super().__init__(msg)
