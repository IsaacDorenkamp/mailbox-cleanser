import enum
import functools
import tkinter
import tkinter.ttk as ttk
import tkinter.messagebox
import typing
import warnings

from PIL import Image, ImageTk

import auth.google
from api import imap, service_factory
import context
from ui import concurrency

from .manual_imap import ManualIMAPDialog


class AuthenticationType(enum.StrEnum):
    GOOGLE = "google"
    MANUAL = "manual"


class AuthenticationOptions(tkinter.Toplevel):
    __wait_window: typing.Callable[[tkinter.Toplevel], None]

    __icons: dict[str, ImageTk.PhotoImage]
    __client: imap.GenericIMAP
    __buttons: list[ttk.Button]
    __alive: bool

    def __init__(self, wait_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__wait_window = wait_window
        self.__icons = {}
        self.__client = None
        self.__alive = True
        self.__setup_ui()

    def __setup_ui(self):
        self.title("Sign In")
        self.protocol("WM_DELETE_WINDOW", self.__close_win)

        google_icon = Image.open(context.get_resource("google_icon.png"))
        google_icon = google_icon.resize((32, 32))

        self.__icons["google"] = ImageTk.PhotoImage(google_icon)
        self.__buttons = []
        self.__buttons.append(ttk.Button(
            self, text=" Sign in with Google", image=self.__icons["google"], compound=tkinter.LEFT, style="Large.TButton",
            command=functools.partial(self.authenticate, AuthenticationType.GOOGLE)
        ))

        self.__buttons.append(ttk.Button(
            self, text="Manual IMAP Configuration", command=functools.partial(self.authenticate, AuthenticationType.MANUAL),
            style="Large.TButton"
        ))

        for index, button in enumerate(self.__buttons):
            button.pack(fill=tkinter.BOTH, expand=tkinter.YES, padx=10, pady=(10, 10 if index > 0 else 0), ipady=10, ipadx=10)

        self.resizable(False, False)

    def authenticate(self, auth_type: AuthenticationType):
        self.set_enabled(False)

        auth_task = None

        if auth_type == AuthenticationType.GOOGLE:
            auth_task = concurrency.DeferredTask(self.__google_auth)
        elif auth_type == AuthenticationType.MANUAL:
            auth_task = concurrency.DeferredTask(functools.partial(concurrency.main, self.__manual_auth))

        if auth_task:
            auth_task.then(self.__on_authenticate)
            auth_task.run()
        else:
            self.set_enabled(True)

    def __on_authenticate(self, success: bool):
        if not self.alive:
            return

        if success:
            service_factory.save_imap_service(self.__client)
            concurrency.main(self.destroy)
        else:
            concurrency.main(self.set_enabled, True)
    
    def set_enabled(self, enabled: bool):
        for button in self.__buttons:
            button.configure(state=tkinter.NORMAL if enabled else tkinter.DISABLED)

    def __google_auth(self) -> bool:
        try:
            google_creds = auth.google.run_authorization_flow()
        except auth.google.AuthorizationError as err:
            concurrency.main(tkinter.messagebox.showerror, str(err))
            return False
        except Warning:
            concurrency.main(tkinter.messagebox.showerror, "Insufficient Permissions", "You have not granted sufficient permissions for Mailbox Cleanser to work."
                             " Please ensure you grant permissions to view, modify, and delete mail in order to allow Mailbox Cleanser to work properly.")
            return False

        if google_creds:
            concurrency.main(self.master.attributes, "-topmost", True)
            concurrency.main(self.master.attributes, "-topmost", False)
            username = imap.GmailIMAP.get_user_email(google_creds)
            self.__client = imap.GmailIMAP(username, google_creds, debug=context.is_debug)
            return True
        
        return False
    
    def __manual_auth(self) -> bool:
        dialog = ManualIMAPDialog()
        dialog.grab_set()
        self.__wait_window(dialog)

        if dialog.ok:
            self.__client = imap.ManualIMAP(dialog.user, dialog.password, dialog.host)
            return True
        else:
            return False
    
    def get_client(self) -> imap.GenericIMAP | None:
        return self.__client
    
    def __close_win(self):
        self.__alive = False
        self.destroy()
    
    @property
    def alive(self) -> bool:
        return self.__alive
