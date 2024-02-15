import imaplib
import tkinter
import tkinter.ttk as ttk
import tkinter.messagebox
import typing

from api.service import CleanserService
from api.imap import GenericIMAP
from .checklist import Checklist
import persist
from ui import concurrency


class Selector(ttk.Frame):
    __service: CleanserService

    __senders: Checklist
    __purge: ttk.Button
    __busy: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__service = None
        self.__status = None
        self.__busy = False
        self.__setup_ui()
    
    def __setup_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ttk.Label(self, text="Senders to Purge", style="Padded.TLabel").grid(column=0, row=0, padx=5, sticky='nsw')

        self.__senders = Checklist(self, borderwidth=1)
        self.__senders.grid(column=0, row=1, sticky='nesw')

        self.__purge = ttk.Button(self, text="Purge E-mails")
        self.__purge.configure(command=self.start_purge, state=tkinter.DISABLED)
        self.__purge.grid(column=0, row=2, pady=7)

    def emit_status(self, status: str):
        self.__status = status
        concurrency.main(self.event_generate, "<<Status>>")
    
    def start_purge(self):
        senders = len(self.__senders.get_checked())
        message = "Are you sure you want to purge e-mails from %d senders?" % senders
        if not self.__service.junk_folder:
            message += " NOTE: No junk folder is configured - e-mails will be deleted permanently!"
        confirmed = tkinter.messagebox.askyesno("Confirm", message)
        if confirmed:
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
        
        if len(to_purge) == 0:
            self.emit_status("Found no e-mails to purge!")
            self.__end_purge()
            return

        self.emit_status("Purging %d e-mails..." % len(to_purge))
        try:
            self.service.cleanse_emails(to_purge)
        except (imaplib.IMAP4.error, GenericIMAP.OperationError) as err:
            self.emit_status("Could not move e-mails to the Junk folder. Reason: %s" % str(err))
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

    def clear_senders(self):
        self.__senders.clear()

    def set_enabled(self, enabled: bool):
        state = tkinter.NORMAL if enabled else tkinter.DISABLED
        self.__senders.set_enabled(enabled)
        self.__purge.configure(state=state)

    @property
    def status(self) -> str | None:
        return self.__status
    
    @property
    def busy(self) -> bool:
        return self.__busy
    
    @property
    def service(self) -> CleanserService | None:
        return self.__service

    @service.setter
    def service(self, service: CleanserService | None):
        self.__service = service
        concurrency.main(self.__purge.configure, state=tkinter.DISABLED if not service else tkinter.NORMAL)
