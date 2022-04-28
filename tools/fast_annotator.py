import cv2
import numpy as np
from bases.graphic import WorkCanvas
from bases.targets import Target
from common import LoggerMeta
from logging import Logger
from bases.trackers import CVTracker


# class AutoAnnotator(metaclass=LoggerMeta):
#     _L: Logger = None
#
#     def __init__(self):
#
#
#     def feed(self):


class Annotator(WorkCanvas, metaclass=LoggerMeta):
    _L: Logger = None

    def __init__(self, win_name, font, font_height, classes: list):
        self.__annotation_state = -1   # -1 非新增模式，从0开始分别对应标注类别
        self.__classes = classes
        self.__font = font
        self.__font_height = font_height

        self.__label_new = False
        self.__label_new_start_x = 0
        self.__label_new_start_y = 0
        self.__label_new_end_x = 0
        self.__label_new_end_y = 0

        self.__targets_insight = []
        self._selected_target: Target = None
        self._selected_target_poly = np.zeros((4, 2), dtype='float')
        self._select_point = -1
        self._selected_flag = -1

        self._start_move_point = False
        self._start_drag_target = False
        self._drag_x = 0
        self._drag_y = 0

        self._tmp_frame = None

        self._auto_track = None

        # flag color
        self._flag_color = [
            [255, 0, 0],
            [0, 0, 255],
            [0, 255, 0]
        ]

        # make dict
        self.__classes_dict = {}
        for i in range(len(self.__classes)):
            self.__classes_dict[ord(str(i+1))] = i

        self.__classes_color_dict = {}
        for class_item in self.__classes:
            self.__classes_color_dict[class_item[0]] = class_item[1]

        super().__init__(win_name, font, font_height)

    @property
    def class_now(self):
        if self.__annotation_state < 0:
            return None
        return self.__classes[self.__annotation_state]

    def _mouse_event(self, key, x, y, flag, params):
        if self._selected_target:
            # print(key, flag, cv2.EVENT_LBUTTONDOWN, cv2.EVENT_FLAG_CTRLKEY)
            if key == cv2.EVENT_LBUTTONDOWN and flag == (cv2.EVENT_FLAG_CTRLKEY+key):
                self._start_drag_target = True
                self._drag_x = x
                self._drag_y = y
                return

            elif self._start_drag_target and key == cv2.EVENT_MOUSEMOVE and flag == (cv2.EVENT_FLAG_CTRLKEY+1):
                dx = x - self._drag_x
                dy = y - self._drag_y
                self._selected_target_poly += [dx, dy]
                self._tmp_frame = self._frame.frame
                selected_poly = self._selected_target_poly.astype('int').reshape((-1, 1, 2))
                self._draw_select_target(self._tmp_frame, selected_poly)
                self._quick_show(self._tmp_frame)
                self._drag_x = x
                self._drag_y = y
                return

            elif self._start_drag_target and key == cv2.EVENT_LBUTTONUP:
                self._start_drag_target = False
                self._selected_target.set_key_point(self._frame.frame_index,
                                                    self._frame.get_global_poly(self._selected_target_poly))
                self.refresh()
                return

            if self._select_point > -1:
                if key == cv2.EVENT_LBUTTONDOWN:
                    self._start_move_point = True
                    return
                elif self._start_move_point and key == cv2.EVENT_MOUSEMOVE:
                    self._selected_target_poly[self._select_point, 0] = x
                    self._selected_target_poly[self._select_point, 1] = y
                    if self._select_point == 0:
                        self._selected_target_poly[1, 1] = y
                        self._selected_target_poly[3, 0] = x
                    elif self._select_point == 1:
                        self._selected_target_poly[0, 1] = y
                        self._selected_target_poly[2, 0] = x
                    elif self._select_point == 2:
                        self._selected_target_poly[1, 0] = x
                        self._selected_target_poly[3, 1] = y
                    else:
                        self._selected_target_poly[0, 0] = x
                        self._selected_target_poly[2, 1] = y
                    self._tmp_frame = self._frame.frame
                    poly_points = self._selected_target_poly.astype('int')
                    poly_points = poly_points.reshape((-1, 1, 2))
                    self._draw_select_target(self._tmp_frame, poly_points)
                    self._quick_show(self._tmp_frame)
                    return
                    # self._selected_target.rect_poly_points[
                    #     self._frame.frame_index, :] = self._frame.get_global_poly(self._selected_target_poly)
                elif self._start_move_point and key == cv2.EVENT_LBUTTONUP:
                    self._start_move_point = False
                    self._selected_target.set_key_point(self._frame.frame_index,
                                                        self._frame.get_global_poly(self._selected_target_poly))
                    self.refresh()
                    return
                # self.refresh()

            if (not self._start_move_point) and key == cv2.EVENT_MOUSEMOVE:
                points = self._selected_target_poly
                l = np.square(points[:, 0] - x) + np.square(points[:, 1] - y)
                n = np.argmin(l)
                # print(l[n])
                if l[n] > 25:
                    n = -1
                if n != self._select_point:
                    self._select_point = n
                    # print(self._select_point)
                    self.refresh()

        if self.__label_new:
            if key == cv2.EVENT_MOUSEMOVE:
                frame = self._frame_show.copy()
                cv2.rectangle(frame, (self.__label_new_start_x, self.__label_new_start_y), (x, y),
                              color=self.class_now[1], thickness=1)
                self._quick_show(frame)
                self.__label_new_end_x = x
                self.__label_new_end_y = y
            elif key == cv2.EVENT_LBUTTONUP:
                self.__label_new = False
                start_x, start_y = self._frame.get_global_location(self.__label_new_start_x, self.__label_new_start_y)
                end_x, end_y = self._frame.get_global_location(self.__label_new_end_x, self.__label_new_end_y)
                left_x = min(start_x, end_x)
                left_y = min(start_y, end_y)
                right_x = max(start_x, end_x)
                right_y = max(start_y, end_y)
                if right_x - left_x < 2.5 or right_y - left_y < 2.5:
                    self._L.error('Too small target!')
                    self.refresh()
                    return
                Target.New(points=np.array([[left_x, left_y], [right_x, left_y],
                                            [right_x, right_y], [left_x, right_y]]),
                           start_index=self._frame.frame_index, class_name=self.class_now[0])
                self.refresh()
            return

        if self.__annotation_state >= 0:
            if key == cv2.EVENT_LBUTTONDOWN:
                self.__label_new = True
                self.__label_new_start_x = x
                self.__label_new_start_y = y
                self.__label_new_end_x = x
                self.__label_new_end_y = y
        else:
            if cv2.EVENT_LBUTTONDOWN == key:
                for t, poly in self.__targets_insight:
                    left = np.min(poly[:, 0])
                    right = np.max(poly[:, 0])
                    top = np.min(poly[:, 1])
                    bottom = np.max(poly[:, 1])
                    if (left <= x <= right) and (top <= y <= bottom):
                        self._selected_target = t
                        self._selected_target_poly[:, :] = poly[:, :]
                        self.refresh()
                        return
                self._selected_target = None
                self.refresh()

            super()._mouse_event(key, x, y, flag, params)

    def _draw_select_target(self, frame, poly_points):
        cv2.polylines(frame, [poly_points], True, self.__classes_color_dict[self._selected_target.class_name], 1, cv2.LINE_AA)

        start, end, flag = self._selected_target.key_frame_flags[self._frame.frame_index]
        self._selected_flag = flag
        # print(start, end, flag)

        for point in poly_points:
            cv2.circle(frame, (point[0, 0], point[0, 1]), 4, self._flag_color[flag], -1)

        if 0 <= self._select_point < len(poly_points):
            point = poly_points[self._select_point]
            cv2.circle(frame, (point[0, 0], point[0, 1]), 5, [0, 255, 0], 2)

    def _draw_targets(self, frame):
        left, top, right, bottom = self._frame.range_rectangle_global
        targets = Target.GetTargetsRange(self._frame.frame_index, top, bottom, left, right)
        self.__targets_insight.clear()
        for target in targets:
            existed, poly_points = target.get_rect_poly(self._frame.frame_index)
            # poly_points = target.rect_poly_points[self._frame.frame_index].copy()
            poly_points[:, 0] -= left
            poly_points[:, 1] -= top
            poly_points *= self._frame.scale
            self.__targets_insight.append([target, poly_points.copy()])
            poly_points = np.around(poly_points)
            poly_points = poly_points.astype('int')
            poly_points = poly_points.reshape((-1, 1, 2))

            if self._selected_target and self._selected_target == target:
                self._draw_select_target(frame, poly_points)
            else:
                if existed:
                    cv2.polylines(frame, [poly_points], True, self.__classes_color_dict[target.class_name], 1,
                                  cv2.LINE_AA)
                else:
                    # 对于不存在的目标显示为暗色
                    cv2.polylines(frame, [poly_points], True, [0, 0, 0], 1, cv2.LINE_AA)

    def _refresh(self):
        frame_image = super()._refresh()
        self._draw_targets(frame_image)
        return frame_image

    def _key_map(self, key):
        label_state = self.__classes_dict.get(key)
        if label_state is not None:
            self._L.info('进入标注模式：%s' % self.__classes[label_state][0])
            self.__annotation_state = label_state
        elif key == ord('0'):
            # exit new label model
            self._L.info('退出标注模式：%s' % self.__classes[self.__annotation_state][0])
            self.__annotation_state = -1
        elif key == 13: # enter
            if self._selected_target and self._selected_flag < 1:
                self._selected_target.set_key_point(self._frame.frame_index)
            self.refresh()
        elif key == 8: # backspace
            if self._selected_target and self._selected_flag == 1:
                self._selected_target.remove_key_point_at(self._frame.frame_index)

        elif key == '_':
            if self._selected_target:
                while True:
                    ans = input('确定要删除该目标[%s]？Y/N' % self._selected_target.name)
                    if ans.strip() == 'Y':
                        Target.RemoveTarget(self._selected_target)
                        break
                    elif ans.strip() == 'N':
                        break

        elif key == ord('t'):

            if self._auto_track is None:
                self._L.info('已开启自动辅助标注!')
                self._auto_track = CVTracker(CVTracker.KCF)
            else:
                del self._auto_track
                self._auto_track = None
                self._L.info('自动辅助标注已关闭!')
        else:
            super()._key_map(key)

