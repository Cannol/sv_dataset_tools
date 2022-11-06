from logging import Logger
import tkinter as tkk
from common.logger import LoggerMeta
from tkinter import filedialog


class TopBar(tkk.Frame, metaclass=LoggerMeta):
    _L: Logger = None

    def __init__(self, master, cnf={}, **kw):
        if kw.get('bg') is None:
            kw['bg'] = 'Grey'
        super().__init__(master, cnf, **kw)
        bg = kw['bg']

        self._btn_open = tkk.Button(self, bg=bg, command=self._open, width=16, text='Open WorkSpace', relief='flat')
        self._btn_conn = tkk.Button(self, bg=bg, command=self._connection, width=20, text='Server: Offline',
                                    relief='flat')
        self._btn_update = tkk.Button(self, bg=bg, command=self._update, width=10, text='Update', relief='flat')
        self._btn_settings = tkk.Button(self, bg=bg, command=self._preference, width=15, text='Preference',
                                        relief='flat')
        self._construct()

    def _construct(self):
        self._btn_open.pack(side=tkk.LEFT, fill=tkk.Y)
        self._btn_update.pack(side=tkk.LEFT, fill=tkk.Y)
        self._btn_conn.pack(side=tkk.RIGHT, fill=tkk.Y)
        self._btn_settings.pack(side=tkk.RIGHT, fill=tkk.Y)

    def _open(self):
        folder = filedialog.askdirectory()
        print(folder)

    def _update(self):
        pass

    def _connection(self):
        from ui.windows.LoginWindow import LoginWindow
        l = LoginWindow.GetWindowByDefaultConfigs()

    def _preference(self):
        pass