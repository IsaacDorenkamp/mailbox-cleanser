from __future__ import annotations

from googleapiclient.discovery import build

from abc import ABCMeta, abstractclassmethod, abstractmethod
import datetime
import functools
import imaplib
import logging
import json
import re
import socket
import typing
import warnings

import config
from credentials import Credentials


class Registry(type):
    __registries = {}

    def __new__(cls, name, bases, dct):
        if "_abstract_" in dct:
            if dct["_abstract_"]:
                if name in Registry.__registries:
                    raise TypeError("A registry already exists for class name '%s'" % name)

                Registry.__registries[name] = {}

            del dct["_abstract_"]
        
        new_type = super().__new__(cls, name, bases, dct)
        
        for base in bases:
            if isinstance(base, Registry):
                for superclass in base.__mro__:
                    if superclass.__name__ in Registry.__registries:
                        Registry.__registries[superclass.__name__][name] = new_type

        return new_type
    
    def __getitem__(cls, key):
        return Registry.__registries[cls.__name__][key]


class AbstractRegistry(ABCMeta, Registry):
    def __new__(cls, name, bases, dct):
        return super().__new__(cls, name, bases, dct)


class GenericIMAP(metaclass=AbstractRegistry):
    # Courtesy of https://pymotw.com/3/imaplib/
    LIST_RESPONSE_PATTERN = re.compile(
        r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)'
    )

    _abstract_ = True

    @abstractmethod
    def authenticate(self):
        raise NotImplementedError()
    
    @abstractmethod
    def logout(self):
        raise NotImplementedError()
    
    @abstractmethod
    def serialize(self) -> typing.Any:
        raise NotImplementedError()
    
    @abstractclassmethod
    def build(cls, json_data: typing.Any, debug: bool = False) -> GenericIMAP:
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def imap(self) -> imaplib.IMAP4:
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def user(self) -> str:
        raise NotImplementedError()
    
    def check_folder(self, folder: str) -> bool:
        _, folder_list = self.imap.list()
        folder_names = [
            GenericIMAP.LIST_RESPONSE_PATTERN.match(item.decode('utf-8')).group('name')[1:-1] for item in folder_list
        ]
        return folder in folder_names
    
    def delete_messages(self, messages: set[int], source_mailbox: str = 'Inbox'):
        self.imap.select(source_mailbox)

        message_set = ",".join([str(message) for message in messages])

        try:
            status, _ = self.imap.store(message_set, "+FLAGS", "\\Deleted")
            if status != "OK":
                raise GenericIMAP.OperationError("Delete failed: could not mark messages as deleted.")
            
            status, _ = self.imap.expunge()
            if status != "OK":
                raise GenericIMAP.OperationError("Expunge failed: could not expunge deleted messages")
        except imaplib.IMAP4.error as err:
            raise GenericIMAP.OperationError("Delete failed: IMAP error. Message: " + str(err))
    
    def move(self, messages: set[int], mailbox: str, source_mailbox: str = 'Inbox'):
        self.imap.select(source_mailbox)

        message_set = ",".join([str(message) for message in messages])

        try:
            status, _ = self.imap.copy(message_set, mailbox)
            if status != "OK":
                raise GenericIMAP.OperationError("Move failed: could not copy messages to mailbox '%s'" % mailbox)
            
            status, _ = self.imap.store(message_set, "+FLAGS", "\\Deleted")
            if status != "OK":
                raise GenericIMAP.OperationError("Move failed: could not mark messages as deleted.")
            
            status, _ = self.imap.expunge()
            if status != "OK":
                raise GenericIMAP.OperationError("Expunge failed: could not expunge deleted messages")
        except imaplib.IMAP4.error as err:
            raise GenericIMAP.OperationError("Move failed: IMAP error. Message: " + str(err))
    
    class StateError(Exception):
        def __init__(self, msg):
            super().__init__(msg)
    
    class OperationError(Exception):
        def __init__(self, msg):
            super().__init__(msg)


