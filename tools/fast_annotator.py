from re import T
import cv2
import numpy as np
from bases.graphic import WorkCanvas
from bases.targets import Target
from common import LoggerMeta
from logging import Logger
from bases.trackers import TrackingResult, TrackerRunner
from bases.key_mapper import KeyMapper


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
        self._selected_target_to_merge_poly = np.zeros((4, 2), dtype='float')
        self._selected_target_poly_before = None
        self._selected_target_poly_after = None
        self._selected_target_poly_before_index = -1
        self._selected_target_poly_after_index = -1
        self._select_point = -1
        self._selected_flag = -1
        self._selected_frame_flag = -1

        self._show_rect_keyframe = True
        self._show_black_rect = True
        self._show_select_rect = True
        self._show_select_center_dot = True
        self._show_other_center_dots = True
        self._solo_mode = False

        self._start_move_point = False
        self._start_drag_target = False
        self._drag_x = 0
        self._drag_y = 0
        self._point_drag_x = 0
        self._point_drag_y = 0
        self._drag_slow_mode = False
        self._merge_mode = False
        self._selected_target_to_merge = None

        self._object_state = -1

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
        self.__fake_classes_color_dict = {}
        for class_item in self.__classes:
            self.__classes_color_dict[class_item[0]] = class_item[1]
            self.__fake_classes_color_dict[class_item[0]] = [int(i*0.6) for i in class_item[1]]

        super().__init__(win_name, font, font_height)

    @property
    def class_now(self):
        if self.__annotation_state < 0:
            return None
        return self.__classes[self.__annotation_state]

    def _mouse_event(self, key, x, y, flag, params):
        if self._merge_mode:
            if key == cv2.EVENT_LBUTTONDOWN:
                for t, poly in self.__targets_insight:
                    left = np.min(poly[:, 0])
                    right = np.max(poly[:, 0])
                    top = np.min(poly[:, 1])
                    bottom = np.max(poly[:, 1])
                    if (left <= x <= right) and (top <= y <= bottom):
                        if self._selected_target_to_merge == t:
                            return
                        self._selected_target_to_merge = t
                        self.refresh()
                        return
            elif self._selected_target_to_merge is None and key == cv2.EVENT_MOUSEMOVE:
                frame_ = self._frame_show.copy()
                point = np.average(self._selected_target_poly, axis=0)
                cv2.line(frame_, pt1=(int(point[0]), int(point[1])), pt2=(x, y), color=(0, 74, 125),
                         thickness=2, lineType=cv2.LINE_AA)
                self._quick_show(frame_)

            super()._mouse_event(key, x, y, flag, params)
            return

        if self._selected_target:
            # print(key, flag, cv2.EVENT_LBUTTONDOWN, cv2.EVENT_FLAG_CTRLKEY)
            if key == cv2.EVENT_LBUTTONDOWN and flag == (cv2.EVENT_FLAG_CTRLKEY+key):
                if self._selected_target.freeze:
                    self.message_box('当前目标AI正在跟踪中，无法修改位置和大小，请等待状态改变后再尝试！')
                    return
                self._start_drag_target = True
                self._drag_x = x
                self._drag_y = y
                return

            elif self._start_drag_target and key == cv2.EVENT_MOUSEMOVE and flag == (cv2.EVENT_FLAG_CTRLKEY+1):
                # the left_button_down state mouse has flag == 1
                dx = x - self._drag_x
                dy = y - self._drag_y
                if self._drag_slow_mode:
                    self._selected_target_poly += [dx/10, dy/10]
                else:
                    self._selected_target_poly += [dx, dy]
                self._tmp_frame = self._frame.frame
                selected_poly = self._selected_target_poly.astype('int').reshape((-1, 1, 2))
                self._draw_nearest_key_frames(self._tmp_frame, False)
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
                    self._point_drag_x = x
                    self._point_drag_y = y
                    return

                elif self._start_move_point and key == cv2.EVENT_MOUSEMOVE:
                    if self._drag_slow_mode:
                        dx = (x - self._point_drag_x)/10
                        dy = (y - self._point_drag_y)/10
                    else:
                        dx = x - self._point_drag_x
                        dy = y - self._point_drag_y
                    self._selected_target_poly[self._select_point, 0] += dx
                    self._selected_target_poly[self._select_point, 1] += dy
                    if self._select_point == 0:
                        self._selected_target_poly[1, 1] += dy
                        self._selected_target_poly[3, 0] += dx
                    elif self._select_point == 1:
                        self._selected_target_poly[0, 1] += dy
                        self._selected_target_poly[2, 0] += dx
                    elif self._select_point == 2:
                        self._selected_target_poly[1, 0] += dx
                        self._selected_target_poly[3, 1] += dy
                    else:
                        self._selected_target_poly[0, 0] += dx
                        self._selected_target_poly[2, 1] += dy
                    self._tmp_frame = self._frame.frame
                    poly_points = self._selected_target_poly.astype('int')
                    poly_points = poly_points.reshape((-1, 1, 2))
                    self._draw_select_target(self._tmp_frame, poly_points)
                    self._quick_show(self._tmp_frame)
                    self._point_drag_x = x
                    self._point_drag_y = y
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

            if (not self._start_move_point) and key == cv2.EVENT_MOUSEMOVE and not self._selected_target.freeze:
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
                # return

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
            if key == cv2.EVENT_MOUSEMOVE:
                width, height = self._frame.frame_out_size
                frame_ = self._frame_show.copy()
                cv2.line(frame_, pt1=(x, 0), pt2=(x, height), color=(125, 125, 125), thickness=1, lineType=cv2.LINE_AA)
                cv2.line(frame_, pt1=(0, y), pt2=(width, y), color=(125, 125, 125), thickness=1, lineType=cv2.LINE_AA)
                self._quick_show(frame_)

            elif key == cv2.EVENT_LBUTTONDOWN:
                self.__label_new = True
                self.__label_new_start_x = x
                self.__label_new_start_y = y
                self.__label_new_end_x = x
                self.__label_new_end_y = y
            # if key == cv2.EVENT_MOUSEMOVE:
            #     cv2.circle()
        else:
            if cv2.EVENT_LBUTTONDOWN == key:

                if self._selected_target and self._show_rect_keyframe:
                    if self._selected_target_poly_before is not None:
                        if self._selected_target_poly_before[0, 0] <= x <= self._selected_target_poly_before[2, 0] and \
                           self._selected_target_poly_before[0, 1] <= y <= self._selected_target_poly_before[2, 1]:
                            self._frame.set_frame(self._selected_target_poly_before_index)
                            self.refresh()
                            return

                    if self._selected_target_poly_after is not None:
                        if self._selected_target_poly_after[0, 0] <= x <= self._selected_target_poly_after[2, 0] and \
                                self._selected_target_poly_after[0, 1] <= y <= self._selected_target_poly_after[2, 1]:
                            self._frame.set_frame(self._selected_target_poly_after_index)
                            self.refresh()
                            return

                for t, poly in self.__targets_insight:
                    left = np.min(poly[:, 0])
                    right = np.max(poly[:, 0])
                    top = np.min(poly[:, 1])
                    bottom = np.max(poly[:, 1])
                    if (left <= x <= right) and (top <= y <= bottom):
                        if self._selected_target == t:
                            return
                        self._selected_target = t
                        self.refresh()
                        return

            if cv2.EVENT_RBUTTONDOWN == key:
                if self._selected_target is not None:
                    self._selected_target = None
                    self._selected_target_poly_before = None
                    self._selected_target_poly_after = None
                    self.refresh()
                    return
                # else:
                # super()._mouse_event(key, x, y, flag, params)
                # return
            super(Annotator, self)._mouse_event(key, x, y, flag, params)

    def _draw_select_target(self, frame, poly_points):
        flag = self._selected_target.key_frame_flags[self._frame.frame_index, 2]
        color = [200, 200, 200] if flag == 2 else self.__classes_color_dict[self._selected_target.class_name]
        if self._show_select_rect:
            cv2.polylines(frame, [poly_points], True, color, 1, cv2.LINE_AA)
        state = self._selected_target.state_flags[self._frame.frame_index]
        self._draw_target_state(frame, poly_points, state, color)

        self._selected_flag = int(flag)
        self._selected_frame_flag = self._selected_target.state_flags[self._frame.frame_index]

        for point in poly_points:
            cv2.circle(frame, (point[0, 0], point[0, 1]), 4, self._flag_color[flag], -1)

        if 0 <= self._select_point < len(poly_points):
            point = poly_points[self._select_point]
            cv2.circle(frame, (point[0, 0], point[0, 1]), 5, [0, 255, 0], 2)

    def _draw_select_target_once(self, frame, target, poly_points):
        flag = target.key_frame_flags[self._frame.frame_index, 2]
        color = [200, 200, 200] if flag == 2 else self.__classes_color_dict[target.class_name]
        if self._show_select_rect:
            cv2.polylines(frame, [poly_points], True, color, 1, cv2.LINE_AA)
        state = target.state_flags[self._frame.frame_index]
        self._draw_target_state(frame, poly_points, state, color)

    @staticmethod
    def __calculate_points_between(start_index, end_index, start_point, end_point):
        k = end_index - start_index
        points = np.zeros((k+1, 2), dtype='float')
        points[0][:] = start_point[:]
        points[-1][:] = end_point[:]
        if k > 1:
            mini = (end_point - start_point) / k
            for i in range(1, k):
                points[i, :] = points[i - 1, :] + mini[:]
        return points

    @staticmethod
    def _draw_target_state(frame, target_poly, state, color):
        if state > Target.NOR:
            cv2.line(frame, target_poly[0, 0], target_poly[2, 0], color, 1, cv2.LINE_AA)
        if state > Target.INV:
            cv2.line(frame, target_poly[1, 0], target_poly[3, 0], color, 1, cv2.LINE_AA)

    # def _draw_nearst_key_frames_lines(self, frame):
    #     color = self.__fake_classes_color_dict[self._selected_target.class_name]
    #     now_index = self._frame.frame_index
    #     target = self._selected_target
    #
    #     if self._show_rect_keyframe:
    #         for poly_points, index in [(self._selected_target_poly_before, self._selected_target_poly_before_index),
    #                                    (self._selected_target_poly_after, self._selected_target_poly_after_index)]:
    #             if poly_points is None:
    #                 continue
    #             poly_points = np.around(poly_points)
    #             poly_points = poly_points.astype('int')
    #             poly_points = poly_points.reshape((-1, 1, 2))
    #             cv2.polylines(frame, [poly_points], True, color, 1, cv2.LINE_AA)
    #
    #             state = self._selected_target.state_flags[index]
    #             self._draw_target_state(frame, poly_points, state, color)

    def _draw_routine(self, frame, target, start, end):
        cps = target.get_route(start, end)
        # color = get_color_randomly()
        left, top, _, _ = self._frame.range_rectangle_global
        cps[:, 0] -= left
        cps[:, 1] -= top
        cps *= self._frame.scale
        cps = cps.astype('int')
        cps = cps.reshape((-1, 1, 2))
        cv2.polylines(frame, [cps], False, [100, 23, 90], 1, lineType=cv2.LINE_AA)

    def _draw_nearest_key_frames(self, frame, points=True):
        color = self.__fake_classes_color_dict[self._selected_target.class_name]
        now_index = self._frame.frame_index
        target = self._selected_target

        if self._show_rect_keyframe:
            for poly_points, index in [(self._selected_target_poly_before, self._selected_target_poly_before_index),
                                       (self._selected_target_poly_after, self._selected_target_poly_after_index)]:
                if poly_points is None:
                    continue
                poly_points = np.around(poly_points)
                poly_points = poly_points.astype('int')
                poly_points = poly_points.reshape((-1, 1, 2))
                cv2.polylines(frame, [poly_points], True, color, 1, cv2.LINE_AA)

                state = self._selected_target.state_flags[index]
                self._draw_target_state(frame, poly_points, state, color)

        # draw points between [before, curr] and between [curr, after]
        # print(self._selected_target_poly_before_index, self._frame.frame_index, self._selected_target_poly_after_index)
        center_point_curr = np.average(self._selected_target_poly, axis=0)
        # print(self._selected_target_poly)
        if self._show_other_center_dots:
            if points:
                start = now_index if self._selected_target_poly_before is None else self._selected_target_poly_before_index
                end = now_index if self._selected_target_poly_after is None else self._selected_target_poly_after_index

                left, top, _, _ = self._frame.range_rectangle_global
                indexes = list(range(start, end+1))
                # print(indexes)
                # print(now_index)
                indexes.remove(now_index)

                if len(indexes) > 0:
                    points_sides = target.get_route_indexes(indexes)
                    points_sides[:, 0] -= left
                    points_sides[:, 1] -= top
                    points_sides *= self._frame.scale

                    for i in range(len(points_sides)):
                        cv2.circle(frame, (int(points_sides[i, 0]), int(points_sides[i, 1])), 2, color, -1)
            else:
                if self._selected_target_poly_before is not None:
                    center_point = np.average(self._selected_target_poly_before, axis=0)
                    cv2.line(frame, (int(center_point_curr[0]), int(center_point_curr[1])),
                             (int(center_point[0]), int(center_point[1])),
                             self.__classes_color_dict[self._selected_target.class_name], 1, lineType=cv2.LINE_AA)
                if self._selected_target_poly_after is not None:
                    center_point = np.average(self._selected_target_poly_after, axis=0)
                    cv2.line(frame, (int(center_point_curr[0]), int(center_point_curr[1])),
                             (int(center_point[0]), int(center_point[1])),
                             self.__classes_color_dict[self._selected_target.class_name], 1, lineType=cv2.LINE_AA)

            # if self._selected_target_poly_before is not None:
            #
            #     center_point_before = np.average(self._selected_target_poly_before, axis=0)
            #     points_before = self.__calculate_points_between(self._selected_target_poly_before_index, self._frame.frame_index,
            #                                              center_point_before, center_point_curr).astype('int')
            #     # points = points.astype('int')
            #     for i in range(len(points_before)-1):
            #         cv2.circle(frame, (points_before[i, 0], points_before[i, 1]), 2, color, -1)
            #
            # if self._selected_target_poly_after is not None:
            #     center_point_after = np.average(self._selected_target_poly_after, axis=0)
            #     points_after = self.__calculate_points_between(self._frame.frame_index, self._selected_target_poly_after_index,
            #                                              center_point_curr, center_point_after).astype('int')
            #     for i in range(1, len(points_after)):
            #         cv2.circle(frame, (points_after[i, 0], points_after[i, 1]), 2, color, -1)

        if self._show_select_center_dot:
            cv2.circle(frame, (int(center_point_curr[0]), int(center_point_curr[1])), 2, self.__classes_color_dict[self._selected_target.class_name], -1)

    def _draw_targets(self, frame):

        left, top, right, bottom = self._frame.range_rectangle_global

        if self._solo_mode and self._selected_target:
            self.__targets_insight.clear()
            targets = [self._selected_target]
        else:
            targets = Target.GetTargetsRange(self._frame.frame_index, top, bottom, left, right)
            self.__targets_insight.clear()

        for target in targets:
            existed, poly_points = target.get_rect_poly(self._frame.frame_index)
            if self._merge_mode:
                if (target.class_name != self._selected_target.class_name or target.end_index <= self._frame.frame_index) \
                        and self._selected_target != target:
                    continue
            # poly_points = target.rect_poly_points[self._frame.frame_index].copy()
            poly_points[:, 0] -= left
            poly_points[:, 1] -= top
            poly_points *= self._frame.scale
            # self.__targets_insight.append([target, poly_points.copy()])
            poly_points_ori = poly_points.copy()
            
            poly_points = np.around(poly_points)
            poly_points = poly_points.astype('int')
            poly_points = poly_points.reshape((-1, 1, 2))

            if self._selected_target and self._selected_target == target:
                self.__targets_insight.append([target, poly_points_ori])

                (self._selected_target_poly_before_index, self._selected_target_poly_after_index,
                 self._selected_target_poly_before, self._selected_target_poly_after) = \
                    target.get_nearest_key_frame_rects(self._frame.frame_index)
                if self._selected_target_poly_before is not None:
                    self._selected_target_poly_before[:, 0] -= left
                    self._selected_target_poly_before[:, 1] -= top
                    self._selected_target_poly_before *= self._frame.scale
                if self._selected_target_poly_after is not None:
                    self._selected_target_poly_after[:, 0] -= left
                    self._selected_target_poly_after[:, 1] -= top
                    self._selected_target_poly_after *= self._frame.scale
                self._selected_target_poly[:, :] = self.__targets_insight[-1][1][:, :]
                self._draw_nearest_key_frames(frame)
                self._draw_select_target(frame, poly_points)
            elif self._merge_mode and self._selected_target_to_merge and target == self._selected_target_to_merge:
                self.__targets_insight.append([target, poly_points_ori])
                self._draw_select_target_once(frame, target, poly_points)
                self._selected_target_to_merge_poly = poly_points[:, 0, :]
            else:
                if existed:
                    self.__targets_insight.append([target, poly_points_ori])
                    cv2.polylines(frame, [poly_points], True, self.__classes_color_dict[target.class_name], 1,
                                  cv2.LINE_AA)
                elif self._show_black_rect:
                    # 对于不存在的目标显示为暗色
                    self.__targets_insight.append([target, poly_points_ori])
                    cv2.polylines(frame, [poly_points], True, [0, 0, 0], 1, cv2.LINE_AA)
        if self._merge_mode:
            self._draw_routine(frame, self._selected_target, None, self._frame.frame_index)
            if self._selected_target_to_merge:
                self._draw_routine(frame, self._selected_target_to_merge, self._frame.frame_index, None)

                point1 = np.average(self._selected_target_poly, axis=0)
                point2 = np.average(self._selected_target_to_merge_poly, axis=0)
                cv2.arrowedLine(frame, pt1=(int(point1[0]), int(point1[1])), pt2=(int(point2[0]), int(point2[1])),
                                color=(0, 74, 125), thickness=2, line_type=cv2.LINE_AA)

    def _refresh(self):
        frame_image = super()._refresh()
        self._draw_targets(frame_image)

        if self.__annotation_state >= 0:
            label_text = 'Labeling... %s' % self.__classes[self.__annotation_state][0]
            cv2.putText(frame_image, label_text, (20, 45), 0, 0.5, (255, 255, 255), 1, lineType=cv2.LINE_AA)

        elif self._selected_target:
            target_text = 'Target_ID: %s' % self._selected_target.name
            cv2.putText(frame_image, target_text, (20, 45), 0, 0.5, (255, 255, 255), 1, lineType=cv2.LINE_AA)

            target_state = 'State: %s (%s)' % (Target.flag_dict_en[self._selected_frame_flag],
                                               Target.key_frame_flag_dict_en[self._selected_flag])
            cv2.putText(frame_image, target_state, (20, 70), 0, 0.5, (255, 255, 255), 1, lineType=cv2.LINE_AA)
            target_class = 'Class: %s' % self._selected_target.class_name
            cv2.putText(frame_image, target_class, (20, 95), 0, 0.5, (255, 255, 255), 1, lineType=cv2.LINE_AA)
        else:
            static_text = 'Labeled Targets: %d [Global: %d, RoI: %d]' \
                          % (len(Target.targets_dict),
                             len(Target.targets_dict)+Target.total_num_add,
                             len(self.__targets_insight))
            cv2.putText(frame_image, static_text, (20, 45), 0, 0.5, (255, 255, 255), 1, lineType=cv2.LINE_AA)

        return frame_image

    def _set_state_flag(self, new_flag):
        if self._selected_target is not None:
            if self._selected_flag == 1:
                self._selected_target.set_object_state(
                    self._frame.frame_index, new_flag, self._selected_target_poly_after_index)
            elif self._selected_flag == -1:
                self._L.error('此处没有创建关键帧，因此无法修改帧状态属性值，请创建关键帧后再操作！')
            elif self._selected_flag == 0:
                self._L.warning('由于处于非关键帧，操作将会修改上一个关键帧到下一个关键帧之间所有帧属性')
                self._selected_target.set_object_state(
                    self._selected_target_poly_before_index, new_flag, self._selected_target_poly_after_index
                )

    def receive_auto_results(self, result: TrackingResult):
        target: Target = Target.targets_dict.get(result.target_id, None)
        if target:
            if result.result_polys is None:
                self._L.info('[自动跟踪] 目标%s，尝试自动跟踪 %d帧 ~ %d帧, 失败！'
                             % (result.target_id, result.indexes[0]+1, result.indexes[-1]+1))
            else:
                target.set_auto_key_points(result.indexes, result.result_polys)
                self._L.info('[自动跟踪] 目标%s，成功更新帧: %d ~ %d'
                             % (result.target_id, result.indexes[0]+1, result.indexes[-1]+1))
            target.freeze = ''
            self.refresh()
        else:
            self._L.info('[自动跟踪] 由于目标%s已被移除，自动跟踪结果无效丢弃！' % result.target_id)

    def send_auto_track_task(self, target: Target, index: int, track_after: bool=True):
        pre_, next_, flag = target.key_frame_flags[index]

        if flag == 0:
            self._L.info('[自动跟踪] 非关键帧--自动跟踪从上一关键帧%d到下一关键帧%d'
                         % (pre_+1, next_+1))
            indexes = list(range(pre_, next_+1))
            ref_polys = [target.get_rect_poly(pre_)[1], target.get_rect_poly(next_)[1]]

        elif flag == 2:
            if self.ask_message('该目标从第%d帧至第%d帧已经存在自动跟踪的记录，是否重新跟踪？' % (pre_+1, next_+1)):
                indexes = list(range(pre_, next_ + 1))
                ref_polys = [target.get_rect_poly(pre_)[1], target.get_rect_poly(next_)[1]]
            else:
                return False

        elif flag == 1:
            if track_after:
                if next_ == -1:
                    self._L.info('[自动跟踪] 后一关键帧不存在！自动尝试向后跟踪10帧')
                    indexes = list(range(index, self._frame.valid_frame_index(index+10)+1))
                    ref_polys = [target.get_rect_poly(index)[1]]
                else:
                    self._L.info('[自动跟踪] 关键帧--自动跟踪至下一个关键帧%d' % (next_+1))
                    indexes = list(range(index, next_ + 1))
                    ref_polys = [target.get_rect_poly(index)[1], target.get_rect_poly(next_)[1]]
            else:
                if self._selected_target_poly_before is None:
                    self._L.info('[自动跟踪] 前一关键帧不存在！自动尝试向前跟踪10帧')
                    indexes = list(range(index, self._frame.valid_frame_index(index-10)-1, -1))
                    ref_polys = [target.get_rect_poly(index)[1]]
                else:
                    self._L.info('[自动跟踪] 关键帧--自动跟踪至上一个关键帧%d' % (pre_+1))
                    indexes = list(range(pre_, index+1))
                    ref_polys = [target.get_rect_poly(pre_)[1], target.get_rect_poly(index)[1]]
        else:
            self.message_box('目标还未标记至此处，无法启动自动标注！(该目标有效范围：%d - %d)'
                             % (target.start_index+1, target.end_index+1))
            return False

        if len(ref_polys) > 1 and len(indexes) <= 2:
            self.message_box('没有能跟踪的非关键帧，输入无效！')
            return False

        if len(ref_polys) == 1 and len(indexes) == 1:
            self.message_box('已经到达尽头，无法继续向前或向后跟踪！')
            return False

        flag = target.key_frame_flags[indexes[1], 2]
        if flag == 2:
            if self.ask_message('该目标从第%d帧至第%d帧已经存在自动跟踪的记录，是否重新跟踪？' % (indexes[0] + 1, indexes[-1] + 1)):
                pass
            else:
                return False

        target.freeze = '自动跟踪进行中...'
        TrackerRunner.AddTask(target_id=target.name,
                              indexes=indexes,
                              ref_polys=ref_polys,
                              enlarge=5,
                              scale=10)
        self._L.info('成功添加自动跟踪任务: %s - %s' % (self._selected_target.name, str(indexes)))
        return True

    def _key_map(self, key):
        # print(key)
        label_state = self.__classes_dict.get(key)
        if label_state is not None:
            if self._selected_target is None:
                self._L.info('进入标注模式：%s' % self.__classes[label_state][0])
                self.__annotation_state = label_state
            else:
                self._selected_target.change_target_class(self.__classes[label_state][0])

        elif key == ord('0'):
            # exit new label model
            self._L.info('退出标注模式：%s' % self.__classes[self.__annotation_state][0])
            self.__annotation_state = -1

        elif key == KeyMapper.ESC:
            if self._merge_mode:
                self._merge_mode = False
                self._selected_target_to_merge = None
                key = -99999
            if self._selected_target:
                self._selected_target = None
                key = -99999
            elif self.__annotation_state >= 0:
                self._L.info('退出标注模式：%s' % self.__classes[self.__annotation_state][0])
                self.__annotation_state = -1
                key = -99999
        
        elif key == KeyMapper.ENTER:  # enter
            if self._merge_mode:
                if self._selected_target_to_merge:
                    if self.ask_message('准备合并目标%s和%s，是否继续？' % (self._selected_target.name, self._selected_target_to_merge.name)):
                        target_new = Target.merge_target(target_a=self._selected_target,
                                                         target_b=self._selected_target_to_merge,
                                                         frame_index=self._frame.frame_index)
                        if target_new:
                            self.message_box('合并目标成功，新目标名称为: %s' % target_new.name)
                            self._selected_target = target_new
                        else:
                            self.message_box('目标合并失败！')
                        self._merge_mode = False
                else:
                    self.message_box('缺少被合并的另一个目标，请选择被合并的目标后再按回车确认。')
            else:
                if self._selected_target and self._selected_flag in [-1, 0, 2]:
                    if self._selected_target.freeze:
                        self.message_box('目标正在被AI跟踪，请不要修改！')
                    else:
                        self._selected_target.set_key_point(self._frame.frame_index)

        elif key == KeyMapper.BACK_SPACE:  # backspace
            if self._selected_target:
                if self._selected_target.freeze:
                    self.message_box('目标正处于AI跟踪中，请勿修改此目标！')
                else:
                    self._selected_target.remove_key_point_at(self._frame.frame_index)
        elif key == KeyMapper.DEL or key == ord('-'):
            if self._selected_target:
                target = self._selected_target
                while True:
                    ans = self.ask_message(message='确定要删除该目标[%s]？' % target.name, ok_key=ord('y'), cancel_key=ord('n'), ok_key_name='y', cancel_key_name='n')
                    if ans:
                        Target.set_pause(True)
                        Target.RemoveTarget(target)
                        self._selected_target = None
                        Target.set_pause(False)
                        break
                    else:
                        return
        elif key == KeyMapper.BLANK_SPACE:
            self._solo_mode = not self._solo_mode

        elif key == ord('b'):
            self._show_black_rect = not self._show_black_rect

        elif key == ord('v'):
            self._show_rect_keyframe = not self._show_rect_keyframe

        elif key == ord('c'):
            self._show_select_rect = not self._show_select_rect

        elif key == ord('n'):
            self._show_select_center_dot = not self._show_select_center_dot

        elif key == ord('m'):
            self._show_other_center_dots = not self._show_other_center_dots

        elif key == ord('q'):
            if self._selected_target and self._selected_target_poly_before is not None:
                self._frame.set_frame(self._selected_target_poly_before_index)
        
        elif key == ord('w'):
            if self._selected_target and self._selected_target_poly_after is not None:
                self._frame.set_frame(self._selected_target_poly_after_index)

        elif key == ord(','):
            self._set_state_flag(Target.NOR)

        elif key == ord('.'):
            self._set_state_flag(Target.INV)
        elif key == ord('/'):
            self._set_state_flag(Target.OCC)

        elif key == ord('`'):
            res = self.progress_bar(Target.SaveAllTargets)
            # res = Target.SaveAllTargets()
            self.message_box('保存完毕，新保存目标%d个，错误%d个，跳过被冻结目标%d个！' % (res[0], res[2], res[3]))

        elif key == ord('i'):
            if self._selected_target:
                self._selected_target.show_target_abs()
            return

        elif key == ord('e'):
            self._drag_slow_mode = not self._drag_slow_mode
            return

        elif key == ord('o'):
            if self._selected_target and self._selected_flag >= 0:
                if self._selected_target.freeze:
                    self.message_box('目标正在被AI跟踪，请不要修改！')
                elif self.ask_message('确定要删除此目标往前（不包括当前帧）的所有帧吗？'):
                    self._selected_target.remove_before_frame(self._frame.frame_index)
            else:
                return

        elif key == ord('p'):
            if self._selected_target and self._selected_flag >= 0:
                if self._selected_target.freeze:
                    self.message_box('目标正在被AI跟踪，请不要修改！')
                elif self.ask_message('确定要删除此目标往后（不包括当前帧）的所有帧吗？'):
                    self._selected_target.remove_after_frame(self._frame.frame_index)
            else:
                return

        elif key == ord('u'):
            if self._merge_mode:
                self.message_box('您已经处于合并目标状态下！')
                return
            if self._selected_target:
                if self._selected_target.freeze:
                    self.message_box('目标正在被AI跟踪，请不要修改！')
                else:
                    self._selected_target_to_merge = None
                    self._selected_target_to_merge_poly = None
                    self._merge_mode = True
            else:
                self.message_box('抱歉！您没有选中任何目标，无法开始目标合并。请先选择一个起始目标再按此按键！')
                return

        elif key == ord('t'):
            if self._selected_target:
                if not self.send_auto_track_task(target=self._selected_target,
                                                 index=self._frame.frame_index,
                                                 track_after=False):
                    return
            else:
                return

        elif key == ord('y'):
            if self._selected_target:
                if not self.send_auto_track_task(target=self._selected_target,
                                                 index=self._frame.frame_index):
                    return
            else:
                return
        elif key == ord('k'):
            if self._selected_target:
                if self._selected_target.freeze:
                    self.message_box('目标正在被AI跟踪，请不要修改！')
                else:
                    if self._selected_flag == 2:
                        self._selected_target.delete_auto_frames_at(self._frame.frame_index)
                    else:
                        self.message_box('当前帧不是AI帧，无法清楚该段自动跟踪的结果！')

        super()._key_map(key)

