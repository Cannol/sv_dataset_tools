from logging import Logger
import tkinter.ttk as ttk  # 可视化界面主要包
import tkinter as tkk
from collections import OrderedDict as Dict, Sized, Iterable
from math import ceil, modf

from PIL import Image, ImageTk

from common.logger import LoggerMeta
from .plugs import MemoryValidateTag


def Empty_Func(*args, **kw):
    pass


class Boxes:
    class BoxBase(ttk.Frame):
        def __init__(self, master, text_ask, text_width, font, **kwargs):
            super().__init__(master, **kwargs)
            self.label = ttk.Label(self, width=text_width, text=text_ask, anchor=tkk.E,
                                   font=font, justify=tkk.RIGHT)
            self.entry: tkk.Entry = None
            self.other: tkk.Entry = None

        def place_way(self, place_type='place', *args, **kwargs):

            self.label.pack(side=tkk.LEFT)
            self.entry.pack(side=tkk.LEFT)
            if self.other:
                self.other.pack(side=tkk.LEFT)

            if place_type == 'pack':
                self.pack(*args, **kwargs)
            elif place_type == 'grid':
                self.pack(*args, **kwargs)
            elif place_type == 'place':
                self.place(*args, **kwargs)
            else:
                assert False, 'Error place type!'

        def other_widget(self, widget):
            self.other = widget

        @property
        def Value(self):
            return self.entry.get()

    class DisplayBox(BoxBase):
        def __init__(self, master, text_ask, text_width, text_ans, ans_width, font, **kwargs):
            super().__init__(master, text_ask, text_width, font, **kwargs)

            self.entry = ttk.Label(self, width=ans_width, text=text_ans, font=font, justify=tkk.LEFT)

        @property
        def Value(self):
            return self.entry['text']

        @Value.setter
        def Value(self, value):
            self.entry['text'] = value

    class InputBox(BoxBase):
        def __init__(self, master, text_ask, text_width, input_width, font, **kwargs):
            super().__init__(master, text_ask, text_width, font, **kwargs)

            self.entry = ttk.Entry(self, width=input_width, font=font, justify=tkk.LEFT)

    class InputSelectBox(BoxBase):
        def __init__(self, master, text_ask, text_width, input_width, font, select_list, **kwargs):
            super().__init__(master, text_ask, text_width, font, **kwargs)

            # label + value
            self.entry = ttk.Combobox(self, width=input_width, font=font, justify=tkk.LEFT)
            self.entry['value'] = tuple(select_list)

        def set_values(self, values):
            self.entry['value'] = values

        @property
        def Value(self):
            return self.entry.get()

        @Value.setter
        def Value(self, value):
            return self.entry.set(value=value)

        @property
        def Index(self):
            return self.entry.current()

        @Index.setter
        def Index(self, index):
            self.entry.current(newindex=index)

        def ReadOnly(self):
            self.entry['state'] = "readonly"

        def Normal(self):
            self.entry['state'] = "normal"

        def Disabled(self):
            self.entry['state'] = "disabled"


