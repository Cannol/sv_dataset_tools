import tkinter as tkk
import tkinter.ttk as ttk
from tkinter.font import Font

from ui.components.components import Boxes

from logging import Logger
from common.logger import LoggerMeta
from common.json_helper import JsonTransBase


class WindowBase(metaclass=LoggerMeta):

    _L: Logger = None

    _VERSION = '1.0beta'

    # default settings
    Height: int = 500
    Width: int = 400
    Title: str = ''
    StartCenter: bool = True
    ResizeX: bool = False
    ResizeY: bool = False

    def __init__(self, *args, **kwargs):
        tk = kwargs.get('tk')
        if tk:
            self._tk = tk
        else:
            self._tk = tkk.Tk()
        self._config_components()

    def _config_components(self): raise NotImplementedError

    @classmethod
    def GetWindow(cls, window_w, window_h, title, center=True, fix_x=False, fix_y=False):
        tk = tkk.Tk()
        tk.title(title)
        if center:
            screen_w = tk.winfo_screenwidth()
            screen_h = tk.winfo_screenheight()
            l_x = max((screen_w - window_w)//2, 0)
            l_y = max((screen_h - window_h)//2, 0)
        else:
            l_x, l_y = 0, 0
        tk.geometry('%dx%d+%d+%d' % (window_w, window_h, l_x, l_y))
        tk.resizable(fix_x, fix_y)
        return cls(tk)

    @classmethod
    def GetWindowByDefaultConfigs(cls):
        return cls.GetWindow(cls.Width, cls.Height, cls.Title, cls.StartCenter, cls.ResizeX, cls.ResizeY)

    def show(self):
        self._tk.mainloop()


class NetworkConfig(JsonTransBase):
    def __init__(self):
        self.ips = []
        self.users = []
        self.secret_file = ''


class LoginWindow(WindowBase):
    Height: int = 350
    Width: int = 500
    Title = 'Please login your account'
    NetworkFile = ''

    def __init__(self, tk):
        super().__init__(tk=tk)

    def _config_components(self):
        root = self._tk
        self.label_main = tkk.Label(root, height=3, text='Connect to IPIU Cloud Server', font=('Arial', 16, 'bold'))
        self.label_main.pack()

        text_width = 25
        input_width = 20
        self.font = Font(size=15)

        ipp = ['192.168.1.8']
        users = ['abc']

        self.input_ip_port = Boxes.InputSelectBox(root, 'Server IP:', text_width, input_width, self.font, ipp)
        self.input_username = Boxes.InputSelectBox(root, 'User ID:', text_width, input_width, self.font, users)
        self.input_password = Boxes.InputBox(root, 'Password:', text_width, input_width, self.font)
        self.input_password.entry['show'] = '*'
        self.input_code = Boxes.InputBox(root, 'Secret Code:', text_width, input_width, self.font)

        self.frame_btns = ttk.Frame(root, height=20, width=400)
        # style = ttk.Style(self.frame_btns)
        # style.configure('my.TButton', background='#345', foreground='black', font=('Arial', 14))
        self.btn_login = tkk.Button(self.frame_btns, command=self.login, width=80,
                                    text='LOGIN', font=('Arial', 14))

        self.input_ip_port.place_way('pack', pady=10, anchor=tkk.W)
        self.input_username.place_way('pack', pady=10, anchor=tkk.W)
        self.input_password.place_way('pack', pady=10, anchor=tkk.W)
        self.input_code.place_way('pack', pady=10, anchor=tkk.W)

        self.frame_btns.pack(expand=1, anchor=tkk.CENTER)
        self.btn_login.pack(anchor=tkk.CENTER)

    def show(self):
        self._tk.mainloop()

    def login(self):
        user_name = self.input_username.Value
        password = self.input_password.Value
        ip = self.input_ip_port.Value
        # Client.ServerPort = int(port)
        # Client.ServerIP = ip
        # state, msg = Client.Login(user_name, password)
        # if state:
        #     self._tk.destroy()
        # else:
        #     self._L.info(msg)
