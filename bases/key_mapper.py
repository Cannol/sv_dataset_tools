import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image

from logging import Logger
from common.logger import GLogger
from configs import VIDEO_TARGET_SELECTOR_FONT_FILE, KEY_MAP_CONFIG_FILE, MOUSE_EVENT_CONFIG_FILE
from common.yaml_helper import YamlConfigClassBase

_L: Logger = GLogger.get('KeyMapper', 'bases.key_mapper')

_font1 = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 15)
_, _font1_height = _font1.getsize('测试高度')
_font0 = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 30)
_, _font0_height = _font0.getsize('测试高度')


class MouseFlagMapper(YamlConfigClassBase):
    LB = 1
    LB_ALT = 33
    LB_CTRL = 9
    LB_SHIFT = 17

    RB = 2
    RB_ALT = 34
    RB_CTRL = 10
    RB_SHIFT = 18

    MOUSE_MOVE = 0
    MOUSE_ALT_MOVE = 32
    MOUSE_CTRL_MOVE = 8
    MOUSE_SHIFT_MOVE = 16

    # cv2.EVENT_FLAG_ALTKEY
    # cv2.EVENT_FLAG_CTRLKEY
    # cv2.EVENT_FLAG_SHIFTKEY


MouseFlagMapper.Load(MOUSE_EVENT_CONFIG_FILE)


def start_mouse_test():

    def mouse_event_up_down(event, x, y, flag, params):
        print(event, flag)

    width = 1200
    height = 800
    cv2.namedWindow('test', cv2.WINDOW_GUI_NORMAL | cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback('test', mouse_event_up_down)

    image = np.zeros((height, width, 3), 'uint8')
    cv2.imshow('test', image)
    while True:
        print(cv2.waitKey(0))


class KeyDescriptor(object):
    ESC = [u'ESC 按键', u'键盘左上角']
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
    F12 = [u'F12 功能键', u'按键盘上方功能键区域的F12']


class KeyMapper(YamlConfigClassBase):
    ESC = 27
    BACK_SPACE = 8
    BLANK_SPACE = 10
    ENTER = 13

    HOME = 0
    END = 0
    DEL = 0
    INS = 0

    # bu jian rong
    # ARROW_UP = 0
    # ARROW_DOWN = 0
    # ARROW_LEFT = 0
    # ARROW_RIGHT = 0

    TAB = 0
    SHIFT_TAB = 0

    SHIFT = 0
    ALT = 0
    F12 = 0


def start_key_test():
    cls = KeyMapper
    width = 1200
    height = 800
    # image = np.zeros((800, 1200, 3), 'uint8')
    cv2.namedWindow('test', cv2.WINDOW_GUI_NORMAL | cv2.WINDOW_AUTOSIZE)
    # cv2.setWindowProperty('test', cv2.WND_PROP_FULLSCREEN, 1)
    # cv2.imshow('test', image)
    # cv2.setMouseCallback('test', self.mouse_event)

    all_keys = cls.__dict__.copy()
    all_keys.pop('SHIFT')
    all_keys.pop('ALT')
    keys = [(key, getattr(KeyDescriptor, key)) for key in all_keys if (not key.startswith('_')) and isinstance(all_keys[key], int)]

    keys.insert(0, ('SHIFT', [u'SHIFT 按键', u'最好是按左边的shift或您最常用的那个shift，后续组合按键都尽量用该按键']))
    keys.insert(0, ('ALT', [u'ALT 按键', u'最好是按左边的Alt或您最常用的那个Alt，后续组合按键都尽量用该按键']))

    length = len(keys)
    index = 0
    try:
        while index < length:
            key_want, key_des = keys[index]
            title = u'按键校正工具 - 正在进行(%d/%d)' % (index+1, length)
            key_text = u'请按一下    %s   (原设置为: %d)' % (key_des[0], getattr(cls, key_want))
            key_tips = u'提示: %s' % key_des[1]
            key_tips1 = u'注意: 如果按0，则表示跳过该按键设置，不做任何修改! '

            cv2.setWindowTitle('test', title)

            image = Image.new('RGB', (width, height), 'black')
            draw = ImageDraw.Draw(image)
            text_width, _ = _font0.getsize(key_text)
            text_x = (width - text_width) / 2
            text_y = height / 2 - _font0_height
            tips_width, _ = _font1.getsize(key_tips)
            tips_x = (width - tips_width) / 2
            tips_y = height / 2 + _font0_height
            tips_width1, _ = _font1.getsize(key_tips1)
            tips_x1 = (width - tips_width1) / 2
            tips_y1 = tips_y + 2*_font1_height

            draw.text((text_x, text_y), key_text, font=_font0, fill=(225, 0, 0))
            draw.text((tips_x, tips_y), key_tips, font=_font1, fill=(150, 200, 200))
            draw.text((tips_x1, tips_y1), key_tips1, font=_font1, fill=(255, 255, 255))

            image = np.array(image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imshow('test', image)
            key = cv2.waitKey(0)
            print(key)

            if index > 1:
                while key == cls.SHIFT or key == cls.ALT:
                    key = cv2.waitKey(0)
                if key == ord('0'):
                    _L.info('跳过按键 %s (%s) 的设置.' % (key_want, key_des[0]))
                elif key == ord('q'):
                    raise ValueError('Exit!')
                else:
                    setattr(cls, key_want, key)
            else:
                if key == ord('0'):
                    _L.info('跳过按键 %s (%s) 的设置.' % (key_want, key_des[0]))
                elif key == ord('q'):
                    raise ValueError('Exit!')
                else:
                    setattr(cls, key_want, key)
            index += 1
        _L.info('Keys are set successfully!')
        cls.Save()
    except Exception as e:
        _L.info('你终止了按键调试，按键已经恢复为修改前设置!')
        cls.Load()
    cv2.destroyWindow('test')


KeyMapper.Load(KEY_MAP_CONFIG_FILE)

if __name__ == '__main__':
    start_mouse_test()