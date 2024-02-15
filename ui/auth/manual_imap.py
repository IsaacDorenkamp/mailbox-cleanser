import re
import tkinter
import tkinter.ttk as ttk


HOST_RE = r'^[A-Za-z0-9\-]+?(\.[A-Za-z0-9\-]+?)*$'


class ManualIMAPDialog(tkinter.Toplevel):
    __ok: bool
    __ready: bool
    __host: tkinter.StringVar
    __user: tkinter.StringVar
    __password: tkinter.StringVar
    __ok_btn: ttk.Button

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__ok = False
        self.__ready = False
        self.__setup_ui()
    
    def __setup_ui(self):
        self.resizable(True, False)
        
        container = ttk.Frame(self, padding=7)
        container.grid_columnconfigure(1, weight=1)

        ttk.Label(container, text="Host:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Label(container, text="E-mail:").grid(row=1, column=0, sticky="e", padx=(0, 5))
        ttk.Label(container, text="Password:").grid(row=2, column=0, sticky="e", padx=(0, 5))

        self.__host = tkinter.StringVar(self)
        self.__user = tkinter.StringVar(self)
        self.__password = tkinter.StringVar(self)

        # I would like to not use deprecated behaviors,
        # but trace_add blocks execution on my machine.
        # Yay MacOS!
        self.__host.trace("w", self.__update)
        self.__user.trace("w", self.__update)
        self.__password.trace("w", self.__update)

        host_field = ttk.Entry(container, textvariable=self.__host)
        user_field = ttk.Entry(container, textvariable=self.__user)
        pass_field = ttk.Entry(container, show="*", textvariable=self.__password)

        host_field.grid(row=0, column=1, sticky="nesw")
        user_field.grid(row=1, column=1, sticky="nesw")
        pass_field.grid(row=2, column=1, sticky="nesw")

        button_box = ttk.Frame(container)
        self.__ok_btn = ttk.Button(button_box, text="OK", command=self.success, state=tkinter.DISABLED)

        host_field.bind("<Return>", self.__try_success)
        user_field.bind("<Return>", self.__try_success)
        pass_field.bind("<Return>", self.__try_success)

        self.__ok_btn.pack(side=tkinter.RIGHT, padx=(5, 0))
        ttk.Button(button_box, text="Cancel", command=self.failure).pack(side=tkinter.RIGHT)

        button_box.grid(row=3, column=1, sticky="nesw")
        container.pack(fill=tkinter.BOTH, expand=tkinter.YES)

        self.__ready = True

    def success(self):
        self.__ok = True
        self.destroy()
    
    def failure(self):
        self.destroy()

    def __try_success(self, _):
        self.__ok_btn.invoke()

    def __update(self, *_):
        if not self.__ready:
            return

        valid_hostname = re.match(HOST_RE, self.host) is not None
        valid_user = bool(self.user) and self.user.strip() == self.user
        valid_password = bool(self.password)

        if valid_hostname and valid_user and valid_password:
            self.__ok_btn.configure(state=tkinter.NORMAL)
        else:
            self.__ok_btn.configure(state=tkinter.DISABLED)
    
    @property
    def host(self) -> str:
        return self.__host.get()
    
    @property
    def user(self) -> str:
        return self.__user.get()
    
    @property
    def password(self) -> str:
        return self.__password.get()
    
    @property
    def ok(self) -> bool:
        return self.__ok
