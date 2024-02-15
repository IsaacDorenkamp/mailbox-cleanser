import configparser
import functools
import imaplib
import os
import sys
import tkinter
import tkinter.ttk as ttk
import tkinter.messagebox
import typing

from api import CleanserService, GenericIMAP, service_factory
from . import concurrency
import config
import persist
from .auth import AuthenticationOptions
from .selector import Selector
from .settings import SettingsDialog


class MenuActions:
    class File:
        CACHE_CLEAR = "Clear Cached Data"
        SIGN_IN = "Log into account..."
        SIGN_OUT = "Log Out"
        PREFERENCES = "Preferences"
        EXIT = "Exit"


    NONTRIVIAL_ACTIONS = [
        ("file", File.CACHE_CLEAR),
        ("file", File.SIGN_IN),
        ("file", File.SIGN_OUT),
        ("file", File.PREFERENCES)
    ]


class MainApplication(ttk.Frame):
    selector: Selector
    status: ttk.Label

    __settings: dict[str, str | None]

    __client: GenericIMAP
    __service: CleanserService

    __menubar: tkinter.Menu
    __menus: dict[str, tkinter.Menu]

    __debug: bool
    __running: tkinter.BooleanVar

    def __init__(self, parent, settings: dict[str, str | None], debug: bool = False):
        super().__init__(parent)
        self.__settings = settings
        self.__running = tkinter.BooleanVar(value=True)
        self.__menus = {}
        self.__debug = debug
        self.__setup_ui()
    
    def __setup_ui(self):
        container = ttk.Frame(self)

        self.status = ttk.Label(container, text="Setting up...", anchor='w', style="Padded.TLabel")
        self.status.pack(side=tkinter.BOTTOM, fill=tkinter.X, padx=5)

        self.selector = Selector(container)
        self.selector.bind("<<Status>>", self.on_selector_status)
        self.selector.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=tkinter.YES)

        container.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.__item_states = {}
        self.__menubar = menu_bar = tkinter.Menu(self.master)
        file_menu = tkinter.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label=MenuActions.File.CACHE_CLEAR, command=functools.partial(
            self.confirm,
            "Confirm Cache Clear",
            "This will clear all cache data. This does not include authorization information, but does include the cached lists of senders. Proceed?",
            self.cache_clear
        ))
        file_menu.add_command(label=MenuActions.File.SIGN_IN, command=self.sign_in, state=tkinter.DISABLED)
        file_menu.add_command(label=MenuActions.File.SIGN_OUT, command=self.sign_out, state=tkinter.DISABLED)
        file_menu.add_separator()
        file_menu.add_command(label=MenuActions.File.PREFERENCES, command=self.show_preferences)
        file_menu.add_separator()
        file_menu.add_command(label=MenuActions.File.EXIT, command=self.try_quit)

        self.__menus["file"] = file_menu

        menu_bar.add_cascade(label="File", menu=file_menu)
        self.master.config(menu=menu_bar)

    def sign_in(self):
        auth_options = AuthenticationOptions(lambda window: concurrency.wait_window(window, self.master, self.running), self.master)

        self.__menubar.entryconfig("File", state=tkinter.DISABLED)

        auth_options.transient(self)
        auth_options.wait_visibility()
        auth_options.grab_set()

        concurrency.wait_window(auth_options, self.master, self.running)

        client = auth_options.get_client()
        if client:
            self.set_client(client)
            self.selector.set_enabled(True)
            initialize_task = concurrency.DeferredTask(self.initialize)
            initialize_task.then(functools.partial(concurrency.main, self.__menubar.entryconfig, "File", state=tkinter.NORMAL))
            initialize_task.run()

    def sign_out(self):
        try:
            os.unlink(os.path.join(config.USER_DATA_DIR, "service_config.json"))
        except FileNotFoundError:
            pass

        if self.__client:
            try:
                self.__client.logout()
            except imaplib.IMAP4.abort:
                # socket EOF
                pass

        self.__client = None
        self.__service = None
        self.selector.service = None

        self.__menus["file"].entryconfig(MenuActions.File.SIGN_IN, state=tkinter.NORMAL)
        self.__menus["file"].entryconfig(MenuActions.File.SIGN_OUT, state=tkinter.DISABLED)
        self.selector.clear_senders()
        self.selector.set_enabled(False)
    
    def show_preferences(self):
        dialog = SettingsDialog(self.__settings, self.master)

        dialog.transient(self)
        dialog.wait_visibility()
        dialog.grab_set()

        concurrency.wait_window(dialog, self.master, self.__running)

        new_settings = dialog.get_new_settings()
        if new_settings:
            self.__service.junk_folder = new_settings["junk_folder"]
            self.__settings = new_settings

            writer = configparser.ConfigParser()
            writer[configparser.DEFAULTSECT] = new_settings
            
            try:
                with open(os.path.join(config.USER_CONFIG_DIR, "settings.ini"), "w") as fp:
                    writer.write(fp)
            except IOError:
                tkinter.messagebox.showerror("Could not save preferences.")

    def set_client(self, client: GenericIMAP):
        self.__client = client
        self.__service = CleanserService(self.__client, junk_folder=self.__settings.get("junk_folder"))
        self.selector.service = self.__service
    
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
        self.selector.clear_senders()
        self.selector.populate_senders(sorted(senders, key=lambda x: x.lower()))
    
    def set_status(self, status: str):
        concurrency.main(self.status.configure, text=status)
    
    def setup_imap_and_load_data(self):
        self.set_status("Connecting...")
        
        try:
            imap_service = service_factory.create_service(debug=self.__debug)
        except GenericIMAP.OperationError as err:
            self.set_status("Failed to connect to IMAP server.")
            concurrency.main(self.__menus["file"].entryconfigure, MenuActions.File.SIGN_IN, state=tkinter.NORMAL)
            concurrency.main(tkinter.messagebox.showerror, "Setup Error", str(err))
            return
        
        if not imap_service:
            self.set_status("Not logged in.")
            concurrency.main(self.__menus["file"].entryconfigure, MenuActions.File.SIGN_IN, state=tkinter.NORMAL)
            concurrency.main(self.sign_in)
            return
        
        # ensure persisted data is updated, such as in the case that
        # Google credentials were refreshed during the construction
        service_factory.save_imap_service(imap_service)
        self.set_client(imap_service)
        
        self.initialize()
        concurrency.main(self.__menus["file"].entryconfigure, MenuActions.File.SIGN_OUT, state=tkinter.NORMAL)

    def initialize(self):
        self.set_status("Authenticating...")
        self.__client.authenticate()
        self.set_status("Fetching unique senders...")
        self.load_and_populate_unique_senders()
        self.set_status("Done.")

        concurrency.main(self.__menus["file"].entryconfigure, MenuActions.File.SIGN_IN, state=tkinter.DISABLED)
        concurrency.main(self.__menus["file"].entryconfigure, MenuActions.File.SIGN_OUT, state=tkinter.NORMAL)
    
    def load_and_populate_unique_senders(self):
        senders = self.load_unique_senders()
        concurrency.main(self.populate_unique_senders, senders)

    def cache_clear(self):
        persist.clear_all()

        if self.__service:
            self.disable_actions()

            self.set_status("Fetching unique senders...")
            deferred_cache = concurrency.DeferredTask(self.load_and_populate_unique_senders)
            deferred_cache.then(functools.partial(self.set_status, "Done."))
            deferred_cache.then(functools.partial(concurrency.main, self.enable_actions))
            deferred_cache.run()
    
    def disable_actions(self):
        for menu_name, action_name in MenuActions.NONTRIVIAL_ACTIONS:
            self.__item_states[menu_name, action_name] = self.__menus[menu_name].entrycget(action_name, "state")
            self.__menus[menu_name].entryconfigure(action_name, state=tkinter.DISABLED)
        
        self.selector.set_enabled(False)

    def enable_actions(self):
        for menu_name, action_name in MenuActions.NONTRIVIAL_ACTIONS:
            self.__menus[menu_name].entryconfigure(action_name, state=self.__item_states.get((menu_name, action_name), tkinter.NORMAL))
        
        self.selector.set_enabled(True)
    
    def confirm(self, title: str, message: str, action: typing.Callable[[], typing.Any]):
        response = tkinter.messagebox.askyesno(title, message)
        if response:
            action()
    
    @property
    def busy(self) -> bool:
        return self.selector.busy
    
    def try_quit(self):
        if self.busy:
            confirm = tkinter.messagebox.askyesno("Task in Progress", "The app is busy with a task right now! If you quit now, the task could be interrupted leading "
                                                  "to unexpected results.")
            if not confirm:
                return
        
        self.__running.set(False)
    
    @property
    def running(self) -> tkinter.BooleanVar:
        return self.__running


