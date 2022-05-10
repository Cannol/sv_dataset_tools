import cv2
import numpy as np
from PIL import ImageFont

from configs import VIDEO_TARGET_SELECTOR_FONT_FILE
from common.yaml_helper import YamlConfigClassBase


_font1 = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 15)
_, _font1_height = _font1.getsize('测试高度')
_font0 = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 30)
_, _font0_height = _font0.getsize('测试高度')

def _get_center_xy(win_height, win_width, x, y):


class MouseFlagMapper(YamlConfigClassBase):
    LB_DOWN = 0
    LB_UP = 0
    LB_MOVE = 0

    LB_ALT_DOWN = 0
    LB_CTRL_DOWN = 0
    LB_SHIFT_DOWN = 0

    LB_ALT_UP = 0
    LB_CTRL_UP = 0
    LB_SHIFT_UP = 0

    LB_ALT_MOVE = 0
    LB_CTRL_MOVE = 0
    LB_SHIFT_MOVE = 0

    RB_DOWN = 0
    RB_UP = 0
    RB_MOVE = 0

    RB_ALT_DOWN = 0
    RB_CTRL_DOWN = 0
    RB_SHIFT_DOWN = 0

    RB_ALT_UP = 0
    RB_CTRL_UP = 0
    RB_SHIFT_UP = 0

    RB_ALT_MOVE = 0
    RB_CTRL_MOVE = 0
    RB_SHIFT_MOVE = 0
    #
    # @classmethod
    # def start_test(cls):


class KeyDiscripter(object):
    ESC = [u'ESC', u'键盘左上角']
    BACK_SPACE = [u'Back Space 退格键', u'主键盘数字键所在行最后一个']
    BLANK_SPACE = [u'Blank Space 空格键', u'最长的那个']
    ENTER = [u'Enter 回车键', u'通常位于asdf...一排最后一个，有的拐弯成L形状']

    HOME = [u'Home 按键', u'通常位于上下左右光标按键上方的键盘区域中']
    END = [u'End 按键', u'通常位于上下左右光标按键上方的键盘区域中']
    DEL = [u'Delete 按键', u'通常位于上下左右光标按键上方的键盘区域中，有的简写为Del']
    INS = [u'Insert 按键', u'通常位于上下左右光标按键上方的键盘区域中，有的简写为Ins']

    ARROW_UP = [u'上 按键', u'光标键区域向上箭头']
    ARROW_DOWN = [u'下 按键', u'光标键区域向下箭头']
    ARROW_LEFT = [u'左 按键', u'光标键区域向左箭头']
    ARROW_RIGHT = [u'右 按键', u'光标键区域向右箭头']

    TAB = [u'Tab 按键', u'制表按键位于键盘左侧第一列，Q左边']
    SHIFT_TAB = [u'Shift + Tab 组合键', u'先按住Shift按键，再按一下Tab按键']


class KeyMapper(YamlConfigClassBase):
    ESC = 27
    BACK_SPACE = 8
    BLANK_SPACE = 10
    ENTER = 13

    HOME = 0
    END = 0
    DEL = 0
    INS = 0

    ARROW_UP = 0
    ARROW_DOWN = 0
    ARROW_LEFT = 0
    ARROW_RIGHT = 0

    TAB = 0
    SHIFT_TAB = 0

    @classmethod
    def start_test(cls):
        image = np.zeros((800, 1200, 3), 'uint8')
        cv2.namedWindow('test', cv2.WINDOW_GUI_NORMAL | cv2.WINDOW_AUTOSIZE)
        # cv2.setWindowProperty('test', cv2.WND_PROP_FULLSCREEN, 1)
        cv2.imshow('test', image)
        # cv2.setMouseCallback('test', self.mouse_event)

        all_keys = cls.__dict__
        keys = [(key, getattr(KeyDiscripter, key) for key in all_keys if (not key.startswith('_')) and isinstance(all_keys[key], int))]

        keys.insert(0, ('SHIFT', [u'SHIFT 按键', u'最好是按左边的shift或您最常用的那个shift，后续组合按键都尽量用该按键']))
        keys.insert(0, ('ALT', [u'ALT 按键', u'最好是按左边的Alt或您最常用的那个Alt，后续组合按键都尽量用该按键']))

        length = len(keys)
        index = 0

        while True:
            cv2.imshow('test', image)
            key = cv2.waitKey(0)
            key_want, key_des = keys[index]
            title = u'按键校正工具 - 正在进行(%d/%d)' % (index+1, length)
            key_text = u'请按一下  %s  按键' % key_des[0]
            key_tips = key_des[1]

            if index < 2:
                # 基础按键测试


            print(key)


KeyMapper.start_test()