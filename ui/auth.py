import enum
import functools
import threading
import tkinter

from PIL import Image, ImageTk

from ui import concurrency
import context
import credentials
from api import imap


class AuthenticationType(enum.StrEnum):
    GOOGLE = "google"


class AuthenticationOptions(tkinter.Toplevel):
    __icons: dict[str, ImageTk.PhotoImage]
    __client: imap.GmailIMAP  # TODO: Abstract this!
    __buttons: list[tkinter.Button]
    __alive: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.__buttons.append(tkinter.Button(
            self, text=" Sign in with Google", image=self.__icons["google"], compound=tkinter.LEFT, font=("Roboto", 16),
            command=functools.partial(self.authenticate, AuthenticationType.GOOGLE)
        ))

        for button in self.__buttons:
            button.pack(fill=tkinter.BOTH, expand=tkinter.YES, padx=10, pady=10, ipady=10, ipadx=10)

        self.resizable(False, False)

    def authenticate(self, auth_type: AuthenticationType):
        self.set_enabled(False)

        auth_task = None

        if auth_type == AuthenticationType.GOOGLE:
            auth_task = concurrency.DeferredTask(self.__google_auth)

        if auth_task:
            auth_task.then(self.__on_authenticate)
            auth_task.run()
        else:
            self.set_enabled(True)

    def __on_authenticate(self, success: bool):
        if not self.alive:
            return

        if success:
            concurrency.main(self.destroy)
        else:
            concurrency.main(self.set_enabled, True)
    
    def set_enabled(self, enabled: bool):
        for button in self.__buttons:
            button.configure(state=tkinter.NORMAL if enabled else tkinter.DISABLED)

    def __google_auth(self) -> bool:
        try:
            google_creds = credentials.get_credentials_flow()
        except TimeoutError:
            return False

        if google_creds:
            username = imap.get_user_email(google_creds)
            self.__client = imap.GmailIMAP(username, google_creds.token, debug=context.is_debug)
            credentials.save_credentials(google_creds)
            return True
        
        return False
    
    def get_client(self) -> imap.GmailIMAP | None:
        return self.__client
    
    def __close_win(self):
        self.__alive = False
        self.destroy()
    
    @property
    def alive(self) -> bool:
        return self.__alive
    

