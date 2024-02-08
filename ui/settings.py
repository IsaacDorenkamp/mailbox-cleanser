import tkinter
import tkinter.messagebox


class SettingsDialog(tkinter.Toplevel):
    __use_junk_folder: tkinter.BooleanVar
    __junk_folder: tkinter.StringVar
    __junk_folder_field: tkinter.Entry

    __settings: dict[str, str] | None

    def __init__(self, settings, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__settings = None
        self.__setup_ui(settings)
    
    def __setup_ui(self, settings: dict[str, str]):
        self.configure(padx=5, pady=5)

        self.__use_junk_folder = tkinter.BooleanVar(value=settings.get("junk_folder") is not None)
        self.__junk_folder = tkinter.StringVar(value=settings.get("junk_folder"))

        self.__use_junk_folder.trace("w", self.__update)

        tkinter.Label(self, text="Use Junk Folder?").grid(row=0, column=0, sticky="e", padx=(0, 5))
        tkinter.Label(self, text="Junk Folder").grid(row=1, column=0, sticky="e", padx=(0, 5))

        junk_folder_check = tkinter.Checkbutton(self, variable=self.__use_junk_folder)
        junk_folder_check.grid(row=0, column=1, sticky="w")

        self.__junk_folder_field = junk_folder = tkinter.Entry(
            self, textvariable=self.__junk_folder, state=tkinter.NORMAL if self.__use_junk_folder.get() else tkinter.DISABLED
        )
        junk_folder.grid(row=1, column=1, sticky="nesw")

        button_box = tkinter.Frame(self)
        ok = tkinter.Button(button_box, text="OK", command=self.success)
        cancel = tkinter.Button(button_box, text="Cancel", command=self.destroy)

        ok.pack(side=tkinter.RIGHT, padx=(5, 0))
        cancel.pack(side=tkinter.RIGHT)

        button_box.grid(row=2, column=0, columnspan=2, sticky="nesw", pady=(5, 0))

        self.resizable(True, False)
    
    def __update(self, *_):
        self.__junk_folder_field.configure(state=tkinter.NORMAL if self.__use_junk_folder.get() else tkinter.DISABLED)
    
    def success(self):
        error = None
        junk_folder = None if not self.__use_junk_folder.get() else self.__junk_folder.get()
        if junk_folder:
            valid_junk_folder = junk_folder.strip() == junk_folder
            if not valid_junk_folder:
                error = "Junk folder name must not begin or end with whitespace."
        
        if error:
            tkinter.messagebox.showerror(error)
        else:
            self.__settings = {
                "junk_folder": junk_folder or ""
            }
            self.destroy()
    
    def get_new_settings(self) -> dict[str, str] | None:
        return self.__settings
