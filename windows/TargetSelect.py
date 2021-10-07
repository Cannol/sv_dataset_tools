import cv2
import numpy as np


class TargetSelectWindow:
    def __init__(self, win_width, win_height, image_width, image_height, image_list, targets, window_name):

        # basic objects
        self._targets = targets
        self._image_list = image_list
        self._image_width = image_width
        self._image_height = image_height
        self._total_frames = len(self._image_list)

        # window settings
        self._width = win_width
        self._height = win_height
        self._state_bar_height = 50
        self._window_name = window_name
        cv2.namedWindow(window_name, flags=cv2.WINDOW_AUTOSIZE | cv2.WINDOW_NORMAL)

        # inner vars
        self._frame_now = np.zeros((win_height+self._state_bar_height, win_width, 3), 'uint8')
        self._image_now = None
        self._image_resize = None
        self._image_crop = np.zeros((win_height, win_width, 3), 'uint8')
        self._image_show = np.zeros((win_height, win_width, 3), 'uint8')
        self._index_now = -1
        self._invoke_refresh = [False, False]
        self._wait_time = 16
        self._scale = 1.0
        self._off_x = 0
        self._off_y = 0
        self._invoke_reshow = False

        # set hook dict
        self._actions = {}

    def _draw_targets(self):
        pass

    def _goto_frame(self, frame_index):
        if 0 <= frame_index < self._total_frames:
            self._index_now = frame_index
        else:
            self._index_now = min(max(frame_index, 0), self._total_frames-1)
        self._image_now = cv2.imread(self._image_list[self._index_now])

    def _resize_frame(self, new_scale):
        self._scale = new_scale
        self._image_resize = cv2.resize(self._image_now, None,
                                        fx=self._scale, fy=self._scale, interpolation=cv2.INTER_CUBIC)

    def _crop_frame(self):
        self._image_crop[:] = \
            self._image_resize[self._off_y:self._off_y+self._height, self._off_x:self._off_x+self._width]

    def _draw_framework(self):
        pass

    def _handle_keys(self, key):
        re = self._actions[key]
        if re is None:
            return True
        return re()

    def main_loop(self):
        is_going = True

        while is_going:
            if self._invoke_refresh[0]:
                self._draw_content()
                self._invoke_refresh[0] = False
            if self._invoke_refresh[1]:
                self._draw_framework()
                self._invoke_refresh[1] = False
            if self._invoke_reshow:
                cv2.imshow(self._window_name, self._frame_now)
                self._invoke_reshow = False

            key = cv2.waitKey(self._wait_time)
            is_going = self._handle_keys(key)




