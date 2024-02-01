import tkinter
import typing


# Took inspiration from https://stackoverflow.com/questions/68036371/tkinter-canvas-scroll-slow-rendering
# in order to provide comfortable scrolling behavior.
class Checklist(tkinter.Frame):
    _items: list[tkinter.Checkbutton]
    __enabled: bool

    _scroll_window: tkinter.Text
    _vscroll: tkinter.Scrollbar

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._items = []
        self.__enabled = True

        self.__setup_ui()
    
    def __setup_ui(self):
        self._scroll_window = tkinter.Text(self, state="disabled", cursor="arrow")
        self._vscroll = tkinter.Scrollbar(self, orient=tkinter.VERTICAL)

        self._scroll_window.bind_all("<MouseWheel>", self.handle_mousewheel)
        self._scroll_window.config(yscrollcommand=self._vscroll.set)

        self._vscroll.config(command=self._scroll_window.yview)

        self._scroll_window.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=tkinter.YES)
        self._vscroll.pack(side=tkinter.RIGHT, fill=tkinter.Y)
    
    def handle_mousewheel(self, event):
        self._scroll_window.yview_scroll(int(-event.delta / abs(event.delta)), "units")
    
    def append(self, item: str):
        is_checked = tkinter.BooleanVar()
        check = tkinter.Checkbutton(self._scroll_window, text=item, bg=self._scroll_window.cget("bg"), variable=is_checked)
        
        self._scroll_window.window_create("end", window=check)

        self._scroll_window.config(state="normal")
        self._scroll_window.insert("end", "\n")
        self._scroll_window.config(state="disabled")
        self._items.append((check, is_checked))
    
    def remove(self, items: typing.Container[str]):
        to_destroy = [item[0] for item in self._items if item[0].cget("text") in items]
        self._items = [item for item in self._items if item[0].cget("text") not in items]

        self._scroll_window.configure(state="normal")
        for check in to_destroy:
            entry_index = self._scroll_window.index(str(check))  # the str() cast is ugly, but it gives us tkinter's name for the checkbox
            line = entry_index.split(".")[0]
            end_index = "%d.0" % (int(line) + 1)
            self._scroll_window.delete(entry_index, end_index)
        self._scroll_window.configure(state="disabled")
    
    def get_checked(self) -> set[str]:
        return {button.cget("text") for button, is_checked in self._items if is_checked.get()}
    
    def get_items(self) -> set[str]:
        return {button.cget("text") for button, _ in self._items}
    
    def set_enabled(self, enabled: bool):
        self.__enabled = enabled
        for check in map(lambda x: x[0], self._items):
            check.configure(state='normal' if enabled else 'disabled')

    @property
    def enabled(self) -> bool:
        return self.__enabled
