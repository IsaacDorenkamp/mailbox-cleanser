import tkinter


class Checklist(tkinter.Frame):
    _items: list[tkinter.Checkbutton]

    _canvas: tkinter.Canvas
    _vscroll: tkinter.Scrollbar

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._items = []

        self.__setup_ui()
    
    def __setup_ui(self):
        self._canvas = tkinter.Canvas(self)
        self._vscroll = tkinter.Scrollbar(self, orient=tkinter.VERTICAL)

        self._canvas.config(yscrollcommand=self._vscroll.set)
        self._canvas.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._vscroll.config(command=self._canvas.yview)

        self._canvas.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self._vscroll.pack(side=tkinter.RIGHT, fill=tkinter.Y)
    
    def insert(self, index: int | str, item: str):
        if index == tkinter.END:
            index = len(self._items)

        check = tkinter.Checkbutton(self._canvas, text=item)
        if index > len(self._items) or index < 0:
            raise IndexError("Index must be between 0 and %d, inclusive." % len(self._items))
        
        self._items.insert(index, check)
        check.grid(column=0, row=index, sticky='nws')
