import tkinter
import tkinter.messagebox

from . import concurrency
from .selector import Selector

from api import CleanserService, GmailIMAP
import api.imap
import credentials
import persist


class MainApplication(tkinter.Frame):
    selector: Selector
    status: tkinter.Label

    __client: GmailIMAP
    __service: CleanserService

    def __init__(self, parent):
        super().__init__(parent)
        self.__setup_ui()
    
    def __setup_ui(self):
        self.status = tkinter.Label(self, text="Setting up...", anchor='w')
        self.status.pack(side=tkinter.BOTTOM, fill=tkinter.X, padx=5)

        self.selector = Selector(self)
        self.selector.bind("<<Status>>", self.on_selector_status)
        self.selector.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=tkinter.YES)
    
    def _setup_imap_client(self):
        gmail_credentials = credentials.get_credentials()
        user_email = api.imap.get_user_email(gmail_credentials)
        self.__client = GmailIMAP(user_email, gmail_credentials.token)
        self.__service = CleanserService(self.__client)
        self.selector.service = self.__service
        concurrency.main(self.status.configure, text="Authenticating...")
    
    def on_selector_status(self, _):
        self.set_status(self.selector.status)
    
    def load_unique_senders(self, use_cache: bool = True) -> set[str]:
        unique_senders_store = persist.getvalue("unique-senders")  # even if not using cache, we will need to merge with this existing value
        if not unique_senders_store:
            unique_senders_store = {}

        if use_cache:
            if unique_senders_store:
                unique_senders = unique_senders_store.get(self.__client.user)
            else:
                unique_senders = None
            
            if unique_senders:
                return set(unique_senders)

        unique_senders = self.__service.get_unique_senders()
        unique_senders_store[self.__client.user] = list(unique_senders)
        
        persist.setvalue("unique-senders", unique_senders_store)

        return unique_senders
    
    def populate_unique_senders(self, senders: set[str]):
        self.selector.populate_senders(sorted(senders, key=lambda x: x.lower()))
    
    def set_status(self, status: str):
        concurrency.main(self.status.configure, text=status)
    
    def setup_imap_and_load_data(self):
        self.set_status("Connecting...")
        try:
            self._setup_imap_client()
        except FileNotFoundError:
            self.set_status("Could not set up IMAP client.")
            return

        self.set_status("Authenticating...")
        self.__client.authenticate()
        self.set_status("Fetching unique senders...")

        senders = self.load_unique_senders()
        concurrency.main(self.populate_unique_senders, senders)
        self.set_status("Done.")
    
    @property
    def busy(self) -> bool:
        return self.selector.busy


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
        if app.busy:
            confirm = tkinter.messagebox.askyesno("Task in Progress", "The app is busy with a task right now! If you quit now, the task could be interrupted leading "
                                                  "to unexpected results.")
            if not confirm:
                return

        global running
        running = False

    deferred = concurrency.DeferredTask(app.setup_imap_and_load_data)
    deferred.run()

    root.protocol("WM_DELETE_WINDOW", end_app)
    while running:
        concurrency.process()
        root.update()
        root.update_idletasks()
    
    root.destroy()
