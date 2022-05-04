from typing import List, Tuple

import cv2
import os
import tqdm
import numpy as np
import time
from logging import Logger
from common.logger import LoggerMeta


def _validation(img_list, skip=False):
    if len(img_list) < 1:
        raise RuntimeError('Input image list is empty!')

    img_demo = cv2.imread(img_list[0])
    if img_demo is None:
        raise IOError('Read image error (empty object): %s' % img_list[0])

    if skip:
        return img_demo.shape

    h, w, c = img_demo.shape
    lst = tqdm.tqdm(img_list)
    for img_file in lst:
        lst.set_description('Validating image file: %s' % os.path.basename(img_file))
        img = cv2.imread(img_file)
        if img is None:
            raise IOError('Read image error (empty object): %s' % img_file)
        hh, ww, cc = img.shape
        if hh == h and ww == w and cc == c:
            pass
        else:
            raise RuntimeError('Images in sequence have different size({},{},{} v.s. {},{},{}): %s'
                               .format(hh, ww, cc, h, w, c, img_file))
    return img_demo.shape


class Frame(object):

    def __init__(self, image_list, width_out, height_out, start_scale=1.0, zoom_scale: list = None):
        self._lst = image_list
        self._length = len(image_list)

        if zoom_scale is None:
            self.zoom_scale = [i*0.1 for i in range(1, 101)]
        else:
            self.zoom_scale = zoom_scale

        # set initial parameters
        self._scale = start_scale
        self._scale_index = self.zoom_scale.index(start_scale)
        self._start_scale = self._scale_index
        self._off_x = 0
        self._off_y = 0
        self._frame_index = -1

        # validation
        self._IMAGE_HEIGHT, self._IMAGE_WIDTH, self._IMAGE_CHANNEL = _validation(self._lst, True)
        self._image_height, self._image_width = self._IMAGE_HEIGHT, self._IMAGE_WIDTH
        self._width_out = min(width_out, self._IMAGE_WIDTH)
        self._height_out = min(height_out, self._IMAGE_HEIGHT)

        # prepare data
        self._frame_curr = None   # 当前的原始帧
        self._frame_out = None    # 经过缩放后的帧
        self._frame = None         # 实际要输出的帧

        self.set_frame(0)

    @property
    def range_rectangle_global(self):
        return self._off_x / self.scale, self._off_y / self.scale, \
               (self._off_x + self._width_out) / self.scale, (self._off_y + self._height_out) / self.scale

    def get_global_location(self, x, y):
        return (x + self._off_x) / self.scale, (y + self._off_y) / self.scale

    @property
    def off_x(self):
        return self._off_x

    @property
    def off_y(self):
        return self._off_y

    @property
    def frame_out_size(self):
        return self._width_out, self._height_out

    @property
    def frame_index(self):
        return self._frame_index

    @property
    def frame(self):
        """
        获取当前帧的副本
        :return:
        """
        return self._frame.copy()

    def _crop(self, off: Tuple = None):
        if off is not None:
            _off_x = min(max(off[0], 0), self._image_width - self._width_out)
            _off_y = min(max(off[1], 0), self._image_height - self._height_out)

            if self._off_x == _off_x and self._off_y == _off_y:
                return
            self._off_y = _off_y
            self._off_x = _off_x
        self._frame = self._frame_out[self._off_y: self._off_y + self._height_out,
                                      self._off_x: self._off_x + self._width_out]

    def move_delta(self, delta_x, delta_y):
        self._crop((self._off_x + delta_x, self._off_y + delta_y))

    def set_offset(self, x, y):
        self._crop((x, y))

    def set_frame(self, index):
        if index != self._frame_index:
            index %= self._length
            self._frame_curr = cv2.imread(self._lst[index])
            self._frame_index = index
            self._zoom(self._scale)
            self._crop()

    def __len__(self):
        return self._length

    def previous_frame(self, n=1):
        self.set_frame(self._frame_index - n)

    def next_frame(self, n=1):
        self.set_frame(self._frame_index + n)

    def zoom_in(self, x, y):
        self.zoom_from_point(x, y, 1)

    def zoom_out(self, x, y):
        self.zoom_from_point(x, y, -1)

    def zoom_from_point(self, x, y, index_add):
        self._scale_index = min(max(0, self._scale_index + index_add), len(self.zoom_scale))
        scale_ori = self.scale
        self._zoom(self.zoom_scale[self._scale_index])
        off_x = int(self.scale * (self._off_x + x) / scale_ori - x)
        off_y = int(self.scale * (self._off_y + y) / scale_ori - y)
        self._crop((off_x, off_y))

    def reset_scale(self):
        self._zoom(self.zoom_scale[self._start_scale])

    def _zoom(self, scale_factor):
        if scale_factor == 1.0:
            self._scale = 1.0
            self._frame_out = self._frame_curr.copy()
            self._image_height, self._image_width, _ = self._frame_out.shape
            return

        self._scale = scale_factor
        frame_out = cv2.resize(self._frame_curr, None, fx=scale_factor, fy=scale_factor,
                               interpolation=cv2.INTER_LANCZOS4)
        h, w, _ = frame_out.shape
        if self._width_out > w or self._height_out > h:
            self._scale_index += 1
            return

        self._frame_out = frame_out
        self._image_height, self._image_width, _ = frame_out.shape

    @property
    def scale(self):
        return self._scale


