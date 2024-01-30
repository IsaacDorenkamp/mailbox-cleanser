import tkinter
import ttkwidgets

from . import concurrency
from .checklist import Checklist

from api import CleanserService, GmailIMAP
import api.imap
import credentials


class MainApplication(tkinter.Frame):
    senders: Checklist
    status: tkinter.Label

    __client: GmailIMAP
    __service: CleanserService

    def __init__(self, parent):
        super().__init__(parent)
        self.__setup_ui()
    
    def __setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.senders = Checklist(self)
        self.senders.grid(column=0, row=0, sticky="nesw")

        self.status = tkinter.Label(self, text="Setting up...")
        self.status.grid(column=0, row=1, sticky="nsw", padx=10)
    
    def _setup_imap_client(self):
        gmail_credentials = credentials.get_credentials()
        user_email = api.imap.get_user_email(gmail_credentials)
        self.__client = GmailIMAP(user_email, gmail_credentials.token)
        self.__service = CleanserService(self.__client)
        concurrency.main(self.status.configure, text="Authenticating...")
    
    
    def load_unique_senders(self) -> set[str]:
        return self.__service.get_unique_senders()
    
    def populate_unique_senders(self, senders: set[str]):
        for sender in senders:
            self.senders.insert(tkinter.END, sender)
    
    def set_status(self, status: str):
        concurrency.main(self.status.configure, text=status)
    
    def setup_imap_and_load_data(self):
        self.set_status("Connecting...")
        self._setup_imap_client()
        self.set_status("Authenticating...")
        self.__client.authenticate()
        self.set_status("Fetching unique senders...")

        senders = self.load_unique_senders()
        concurrency.main(self.populate_unique_senders, senders)
        self.set_status("Done.")


def main():
    root = tkinter.Tk()
    root.wm_title("Mailbox Cleanser")
    root.geometry("400x350")

    app = MainApplication(root)
    app.pack(fill=tkinter.BOTH, expand=tkinter.YES)
    

    # if we don't do this, the window won't populate until it is focused.
    root.wm_withdraw()
    root.update()
    root.after(1, root.deiconify)
    
    global running
    running = True
    def end_app():
        global running
        running = False
        root.destroy()

    deferred = concurrency.DeferredTask(app.setup_imap_and_load_data)
    deferred.run()

    root.protocol("WM_DELETE_WINDOW", end_app)
    while running:
        concurrency.process()
        root.update()
        root.update_idletasks()