class GmailIMAP(GenericIMAP):
    GMAIL_IMAP_HOST = "imap.gmail.com"

    __user: str
    __credentials: Credentials
    __client: imaplib.IMAP4
    __authenticated: bool

    def __init__(self, user: str, credentials: Credentials, debug: bool = False):
        self.__user = user
        self.__credentials = credentials

        if debug:
            imaplib.Debug = 4

        try:
            self.__client = imaplib.IMAP4_SSL(GmailIMAP.GMAIL_IMAP_HOST)
        except socket.gaierror:
            raise GenericIMAP.OperationError("Could not connect to host.")

        if debug:
            imaplib.Debug = 0

        self.__authenticated = False
    
    def authenticate(self):
        if self.authenticated:
            raise GenericIMAP.StateError("Already authenticated!")

        self.__client.authenticate("XOAUTH2", functools.partial(GmailIMAP.gmail_auth_cbk, self.__user, self.__credentials.token))
        self.__authenticated = True

    def logout(self):
        self.__require_auth()
        self.__client.logout()
        self.__authenticated = False

    def __require_auth(self):
        if not self.__authenticated:
            raise GenericIMAP.StateError("Must be authenticated first.")
    
    @staticmethod
    def gmail_auth_cbk(user: str, token: str, server_response: bytes) -> bytes:
        if not server_response:
            # initial data
            return (f'user={user}\u0001auth=Bearer {token}\u0001\u0001').encode()
        else:
            return b''
        
    def serialize(self) -> typing.Any:
        # For some reason, credentials has a function to convert to JSON,
        # but not a simple Python dictionary. This is a workaround.
        return json.loads(self.__credentials.to_json())
    
    @classmethod
    def refresh_credentials(credentials: Credentials):
        credentials.refresh()
    
    @classmethod
    def build(cls, json_data: typing.Any, debug: bool = False) -> GmailIMAP | None:
        try:
            expiry_raw = json_data.get("expiry_date")
            if expiry_raw and isinstance(expiry_raw, int):
                utc_expiry = datetime.datetime.fromtimestamp(expiry_raw // 1000, tz=datetime.timezone.utc)
                utc_expiry = utc_expiry.replace(tzinfo=None)
            else:
                utc_expiry = None

            creds = Credentials(json_data["token"], refresh_token=json_data.get("refresh_token"), expiry=utc_expiry)

            if utc_expiry:
                logging.info("Credentials constructed, expires at %s" % utc_expiry.isoformat())
            else:
                logging.info("Credentials constructed, no expiration date.")
        except ValueError as error:
            warnings.warn("Could not construct credentials object: \"%s\"" % str(error))
            return None
        
        if creds:
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    logging.info("Credentials expired, refreshing.")
                    cls.refresh_credentials(creds)
                else:
                    return None
            
            try:
                user = cls.get_user_email(creds)
            except:
                return None

            return cls(
                user,
                creds,
                debug=debug
            )
        else:
            return None
    
    @staticmethod
    def get_user_email(credentials: Credentials) -> str:
        userinfo_service = build(
            serviceName="oauth2", version="v2", credentials=credentials
        )

        response = userinfo_service.userinfo().get().execute()

        return response["email"]
    
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


class ManualIMAP(GenericIMAP):
    __user: str
    __client: imaplib.IMAP4
    __authenticated: bool

    __password: str

    def __init__(self, user: str, password: str, host: str, debug: bool = False):
        self.__user = user
        self.__password = password
        self.__authenticated = False

        if debug:
            imaplib.Debug = 4

        try:
            self.__client = imaplib.IMAP4_SSL(host)
        except socket.gaierror:
            raise GenericIMAP.OperationError("Could not connect to host '%s'" % host)

        if debug:
            imaplib.Debug = 0

    def authenticate(self):
        if self.authenticated:
            raise GenericIMAP.StateError("Already authenticated!")

        self.__client.login(self.__user, self.__password)
        self.__authenticated = True
    
    def logout(self):
        self.__require_auth()
        self.__client.logout()
        self.__authenticated = False

    def __require_auth(self):
        if not self.__authenticated:
            raise GenericIMAP.StateError("Must be authenticated first.")
        
    def serialize(self) -> typing.Any:
        return {
            "user": self.__user,
            "password": self.__password,
            "host": self.__client.host
        }
    
    @classmethod
    def build(cls, json_data: typing.Any, debug: bool = True) -> ManualIMAP | None:
        try:
            return cls(
                json_data["user"],
                json_data["password"],
                json_data["host"],
                debug=debug
            )
        except KeyError:
            return None
    
    @property
    def user(self) -> str:
        return self.__user
    
    @property
    def authenticated(self) -> bool:
        return self.__authenticated
    
    @property
    def imap(self) -> imaplib.IMAP4:
        return self.__client
