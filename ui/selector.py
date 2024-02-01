import imaplib
import tkinter
import typing

from api.service import CleanserService
from .checklist import Checklist
import persist
from ui import concurrency


class Selector(tkinter.Frame):
    service: CleanserService

    __senders: Checklist
    __purge: tkinter.Button
    __busy: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = kwargs.get("service")
        self.__status = None
        self.__busy = False
        self.__setup_ui()
    
    def __setup_ui(self):
        # self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        tkinter.Label(self, text="Senders to Purge").grid(column=0, row=0, padx=5, sticky='nsw')

        self.__senders = Checklist(self, padx=5, borderwidth=1)
        self.__senders.grid(column=0, row=1, sticky='nesw')

        self.__purge = tkinter.Button(self, text="Purge E-mails", bg="red")
        self.__purge.configure(command=self.start_purge)
        self.__purge.grid(column=0, row=2, pady=7)

    def emit_status(self, status: str):
        self.__status = status
        concurrency.main(self.event_generate, "<<Status>>")
    
    def start_purge(self):
        task = concurrency.DeferredTask(self.perform_purge)
        task.run()

    def perform_purge(self):
        concurrency.main(self.__senders.set_enabled, False)
        concurrency.main(self.__purge.configure, text="PURGING...", state="disabled")
        self.emit_status("Finding e-mails to purge...")

        self.__busy = True

        senders = concurrency.main(self.__senders.get_checked)
        try:
            to_purge = self.service.find_emails_to_cleanse(senders)
        except imaplib.IMAP4.error:
            import traceback
            traceback.print_exc()

            self.emit_status("Aggregation query failed. It is possible that a selected address is invalid.")
            self.__end_purge()
            return

        self.emit_status("Purging %d e-mails..." % len(to_purge))
        try:
            self.service.cleanse_emails(to_purge)
        except imaplib.IMAP4.error:
            self.emit_status("Could not move e-mails to the Junk folder.")
            self.__end_purge()
            return

        self.emit_status("E-mails purged.")
        concurrency.main(self.__remove_senders)

        self.__end_purge()

    def __end_purge(self):
        concurrency.main(self.__purge.configure, text="Purge E-mails", state="normal")
        concurrency.main(self.__senders.set_enabled, True)
        self.__busy = False
    
    def __remove_senders(self):
        self.__senders.remove(self.__senders.get_checked())

        sender_store = persist.getvalue("unique-senders")
        if sender_store:
            items = self.__senders.get_items()
            user = self.service.imap.user
            sender_store[user] = list(items)
            persist.setvalue("unique-senders", sender_store)

    def populate_senders(self, senders: typing.Iterable[str]):
        for sender in senders:
            self.__senders.append(sender)

    @property
    def status(self) -> str | None:
        return self.__status
    
    @property
    def busy(self) -> bool:
        return self.__busy

