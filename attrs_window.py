import tkinter as tkk
from tkinter.font import Font
import threading


def _empty(): pass


class Window(threading.Thread):

    def __init__(self):
        super().__init__()
        self.values = []
        self.ATTRS = []
        self.bind_func = _empty

    def construct(self, select_list):
        self.root = tkk.Tk()
        self.root.title('Sequence Attributes')
        self.boxes = []

        for item in select_list:
            v = tkk.IntVar()
            b = tkk.Checkbutton(self.root, text=item, variable=v,
                                onvalue=1, offvalue=0, font=Font(family='fangsong ti', size=12))
            if not item.startswith('*'):
                b['state'] = tkk.DISABLED
            self.values.append(v)
            b.pack(anchor=tkk.W)
            self.boxes.append(b)
        self.btn_update = tkk.Button(self.root, text='Update Auto-Attributes', command=self.func_update)
        self.btn_update.pack(anchor=tkk.W)

    def func_update(self):
        self.bind_func()

    def set_attrs(self, values):
        for btn, value in zip(self.boxes, values):
            if value:
                btn.select()
            else:
                btn.deselect()

    def get_attrs(self):
        attrs = []
        for btn in self.values:
            if btn.get() == 1:
                attrs.append(True)
            else:
                attrs.append(False)
        return attrs

    def run(self):
        self.construct(self.ATTRS)
        self.root.mainloop()


# w = Window()
# print('start')
# w.start()
#
# while w.is_alive():
#     w.join(1)
#     print(w.get_attrs())
# print('end!')