class AdvancedFrame(metaclass=LoggerMeta):

    _L: Logger = None

    def __init__(self, image_list, width_out, height_out, start_scale=1.0, zoom_scales: list = None):

        self._lst = image_list
        self._IMAGE_HEIGHT, self._IMAGE_WIDTH, self._IMAGE_CHANNEL = _validation(self._lst, True)
        self._length = len(self._lst)

        self._OUT_WIDTH = min(width_out, self._IMAGE_WIDTH)
        self._OUT_HEIGHT = min(height_out, self._IMAGE_HEIGHT)
        self._ADV_IMAGE_SIZE_WIDTH = width_out * 3
        self._ADV_IMAGE_SIZE_HEIGHT = height_out * 3

        min_scale_factor = max(self._OUT_WIDTH/self._IMAGE_WIDTH, self._OUT_HEIGHT/self._IMAGE_HEIGHT) - 0.001

        if zoom_scales is None:
            self.zoom_scales = [i * 0.1 for i in range(1, 101) if i*0.1 > min_scale_factor]
            # self.zoom_scales = [0.5, 0.6, 1.6, 2.6]
        else:
            self.zoom_scales = zoom_scales

        if 1.0 not in self.zoom_scales:
            self.zoom_scales += [1.0]
            self.zoom_scales.sort()

        if start_scale not in self.zoom_scales:
            assert isinstance(start_scale, float), 'start scale must be float!'
            self.zoom_scales += [start_scale]
            self.zoom_scales.sort()

        # 高级切图内参
        self._advance_off_x = 0
        self._advance_off_y = 0
        self._advance_off_x_ori = 0
        self._advance_off_y_ori = 0

        self._image_width = 0
        self._image_height = 0
        self._adv_region_ori_width = 0
        self._adv_region_ori_height = 0
        self._off_x = 0
        self._off_y = 0
        self._off_x_inner = 0
        self._off_y_inner = 0

        # 帧内参初始化
        self._frame_index = -1
        self._scale = start_scale
        self._scale_index = self.zoom_scales.index(start_scale)
        self.__start_scale_index = self._scale_index
        self._original_image = None
        self._image_crop = None
        self._frame_curr = None    # 从原始图像crop后resize过的帧图像
        self._frame = None         # 实际crop后的图像

        self.image_qualities = []
        self.image_quality_names = ['Lanczos4', 'Cubic', 'fff', 'Area', 'Linear_Exact', 'aasf', 'Nearest_Exact']

        for i in range(len(self.image_quality_names)-1, -1, -1):
            name = 'INTER_' + self.image_quality_names[i].upper()
            value = getattr(cv2, name, None)
            if value is None:
                self.image_quality_names.pop(i)
                self._L.debug('Removed unsupported method: %s' % name)
            else:
                self.image_qualities.insert(0, value)

        self.image_quality_index = 0
        self._quality = self.image_qualities[self.image_quality_index]

    @property
    def off_x(self):
        return self._off_x

    @property
    def off_y(self):
        return self._off_y

    @property
    def scale(self):
        return self._scale

    @property
    def frame_index(self):
        return self._frame_index

    @property
    def frame(self):
        return self._frame.copy()

    @property
    def range_rectangle_global(self):
        return self._off_x / self.scale, self._off_y / self.scale, \
               (self._off_x + self._OUT_WIDTH) / self.scale, (self._off_y + self._OUT_HEIGHT) / self.scale

    @property
    def frame_out_size(self):
        return self._OUT_WIDTH, self._OUT_HEIGHT

    def get_global_poly(self, poly_points):
        return (poly_points[:] + [self.off_x, self.off_y]) / self.scale

    def get_global_location(self, x, y):
        return (x + self._off_x) / self.scale, (y + self._off_y) / self.scale

    def set_frame(self, index):
        if index != self._frame_index:
            index %= self._length
            self._original_image = cv2.imread(self._lst[index])
            self._frame_index = index
            self._crop_zoom_original(self._off_x, self._off_y, self._scale)

    def zoom_in(self, x, y):
        self.zoom_from_point(x, y, 1)

    def zoom_out(self, x, y):
        self.zoom_from_point(x, y, -1)

    def zoom_from_point(self, x, y, index_add):
        index = min(max(0, self._scale_index + index_add), len(self.zoom_scales)-1)
        if index == self._scale_index:
            return
        scale_ori = self.scale
        scale = self.zoom_scales[index]
        self._scale_index = index

        off_x = int(round(scale * (self._off_x + x) / scale_ori - x))
        off_y = int(round(scale * (self._off_y + y) / scale_ori - y))
        self._crop_zoom_original(off_x, off_y, scale)

    def zoom_from_center_index(self, index_add):
        index = min(max(0, self._scale_index + index_add), len(self.zoom_scales) - 1)
        if index == self._scale_index:
            return
        self.zoom_from_center(self.zoom_scales[index])

    def zoom_from_center(self, scale):
        x = self._OUT_WIDTH // 2
        y = self._OUT_HEIGHT // 2

        off_x = int(round(scale * (self._off_x + x) / self._scale - x))
        off_y = int(round(scale * (self._off_y + y) / self._scale - y))

        self._crop_zoom_original(off_x, off_y, scale)

    def _crop_zoom_original(self, off_x, off_y, scale):
        self._scale = scale
        # 预测通过opencv方式获取的缩放后的尺寸
        self._image_width = int(round(self._IMAGE_WIDTH * scale))
        self._image_height = int(round(self._IMAGE_HEIGHT * scale))

        self._off_x = max(min(off_x, self._image_width-self._OUT_WIDTH-1), 0)
        self._off_y = max(min(off_y, self._image_height-self._OUT_HEIGHT-1), 0)

        self._advance_off_x = self._off_x-self._OUT_WIDTH
        self._advance_off_y = self._off_y-self._OUT_HEIGHT

        self._advance_off_x_ori = int(self._advance_off_x // scale)
        self._advance_off_y_ori = int(self._advance_off_y // scale)
        self._adv_region_ori_width = int(self._ADV_IMAGE_SIZE_WIDTH // scale)
        self._adv_region_ori_height = int(self._ADV_IMAGE_SIZE_HEIGHT // scale)

        ori_x = max(self._advance_off_x_ori, 0)
        ori_y = max(self._advance_off_y_ori, 0)
        ori_xx = min(self._advance_off_x_ori+self._adv_region_ori_width, self._IMAGE_WIDTH)
        ori_yy = min(self._advance_off_y_ori+self._adv_region_ori_height, self._IMAGE_HEIGHT)

        self._image_crop = self._original_image[ori_y:ori_yy, ori_x:ori_xx]
        self._frame_curr = cv2.resize(self._image_crop, None, fx=scale, fy=scale, interpolation=self._quality)
        self._adv_region_height, self._adv_region_width, _ = self._frame_curr.shape

        self.move_delta(0, 0, False)

        # self._off_x_inner = self._off_x if self._advance_off_x < 0 else self._OUT_WIDTH
        # self._off_y_inner = self._off_y if self._advance_off_y < 0 else self._OUT_HEIGHT
        #
        # self._frame = self._frame_curr[self._off_y_inner: self._off_y_inner + self._OUT_HEIGHT,
        #                                self._off_x_inner: self._off_x_inner + self._OUT_WIDTH]
        # print(self.scale)
        # print(self._frame_curr.shape)
        # print(self._frame.shape)

    def move_delta(self, delta_x, delta_y, auto_skip=True):

        _off_x = max(min(self._off_x+delta_x, self._image_width - self._OUT_WIDTH - 1), 0)
        _off_y = max(min(self._off_y+delta_y, self._image_height - self._OUT_HEIGHT - 1), 0)

        _off_x_inner = min(_off_x if self._advance_off_x < 0 else _off_x-self._advance_off_x, self._adv_region_width-self._OUT_WIDTH)
        _off_y_inner = min(_off_y if self._advance_off_y < 0 else _off_y-self._advance_off_y, self._adv_region_height-self._OUT_HEIGHT)

        if auto_skip and _off_x_inner == self._off_x_inner and _off_y_inner == self._off_y_inner:
            return

        if _off_x_inner != self._off_x_inner:
            self._off_x = _off_x
            self._off_x_inner = _off_x_inner
        if _off_y_inner != self._off_y_inner:
            self._off_y = _off_y
            self._off_y_inner = _off_y_inner

        self._frame = self._frame_curr[
                      self._off_y_inner: self._off_y_inner + self._OUT_HEIGHT,
                      self._off_x_inner: self._off_x_inner + self._OUT_WIDTH
                      ]

    def set_new_position(self):
        self._crop_zoom_original(self._off_x, self._off_y, self._scale)

    def t_func(self):
        self._original_image = cv2.imread(self._lst[0])
        self._crop_zoom_original(100, 123, 2.0)
        print(self._frame_curr.shape)
        print(self._frame.shape)
        cv2.namedWindow('frame_curr', cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow('frame', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('frame_curr', self._frame_curr)
        cv2.imshow('frame', self._frame)
        cv2.waitKey(0)

    def __len__(self):
        return self._length

    def previous_n_frame(self, n=1):
        if self._scale_index == 0:
            self._L.error(u'您已经在第一帧，不能再前啦！')
            return
        if self._frame_index - n < 0:
            self._L.warning(u'前进超出了第一帧，自动停在第一帧。')
            self.set_frame(0)
        else:
            self.set_frame(self._frame_index - n)

    def next_n_frame(self, n=1):
        if self._scale_index == 0:
            self._L.error(u'您已经在最后一帧，不能再往后啦！')
            return
        if self._frame_index + n < self._length:
            self.set_frame(self._frame_index + n)
        else:
            self._L.warning(u'前进超出了最后一帧，自动停在最后一帧。')
            self.set_frame(self._length - 1)

    def change_quality(self):
        self.image_quality_index += 1
        self.image_quality_index %= len(self.image_qualities)
        self._L.info(u'图像质量改变为：%s' % self.image_quality_names[self.image_quality_index])
        self._quality = self.image_qualities[self.image_quality_index]
        self._frame_curr = cv2.resize(self._image_crop, None, fx=self.scale, fy=self.scale, interpolation=self._quality)
        self.move_delta(0, 0, False)

    def reset_scale(self):
        if self.__start_scale_index == self._scale_index:
            self._L.error(u'当前已经在初始尺度下，无需重置！')
            return
        self._scale_index = self.__start_scale_index
        scale = self.zoom_scales[self._scale_index]
        self.zoom_from_center(scale)


class CanvasBase(metaclass=LoggerMeta):
    _L: Logger = None
    """
    The functional canvas developed with opencv.
    """
    class ExitCanvas(Exception): pass

    def __init__(self, win_name):
        self.__win_name = win_name
        self._frame_show = None
        self.__need_refresh = True

    @property
    def win_name(self):
        return self.__win_name

    def refresh(self):
        self.__need_refresh = True

    def _mouse_event(self, key, x, y, flag, params):
        print("key:", key)
        print("x:", x)
        print("y:", y)
        print("flag:", flag)
        print('params:', params)

    def _refresh(self):
        image = np.zeros((200, 200))
        if getattr(self, 'tic', None) is None:
            self.tic = time.time()
        else:
            now = time.time()
            cv2.putText(image, '%.2f' % (1/(now-self.tic)), (10, 100), 0, 0.5, [255, 255, 255], 2)
            self.tic = now
        return image

    def _key_map(self, key):
        if key > 0:
            print(key)

    def _quick_show(self, frame):
        cv2.imshow(self.win_name, frame)

    def run(self, window_location=None):
        try:
            cv2.getWindowImageRect(self.__win_name)
        except cv2.error:
            cv2.namedWindow(self.__win_name, cv2.WINDOW_AUTOSIZE)
        if window_location is not None:
            assert isinstance(window_location, (List, Tuple)) and len(window_location) == 2, \
                'Window location must be a List or a Tuple with two values -> (x, y).'
            cv2.moveWindow(self.__win_name, *window_location)
        cv2.setMouseCallback(self.__win_name, self._mouse_event)

        try:
            while True:
                if self.__need_refresh:
                    self._frame_show = self._refresh()
                    self.__need_refresh = False
                    cv2.imshow(self.__win_name, self._frame_show)
                key = cv2.waitKey(1)
                if key < 0:
                    continue
                self._key_map(key)
        except self.ExitCanvas:
            cv2.setMouseCallback(self.__win_name, lambda *args: None)

    def destroy(self):
        cv2.destroyWindow(self.__win_name)


def print_events():
    d = cv2.__dict__
    for dd in d:
        if dd.startswith('EVENT_'):
            print("{}: {}".format(dd, d[dd]))


class WorkCanvas(CanvasBase):
    def __init__(self, win_name, font, font_height):
        super().__init__(win_name)
        self._frame: AdvancedFrame = None
        self.mouse_x = 0
        self.mouse_y = 0

        self.__font = font
        self.__font_height = font_height

        self.__drag = False
        self.__drag_start_x = 0
        self.__drag_start_y = 0

    def set_frame_obj(self, frame: AdvancedFrame):
        self._frame = frame

    def _refresh(self):
        # return super()._refresh()
        frame = self._frame.frame
        frame_text = '%d/%d | %.2f%%' % (self._frame.frame_index+1, len(self._frame), self._frame.scale*100)
        cv2.putText(frame, frame_text, (20, 20), 0, 0.5, (255, 255, 255), 1)

        return frame

    def _mouse_event(self, key, x, y, flag, params):
        if key == cv2.EVENT_MOUSEMOVE:
            if self.__drag:
                delta_x = self.__drag_start_x - x
                delta_y = self.__drag_start_y - y
                self._frame.move_delta(delta_x, delta_y)
                self.__drag_start_y = y
                self.__drag_start_x = x
                self.refresh()

        elif key == cv2.EVENT_LBUTTONDOWN:
            f = flag - key
            if f == cv2.EVENT_FLAG_ALTKEY:
                # 放大
                self._frame.zoom_in(x, y)
                self.refresh()
            elif f == cv2.EVENT_FLAG_SHIFTKEY:
                # 缩小
                self._frame.zoom_out(x, y)
                self.refresh()
            elif f == cv2.EVENT_FLAG_CTRLKEY:
                # print('drag')
                self.__drag = True
                self.__drag_start_x = x
                self.__drag_start_y = y
                self.refresh()
        elif key == cv2.EVENT_LBUTTONUP:
            if self.__drag:
                self.__drag = False
                # print('up')
                self._frame.set_new_position()
                self.refresh()

    def _key_map(self, key):
        if key == ord('a'):
            # 前一帧
            self._frame.previous_n_frame()
            self.refresh()
        elif key == ord('s'):
            self._frame.next_n_frame()
            self.refresh()
        elif key == ord('d'):
            self._frame.previous_n_frame(10)
            self.refresh()
        elif key == ord('f'):
            self._frame.next_n_frame(10)
            self.refresh()
        elif key == ord('Q'):
            raise self.ExitCanvas('Exit')
        elif key == ord('r'):
            self._frame.reset_scale()
            self.refresh()
        elif key == ord('\\'):  # 用来改变图像质量
            self._frame.change_quality()
            self.refresh()
        # if key > 0:
        #     print(key)


class StateShow(CanvasBase):

    def __init__(self, win_name, font, font_height):
        super().__init__(win_name)

    def _mouse_event(self, key, x, y, flag, params): pass




if __name__ == '__main__':
    # print_events()
    import os
    path = '/Users/cannol/PycharmProjects/sv_dataset_tools/tools/data_cache/tmp/73a2edfc01483702cc52fc41d76cc4f4'
    files = os.listdir(path)
    image_list = [os.path.join(path, i) for i in files if i.endswith('.tiff')]
    image_list.sort()
    a = AdvancedFrame(image_list, 304, 194)
    a.t_func()