class ScaleController(tkk.Frame, metaclass=LoggerMeta):
    _L: Logger = None

    def __init__(self, master, cnf={}, **kw):
        if kw.get('bg') is None:
            kw['bg'] = 'Grey'
        super().__init__(master, cnf, **kw)
        root = self  # get the parent container
        bg = kw['bg']

        # key values
        self._rate = 1.0
        self._max_rate = 5.0
        self._min_rate = 0.6
        self._step = 0.05

        self.RateChangeHook = lambda x: print('Please bind me with a method! Get Rate {}'.format(x))

        # widgets
        self.rate_var = tkk.StringVar()
        self.rate_var.set('100 %')
        self.scale_var = tkk.DoubleVar()
        self.input_scale = tkk.Entry(root, bg=bg, width=5, bd=0, justify=tkk.RIGHT,
                                     textvariable=self.rate_var)
        self.scale = tkk.Scale(root, from_=self._min_rate, to=self._max_rate, resolution=0.01,
                               variable=self.scale_var,
                               command=self._get_value,
                               orient=tkk.HORIZONTAL, showvalue=False)
        self.button_add = tkk.Button(root, bg=bg,
                                     command=self.zoom_in,
                                     text='+', relief='flat')
        self.button_de = tkk.Button(root, bg=bg,
                                    command=self.zoom_out,
                                    text='-', relief='flat')

        # make grids
        self.input_scale.grid(row=0, column=0)
        self.button_add.grid(row=0, column=3)
        self.button_de.grid(row=0, column=1)
        self.scale.grid(row=0, column=2)

        MemoryValidateTag.Create(self, 'ImageScale')
        MemoryValidateTag.RegisterWidgetFuncs(self.input_scale, self.change_scale, 'ImageScale')

    def change_scale(self, value):
        if value[-1] == '%':
            t = float(value[:-1]) / 100
        else:
            t = float(value)
        self.RateVar = max(min(t, self._max_rate), self._min_rate)

    def _get_value(self, event):
        self.RateVar = self.scale.get()

    @property
    def RateVar(self):
        return self._rate

    @RateVar.setter
    def RateVar(self, rate: float):
        if self._rate == rate:
            return
        self._rate = rate
        self.rate_var.set('%d%%' % int(rate * 100))
        self.scale.set(self._rate)
        self.RateChangeHook(rate)

    # 放大
    def zoom_in(self):
        self.RateVar = self.RateVar + self._step

    # 缩小
    def zoom_out(self):
        self.RateVar = self.RateVar - self._step


class ProgressBar(tkk.Canvas, metaclass=LoggerMeta):
    _L: Logger = None

    def __init__(self, name, master, height: int, cnf={}, **kw):
        kw['height'] = height
        super().__init__(master, cnf, **kw)
        self._hook_click = Empty_Func
        self._click = False
        self.bind('<Configure>', lambda x: self.initialize())
        self._width = 0
        self._height = height + 3
        self._bar = self.create_rectangle(0, 0, 1, self._height, fill='Red')
        self._indicator = self.create_rectangle(0, 0, 0, 0, fill='white', width=0)
        self._percentage = 0.0
        self._select_percentage = 0.0
        self._mouse_moving_hook = Empty_Func
        self._mouse_leave_hook = Empty_Func
        self._mini_width = 1
        self._numbers_of_block = 0

    def set_mini_width(self, numbers: int):
        self._numbers_of_block = numbers
        self._mini_width = self._width / self._numbers_of_block

    def initialize(self):
        self.update()
        self._L.debug('width = {}'.format(self.winfo_width()))
        self._width = self.winfo_width()
        if self._numbers_of_block > 0:
            self._mini_width = self._width / self._numbers_of_block
        self.coords(self._bar, 0, 0, self._width * self._percentage, self._height)

    def _on_mouse_moving(self, event):
        self._select_percentage = self._mouse_moving_hook(event.x / self._width)
        t = self._select_percentage * self._width
        self.coords(self._indicator, t - self._mini_width, 0, t, self._height)

    def _on_mouse_leave(self, event):
        self.coords(self._indicator, 0, 0, 0, 0)
        self._mouse_leave_hook()

    @property
    def Percentage(self):
        return self._percentage

    @Percentage.setter
    def Percentage(self, value: float):
        self._percentage = max(min(value, 1), 0)
        self.coords(self._bar, 0, 0, self._width * self._percentage, self._height)

    @property
    def HookClick(self):
        return self._hook_click

    @HookClick.setter
    def HookClick(self, func=Empty_Func):
        self._hook_click = func
        if self._hook_click is Empty_Func:
            self._L.debug('Hook Click is canceled.')

    @property
    def HookSelecting(self):
        return self._hook_click

    @HookSelecting.setter
    def HookSelecting(self, func=Empty_Func):
        self._mouse_moving_hook = func
        if self._mouse_moving_hook is Empty_Func:
            self._L.debug('Hook Selecting is canceled.')

    @property
    def HookLeaving(self):
        return self._mouse_leave_hook

    @HookLeaving.setter
    def HookLeaving(self, func=Empty_Func):
        self._mouse_leave_hook = func
        if self._mouse_leave_hook is Empty_Func:
            self._L.debug('Hook Leaving is canceled.')

    @property
    def Click(self):
        return self._click

    @Click.setter
    def Click(self, value: bool):
        if value:
            self.bind('<ButtonRelease-1>', self.click_event)
            self.bind('<Motion>', self._on_mouse_moving)
            self.bind('<Leave>', self._on_mouse_leave)
        else:
            self.unbind('<ButtonRelease-1>')
            self.unbind('<Motion>')
            self.unbind('<Leave>')
        self._click = value

    def click_event(self, event):
        self.update()
        self._percentage = event.x / self._width
        self.coords(self._bar, 0, 0, self._width * self._percentage, self._height)
        self._hook_click(self._percentage)