def _patch_nones(settings: dict[str, str]) -> dict[str, str | None]:
    output = {}
    for key, value in settings.items():
        output[key] = None if value == "" else value
    
    return output


def main():
    import tkinter.ttk as ttk
    import ttkthemes

    parser = configparser.ConfigParser()
    successful = parser.read(os.path.join(config.USER_CONFIG_DIR, "settings.ini"))
    if len(successful) < 0:
        settings = config.SETTINGS_DEFAULTS.copy()
    else:
        settings = config.SETTINGS_DEFAULTS | dict(parser.items(configparser.DEFAULTSECT))
    
    settings = _patch_nones(settings)

    root = ttkthemes.ThemedTk(theme="scidgreen")
    root.wm_title("Mailbox Cleanser")
    root.geometry("400x450")

    style = ttk.Style(root)
    style.configure("Padded.TLabel", padding=5)
    style.configure("TButton", font=("Roboto", 10))
    style.configure("Large.TButton", font=("Roboto", 14))

    debug_mode = "--debug" in sys.argv

    app = MainApplication(root, settings, debug=debug_mode)
    
    app.pack(fill=tkinter.BOTH, expand=tkinter.YES)
    
    # if we don't do this, the window won't populate until it is focused.
    root.wm_withdraw()
    root.update()
    root.after(1, root.deiconify)

    deferred = concurrency.DeferredTask(app.setup_imap_and_load_data)
    deferred.run()

    root.protocol("WM_DELETE_WINDOW", app.try_quit)
    while app.running.get():
        concurrency.update_app(root)
    
    root.destroy()
