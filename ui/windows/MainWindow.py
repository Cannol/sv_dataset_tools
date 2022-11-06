import tkinter as tkk
from tkinter.ttk import Style
from logging import Logger
from common.logger import GLogger

from ui.components import TopBar, PlayController

_VERSION = '1.0beta'

"""
    This script is the First Stage of Annotation
    This step is used to create new target that need to be annotation
    The administrator or designer of the dataset is responsible for this stage 
"""

# ====================================================================
#    Common Functions
# ====================================================================
def _default_win():
    tk = tkk.Tk()
    tk.title('Cloud Labeler Client - Version %s' % _VERSION)
    tk.geometry('%dx%d+%d+%d' % (600, 600, 10, 10))
    # tk.overrideredirect(True)
    style = Style()
    style.configure('my.TButton', background='#345', foreground='black', font=('Arial', 14))
    return tk


# ====================================================================
#    Common Class
# ====================================================================
class MainWindow(object):
    # making logger
    _L: Logger = GLogger.get('MainWindow', 'client.ui.windows.MainWindow')

    # create default window
    root = _default_win()
    menu_bar = TopBar(root, height=30)
    left_panel = tkk.Frame(root)
    right_panel = tkk.Frame(root, width=400)

    menu_bar.pack(side=tkk.TOP, fill=tkk.X)
    right_panel.pack(side=tkk.RIGHT, fill=tkk.Y)
    left_panel.pack(side=tkk.LEFT, fill=tkk.BOTH, expand=tkk.YES)

    workspace = tkk.Canvas(left_panel, bg='black')
    play_controller = PlayController(left_panel, workspace, height=60, bg='Gainsboro')

    workspace.pack(expand=tkk.YES, fill=tkk.BOTH)
    play_controller.pack(fill=tkk.X, side=tkk.BOTTOM)
    right_panel.update()
    _L.debug('Got right_panel width: {}'.format(right_panel.winfo_width()))
    root.minsize(play_controller.MIN_WIDTH + right_panel.winfo_width(), 600)

    @classmethod
    def set_images(cls, images):
        cls.play_controller.set_data(images)

    @classmethod
    def RunLocalData(cls, dir_name):
        import cv2
        import os
        from PIL import Image, ImageTk
        images_list = [os.path.join(dir_name, i) for i in os.listdir(dir_name) if i.endswith('.jpg')]
        images_list.sort()
        images = [cv2.imread(i) for i in images_list]
        images_I = [Image.fromarray(cv2.cvtColor(i, cv2.COLOR_BGR2RGBA)) for i in images]
        cls.set_images(images_I)
        cls.root.mainloop()

    @classmethod
    def Run(cls):
        """
        this method include following steps:
        1. start and manage sub-processes
        2. do some prepare work before open the root screen
        3. start root screen
        4. clean the environment
        :return:int
        """
        # cls._construct()
        cls.root.mainloop()
        # cls._deconstruct()