class DProgressBar(ProgressBar):

    def __init__(self, name, master, height: int, cnf={}, **kw):
        super().__init__(name, master, height, cnf, **kw)
        self._bar_bottom = self.create_rectangle(0, 0, 30, 30, fill='RosyBrown', width=0)
        self.tag_lower(self._bar_bottom)
        self._percentage_bottom = 0.6

    def initialize(self):
        super().initialize()
        self.coords(self._bar_bottom, 0, 0, self._width * self._percentage_bottom, self._height)

    @property
    def PercentageBottom(self):
        return self._percentage_bottom

    @PercentageBottom.setter
    def PercentageBottom(self, value: float):
        self._percentage_bottom = max(min(value, 1), 0)
        self.coords(self._bar_bottom, 0, 0, self._width * self._percentage_bottom, self._height)


class PlayController(tkk.Frame, metaclass=LoggerMeta):
    """
    a class that produce a media controller to go to anywhere you want
        - need a parent container to bind with
        - the size of the inner component is relied on the parent container
    """

    _L: Logger = None

    MIN_WIDTH = 800
    BTN_WIDTH = 10
    MAX_FPS = 60

    def __init__(self, master, canvas_workspace, cnf={}, **kw):
        if kw.get('bg') is None:
            kw['bg'] = 'Grey'
        super().__init__(master, cnf, **kw)
        root = self  # get the parent container
        MemoryValidateTag.Create(root)

        self.IntType = {'F': lambda x: int(x),
                        'f': lambda x: int(x),
                        's': lambda x: round(x * self._fps),
                        'S': lambda x: round(x * self._fps),
                        'M': lambda x: round(x * 60 * self._fps),
                        'm': lambda x: round(x * 60 * self._fps)}

        self.IntTypeInverse = {'F': lambda x: '%d' % x,
                               'f': lambda x: '%d' % x,
                               's': lambda x: '%.3f' % (x / self._fps),
                               'S': lambda x: '%.3f' % (x / self._fps),
                               'M': lambda x: '%.3f' % (x / 60 / self._fps),
                               'm': lambda x: '%.3f' % (x / 60 / self._fps)}

        # data holder
        self.data_frames = None
        self.tk_image = None

        # set vars
        self._total_frames = 0
        self._fps = 10
        self._interval = 1
        self._current_frames = 0
        self._current_time = 0
        self._spf = 1000 // self._fps
        self._total_time = self._total_frames / self._fps
        self._max_interval = self._total_frames // 4

        self._temp_str = ''
        self._focus_on_entry = False

        self._scale = 1.0

        bg = kw['bg']
        self.progress_bar = DProgressBar('play', root, bg='Grey', height=10, bd=0)
        self.progress_bar.Click = False
        self.progress_bar.set_mini_width(1)
        self.label_frame_number = tkk.Label(root, bg=bg, text='Frame: ', justify=tkk.RIGHT)
        self.label_time = tkk.Label(root, bg=bg, text='Time: ', justify=tkk.RIGHT)
        self.label_frame_number_max = tkk.Label(root, bg=bg, text='/ 000000', justify=tkk.LEFT)
        self.label_time_max = tkk.Label(root, bg=bg, text='/ 00:00.000', justify=tkk.LEFT)

        self.frame_number_var = tkk.StringVar()
        self.frame_number_var.set('%06d' % self._current_frames)
        self.time_var = tkk.StringVar()
        self.time_var.set('00:00.000')
        self.fps_var = tkk.StringVar()
        self.fps_var.set('%d' % self._fps)
        self.interval_var = tkk.StringVar()
        self.interval_var.set('%d F' % self._interval)

        # just test
        self.label_frame_number_max['text'] = '/ %d' % self._total_frames
        self._total_time, minutes, sec, msec = self._transfer_frame_to_time(self._total_frames, self._fps)
        self.label_time_max['text'] = '/ %02d:%02d.%03d' % (minutes, sec, msec)

        self.input_frame_number = tkk.Entry(root, bg=bg, width=10, justify=tkk.RIGHT, bd=0,
                                            textvariable=self.frame_number_var)
        self.input_time = tkk.Entry(root, bg=bg, width=10, bd=0, justify=tkk.RIGHT,
                                    textvariable=self.time_var)
        self.input_fps = tkk.Entry(root, bg=bg, width=10, bd=0, justify=tkk.LEFT,
                                   textvariable=self.fps_var)
        self.input_interval = tkk.Entry(root, bg=bg, width=10, bd=0, justify=tkk.LEFT,
                                        textvariable=self.interval_var)

        self._input_var_dict = {self.input_interval: self.interval_var,
                                self.input_fps: self.fps_var,
                                self.input_time: self.time_var,
                                self.input_frame_number: self.frame_number_var}

        self.mid_controller = tkk.Frame(root, bg=bg, width=100, height=20)
        self.label_interval = tkk.Label(root, bg=bg, text='Interval: ')

        self.label_state_panel = tkk.Label(root, bg=bg, text='Please open a new dataset.')
        self.scale = ScaleController(root, bg=bg)
        self.scale.RateChangeHook = self.change_scale
        self.label_fps = tkk.Label(root, bg=bg, text='FPS: ')

        # create grid layout
        root.rowconfigure(0, weight=1)
        root.columnconfigure(3, weight=1)

        self.progress_bar.grid(row=1, column=0, columnspan=6, sticky=tkk.NSEW)
        self.label_frame_number.grid(row=2, column=0, sticky=tkk.E)
        self.input_frame_number.grid(row=2, column=1, sticky=tkk.E)
        self.label_frame_number_max.grid(row=2, column=2, sticky=tkk.W)
        self.label_time.grid(row=3, column=0, sticky=tkk.E)
        self.input_time.grid(row=3, column=1, sticky=tkk.E)
        self.label_time_max.grid(row=3, column=2, sticky=tkk.W)
        self.label_fps.grid(row=3, column=4, sticky=tkk.E)
        self.input_fps.grid(row=3, column=5, sticky=tkk.W)

        self.mid_controller.grid(row=2, column=3, rowspan=2, sticky=tkk.NSEW)
        self.label_state_panel.grid(row=0, column=0, columnspan=3, sticky=tkk.W)
        self.scale.grid(row=0, column=3, columnspan=3, sticky=tkk.E)
        self.label_interval.grid(row=2, column=4)
        self.input_interval.grid(row=2, column=5)

        # create index for buttons
        self.BTN_PREVIOUS = 1
        self.BTN_NEXT = 3
        self.BTN_PLAY_PAUSE = 2
        self.BTN_RESTART = 0
        self.BTN_END = 4

        self._play_state = False
        self._bind_workspace: tkk.Canvas = canvas_workspace

        # create mid_controller button
        self.buttons_names = ['Restart\n|<--',
                              'Previous\n<<-',
                              'Play',
                              'Next\n->>',
                              'End\n-->|']
        self.buttons_hooks = [Dict() for _ in self.buttons_names]
        self.buttons = []
        self.buttons_funcs = [
            lambda: self._btn_hooks(self.buttons_hooks[0]),
            lambda: self._btn_hooks(self.buttons_hooks[1]),
            lambda: self._btn_hooks(self.buttons_hooks[2]),
            lambda: self._btn_hooks(self.buttons_hooks[3]),
            lambda: self._btn_hooks(self.buttons_hooks[4])
        ]

        for n, name_str in enumerate(self.buttons_names):
            btn = tkk.Button(self.mid_controller, bg=bg,
                             command=self.buttons_funcs[n],
                             width=self.BTN_WIDTH, text=name_str, relief='flat')
            btn.grid(row=0, column=(n + 1), sticky=tkk.NS)
            self.buttons.append(btn)
        self.mid_controller.columnconfigure(0, weight=1)
        self.mid_controller.columnconfigure(len(self.buttons) + 1, weight=1)
        self.mid_controller.rowconfigure(0, weight=1)

        # add self hook functions to widgets

        self.progress_bar.HookSelecting = self.show_progress_selecting
        self.progress_bar.HookClick = self.set_new_position
        self.progress_bar.HookLeaving = self.clear_status
        self.add_button_hook(self.BTN_PLAY_PAUSE, 'play_stop_text', self._play_pause_button)
        # self.add_button_hook(self.BTN_PLAY_PAUSE, 'play_enter', self._clear_inputs_focus)
        self.add_button_hook(self.BTN_RESTART, 'go_to_start', lambda: self.go_to_frame(1))
        self.add_button_hook(self.BTN_END, 'go_to_end', lambda: self.go_to_frame(self._total_frames))
        self.add_button_hook(self.BTN_PREVIOUS, 'go_to_pre',
                             lambda: self.go_to_frame(self._current_frames - self._interval))
        self.add_button_hook(self.BTN_NEXT, 'go_to_next',
                             lambda: self.go_to_frame(self._current_frames + self._interval))

        self.bind('<Button-1>', self._clear_inputs_focus)
        self.bind_class('Label', '<Button-1>', self._clear_inputs_focus)
        self.bind_class('Frame', '<Button-1>', self._clear_inputs_focus)
        # self.bind_class('Button', '<Button-1>', self._clear_inputs_focus)
        self.set_data([])

        # binding self check event
        MemoryValidateTag.RegisterWidgetFuncs(self.input_interval, self.change_interval)
        MemoryValidateTag.RegisterWidgetFuncs(self.input_time, self.change_time)
        MemoryValidateTag.RegisterWidgetFuncs(self.input_frame_number, self.change_frame)
        MemoryValidateTag.RegisterWidgetFuncs(self.input_fps, self.change_fps)


    def set_data(self, data_frames: list,
                 fps_default: int = 10,
                 interval_default: int = 1):
        if not isinstance(data_frames, Iterable):
            raise Exception('The input data object must be Iterable!')
        if not isinstance(data_frames, Sized):
            raise Exception('The input data object must be Sized')

        self._total_frames = len(data_frames)
        if self._total_frames == 0:
            self.panel_locker(tkk.DISABLED)
            self.buttons[2]['state'] = tkk.DISABLED
            self.progress_bar.set_mini_width(1)
            self.progress_bar.Click = False
            self.progress_bar.PercentageBottom = 0
            self.label_time_max['text'] = '/ %02d:%02d.%03d' % (0, 0, 0)
            self.label_frame_number_max['text'] = '%d' % 0
            return

        self._fps = fps_default
        self._interval = interval_default

        # initialize panel
        self._current_frames = 1
        self._current_time = 0
        self._spf = 1000 // self._fps
        self._total_time, minutes, sec, msec = self._transfer_frame_to_time(self._total_frames, self._fps)
        self.label_time_max['text'] = '/ %02d:%02d.%03d' % (minutes, sec, msec)
        self.label_frame_number_max['text'] = '/ %d' % self._total_frames
        self._max_interval = self._total_frames // 4
        self.panel_locker(tkk.NORMAL)
        self.buttons[2]['state'] = tkk.NORMAL
        self.progress_bar.set_mini_width(self._total_frames)
        self.progress_bar.Click = True
        self.data_frames = data_frames
        self.height = self.frame_height = data_frames[0].height
        self.width = self.frame_width = data_frames[0].width
        self.set_all_panel()

    def bind_workspace(self, ws: tkk.Canvas):
        assert isinstance(ws, tkk.Canvas), 'You have to bind a valid Canvas object, but we got {}'.format(type(ws))
        self._bind_workspace = ws

    def update_workspace(self):
        self.imgTK = ImageTk.PhotoImage(self.data_frames[self._current_frames - 1]
                                        .resize((self.width, self.height)))
        if self.tk_image is None:
            self.tk_image = self._bind_workspace.create_image(0, 0, anchor='nw', image=self.imgTK)
        else:
            self._bind_workspace.itemconfig(self.tk_image, image=self.imgTK)
        # self._L.debug('--------> Frame %d' % self._current_frames)

    # def update_tick(self):
    #     if not self.Play:
    #         self._L.info('Play ended successfully!')
    #         return
    #     # update panel info
    #     self.go_to_frame(self._current_frames + self._interval)
    #     # update frame
    #     self.update_workspace()
    #
    #     if self._current_frames == self._total_frames:
    #         self.Play = False
    #
    #     if self.Play:
    #         self.after(self._spf, self.update_tick)
    #     else:
    #         self._L.info('Play ended successfully!')

    def update_tick(self):
        if (not self.Play) or self._current_frames == self._total_frames:
            self._L.info('Play ended successfully!')
            self.Play = False
            return
        else:
            self.after(self._spf, self.update_tick)

        # update panel info
        self.go_to_frame(self._current_frames + self._interval)
        # update frame
        self.update_workspace()

    # region ====================== Event Methods ========================
    def change_scale(self, rate):
        self.width = int(self.frame_width*rate)
        self.height = int(self.frame_height*rate)
        self.update_workspace()
        # self._L.debug('Change size to (%d, %d)')

    def change_interval(self, t):
        if t.isdecimal():
            t = t + 'F'
        mode = t[-1]
        if mode in list(self.IntType):
            num = float(t[:-1])
            interval_func = self.IntType[mode]
            interval = interval_func(num)
            if interval > self._max_interval:
                self._L.warning('Interval value must be less than 1/4 of total frames, we got {} > {}'
                                .format(interval, self._max_interval))
                interval = self._total_frames // 4
            interval = max(interval, 1)
            inverse_func = self.IntTypeInverse[mode]
            right_str = '%s %s' % (inverse_func(interval), mode)
            self._interval = interval

            return right_str
        else:
            self._L.error('Unknown unit, the unit must be in {}! <{}>'.format(list(self.IntType), t[-1]))
            raise MemoryValidateTag.ValidateValueError("Unrecognized format in mode: {}".format(mode))

    # set Time
    def change_time(self, time: str):
        t = list(map(float, time.split(':')))
        if len(t) > 1:
            t = t[0] * 60 + t[1]
        elif len(t) == 1:
            t = t[0]
        else:
            raise MemoryValidateTag.ValidateValueError("Too much splitters, please use 'xx:xx.xxxx' or 'float' type.")
        seconds = min(max(t, 0.0), self._total_time)
        self._L.debug('Got time: {}'.format(seconds))
        if seconds == self._current_time:
            return
        self._current_frames = round(self._fps * seconds)
        self._L.debug('Got frames: {}'.format(self._current_frames))
        self.set_all_panel()
        self.update_workspace()

    def change_fps(self, fps: str):
        fps = int(fps)
        if fps < 1 or fps > self.MAX_FPS:
            self._L.error('Fps value must at [1, 60], but we got %d.' % fps)
            fps = min(max(1, fps), self.MAX_FPS)
            self._L.info('Reset to %d' % fps)
        elif fps == self._fps:
            return
        self._fps = fps
        self._spf = 1000 // fps
        self.TimeVar = self._current_frames / self._fps
        self._total_time, minutes, sec, msec = self._transfer_frame_to_time(self._total_frames, self._fps)
        self.label_time_max['text'] = '/ %02d:%02d.%03d' % (minutes, sec, msec)

    def change_frame(self, frames: str):
        t = int(frames)
        if t == self._current_frames:
            return
        self._current_frames = min(max(1, t), self._total_frames)
        self.set_all_panel()

    # endregion
    # region ====================== Properties ========================

    @property
    def TimeVar(self):
        return self._current_time

    @TimeVar.setter
    def TimeVar(self, time_seconds: float):
        if time_seconds == self._current_time:
            return
        self._current_time = time_seconds
        minutes, seconds = divmod(time_seconds, 60)
        m_seconds, seconds = modf(seconds)
        self.time_var.set('%02d:%02d.%03d' % (minutes, seconds, m_seconds * 1000))

    @property
    def Play(self):
        return self._play_state

    @Play.setter
    def Play(self, value: bool):
        if value and self._play_state:
            self._L.warning('Nothing to do with play state.')
            return
        elif value:
            # play
            self.buttons[self.BTN_PLAY_PAUSE]['text'] = 'Pause\n| |'
            self.panel_locker(tkk.DISABLED)
            # self._clear_inputs_focus(None)
            self._play_state = True
            if self._current_frames == self._total_frames:
                self._current_frames = 0
            self.after(self._spf, self.update_tick)
        else:
            # pause
            self._L.info('End playing!')
            self._play_state = False
            self.buttons[self.BTN_PLAY_PAUSE]['text'] = 'Play'
            self.panel_locker(tkk.NORMAL)

        self.buttons[self.BTN_PLAY_PAUSE].update()
        self._play_state = value

    # endregion

    def _btn_hooks(self, hooks):
        if self._focus_on_entry:
            self.focus_set()
            self._focus_on_entry = False
        else:
            self._clear_inputs_focus(None)
            for hook in hooks.values():
                hook()

    def _remember_last(self, event):
        x: tkk.Entry = event.widget
        x.select_present()
        x.select_range(0, 10)
        var = self._input_var_dict[x]
        self._temp_str = var.get()
        self._L.debug('Temp str: %s' % self._temp_str)
        self._focus_on_entry = True

    def _clear_inputs_focus(self, event):
        self._L.debug('Clear focus.')
        self.focus_set()
        self._focus_on_entry = False

    @staticmethod
    def _transfer_frame_to_time(frame, fps):
        time = frame / fps
        m, sec = divmod(time, 60)
        ms, sec = modf(sec)
        return time, m, sec, round(ms * 1000)

    @staticmethod
    def _transfer_time_to_frames(time, fps):
        return round(time * fps)

    def clear_status(self):
        self.label_state_panel['text'] = ''

    def show_progress_selecting(self, percentage):
        t = min(max(1, ceil(percentage * self._total_frames)), self._total_frames)
        percentage = t / self._total_frames
        self.label_state_panel['text'] = 'Selecting: %.2f%%, frame %d' % (percentage * 100, t)
        return percentage

    def set_new_position(self, percentage):
        if self._play_state:
            self.buttons[self.BTN_PLAY_PAUSE].invoke()
        self._current_frames = min(max(1, ceil(percentage * self._total_frames)), self._total_frames)
        self.set_all_panel()

    def go_to_frame(self, frame: int):
        self._current_frames = min(max(1, frame), self._total_frames)
        self.set_all_panel()

    def set_all_panel(self, frames=-1):
        # self.label_state_panel['text'] = 'Current: %.2f%%, frame %d' % (self.progress_bar.Percentage * 100,
        #                                                               self._current_frames)
        if frames != self._current_frames:
            self.frame_number_var.set('%d' % self._current_frames)
            self.progress_bar.Percentage = self._current_frames / self._total_frames
            self.update_workspace()

        # change time
        self.TimeVar = self._current_frames / self._fps

    def add_button_hook(self, button_index: int, hook_name, hook_func):
        name = self.buttons_names[button_index]
        d = self.buttons_hooks[button_index]
        if d.get(hook_name) is not None:
            self._L.debug('Hook name <{}> replace with new one in Button <{}>!'.format(hook_name, name))
        else:
            self._L.debug('New hook function <{}> is added to Button <{}>'.format(hook_name, name))
        d[hook_name] = hook_func

    def remove_button_hook(self, button_index: int, hook_name):
        name = self.buttons_names[button_index]
        d = self.buttons_hooks[button_index]
        if d.get(hook_name) is None:
            self._L.warning('Hook name <{}> does not exist! Nothing to do with Button <{}>.'.format(hook_name, name))
        else:
            d.pop(hook_name)
            self._L.debug('Hook name <{}> is removed in Button <{}>'.format(hook_name, name))

    def _play_pause_button(self):
        self.Play = not self.Play

    def panel_locker(self, lock):
        for i in [0, 1, 3, 4]:
            self.buttons[i]['state'] = lock
        self.input_frame_number['state'] = lock
        self.input_time['state'] = lock
        self.input_interval['state'] = lock
        self.input_fps['state'] = lock


# class DrawingBoard(tkk.Canvas, metaclass=LoggerMeta):
#     _L: Logger = None
#
#     def __init__(self, name, master, cnf, **kw):
#         super().__init__(master, cnf, **kw)
#         self.imgTK = None   # image tk object
#         self._bg_x = 0
#         self._bg_y = 0
#
#     def change_mode(self):
#         # set different drawing mode here
#         pass
#
#     def BackgroundImage(self, image: Image):
#         pass
#
#     def put_background(self, x, y):
#         self.image_on_canvas = self.create_image(x, y)

