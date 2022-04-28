from common.json_helper import JsonTransBase
from common.logger import LoggerMeta
from logging import Logger
import os
import copy
import hashlib
import time
import numpy as np


class Target(JsonTransBase, metaclass=LoggerMeta):
    _L: Logger = None

    targets_dict = {}
    _seed = ''
    _default_path = ''  # default_path
    _max_length = 0  # sequence length

    _global_off_x = 0
    _global_off_y = 0
    _global_off_xx = 0
    _global_off_yy = 0

    def remove_file(self):
        filename = os.path.join(self._default_path, '%s.meta' % self.name)
        os.remove(filename)
        return filename

    @classmethod
    def RemoveTarget(cls, target):
        t = cls.targets_dict.get(target.name, None)
        if t is None:
            cls._L.info('Target is not existed!')
        else:
            cls.targets_dict.pop(target.name)
            cls._L.info('Target %s is removed with file: %s' % (target.name, target.remove_file()))
            del target

    @classmethod
    def SetGlobalOffsize(cls, off_x, off_y, off_xx, off_yy):
        cls._global_off_x = off_x
        cls._global_off_xx = off_xx
        cls._global_off_y = off_y
        cls._global_off_yy = off_yy

    @classmethod
    def GetTargetsRange(cls, frame_index, top, bottom, left, right):
        target_list = []
        for target in cls.targets_dict:
            t = cls.targets_dict[target]
            if t.is_in_the_range(frame_index, left, right, top, bottom):
                target_list.append(t)
        return target_list

    @classmethod
    def GetAllTargets(cls, path):
        os.makedirs(path, exist_ok=True)
        target_files = [os.path.join(path, i) for i in os.listdir(path) if i.endswith('.meta')]
        left = cls._global_off_x
        right = cls._global_off_xx
        top = cls._global_off_y
        bottom = cls._global_off_yy
        for file in target_files:
            yes = False
            t = Target.MakeNewFromJsonFile(file)
            name, _ = file.strip().split('.')
            for i in range(t.start_index, t.end_index+1):
                if t.is_in_the_range(i, left, right, top, bottom):
                    yes = True
                    break
            if yes:
                cls.targets_dict[name] = t
                t.rect_poly_points -= [cls._global_off_x, cls._global_off_y]
                t.__changed_flag = False
        return len(cls.targets_dict), len(target_files)

    @classmethod
    def SetDefaultSavingPath(cls, path):
        cls._default_path = path

    @classmethod
    def SetTargetSeed(cls, new_seed_str):
        cls._seed = new_seed_str

    @classmethod
    def SetLength(cls, length: int):
        cls._max_length = length

    @classmethod
    def SaveAllTargets(cls):
        for i, key, t in enumerate(cls.targets_dict.items()):
            t.rect_poly_points += [cls._global_off_x, cls._global_off_y]
            if t.__changed_flag:
                t.save_file()
                cls._L.info('[%d/%d] Save target %s -> file: %s' % (i, len(cls.targets_dict), key, t.File))
            else:
                cls._L.info('Skipped unchanged target: %s' % t.File)

    def get_rect_poly(self, frame_index):
        if frame_index > self.end_index:
            return False, self.rect_poly_points[self.end_index].copy()
        elif frame_index < self.start_index:
            return False, self.rect_poly_points[self.start_index].copy()
        else:
            return True, self.rect_poly_points[frame_index].copy()

    def is_in_the_range(self, frame_index, left, right, top, bottom):
        if self.start_index == -1:
            return None

        _, points = self.get_rect_poly(frame_index)

        index_ = (left <= points[:, 0]) & (points[:, 0] <= right) & (top <= points[:, 1]) & (points[:, 1] <= bottom)
        # print(index_)
        return True if np.sum(index_) > 0 else False

    def _rand_name_target(self):
        hash_ = hashlib.md5()
        hash_.update(('%s%.3f' % (self._seed, time.time())).encode('ascii'))
        return hash_.hexdigest()

    def __init__(self):
        assert self._max_length > 0, 'Please initialize sequence length by "Target.SetLength(max_length)"!'
        self.rect_poly_points = -np.ones((self._max_length, 4, 2), dtype='float')
        self.create_timestamp = time.time()
        self.class_name = ''
        self.name = self._rand_name_target()
        self.start_index = -1
        self.end_index = -1
        self.visible_flags = np.zeros(self._max_length, dtype='bool')
        self.key_frame_flags = -np.ones((self._max_length, 3), dtype='int')  # (pre_index, next_index, -1 未知 1 关键帧 0 非关键帧)

        self.__changed_flag = True

    def set_start_poly(self, points, start_index):
        self.rect_poly_points[start_index, :, :] = points[:, :]
        self.start_index = start_index
        self.end_index = start_index
        self.visible_flags[start_index] = True
        self.key_frame_flags[start_index] = [start_index, start_index, 1]
        self.__changed_flag = True

    def move(self, frame_index, dx, dy):
        # self.rect_poly_points[frame_index, :, 0] += dx
        # self.rect_poly_points[frame_index, :, 1] += dy
        poly_points = self.rect_poly_points[frame_index, :, :] + [dx, dy]
        self.set_key_point(frame_index, poly_points)

    @classmethod
    def New(cls, points, start_index, class_name):
        obj = cls()
        obj.set_start_poly(points, start_index)
        obj.class_name = class_name
        cls.targets_dict[obj.name] = obj
        cls._L.info('New target was created! [%s]' % obj.name)
        return obj

    @property
    def File(self):
        return os.path.join(self._default_path, '%s.meta' % self.name)

    def save_file(self, path=None):
        self.Json = path if path else self.File

    def set_key_point(self, frame_index, poly_points=None):
        key = self.key_frame_flags[frame_index, 2]
        if poly_points is None:
            _, poly_points = self.get_rect_poly(frame_index)
        if key == 1:
            self._modify_key_point_at(frame_index, poly_points)
        elif key == 0:
            self._add_key_point_between(frame_index, poly_points)
        elif key == -1:
            self._add_new_key_point(frame_index, poly_points)
        self.__changed_flag = True

    def _add_key_point_between(self, frame_index, poly_points):
        # 在两个关键点之间添加新的关键点
        self.rect_poly_points[frame_index, :] = poly_points
        pre_, next_ = self.key_frame_flags[frame_index, :2]
        self._calculate_frame_between(pre_, frame_index)
        self._calculate_frame_between(frame_index, next_)
        self.key_frame_flags[frame_index, 2] = 1
        self.key_frame_flags[pre_, 1] = frame_index
        self.key_frame_flags[next_, 0] = frame_index

    def _calculate_frame_between(self, start, end, update=True):
        k = end - start
        if k > 1:
            mini = (self.rect_poly_points[end, :] - self.rect_poly_points[start, :]) / k
            for i in range(start+1, end):
                self.rect_poly_points[i, :] = self.rect_poly_points[i-1, :] + mini[:]
                if update:
                    self.key_frame_flags[i, :] = [start, end, 0]

    def _add_new_key_point(self, frame_index, poly_points):
        self.rect_poly_points[frame_index, :, :] = poly_points
        if frame_index > self.end_index:
            self.key_frame_flags[frame_index, :] = [self.end_index, frame_index, 1]
            self.key_frame_flags[self.end_index, 1] = frame_index
            self._calculate_frame_between(self.end_index, frame_index)
            self.visible_flags[self.end_index+1:frame_index+1] = True
            self.end_index = frame_index
        elif frame_index < self.start_index:
            self.key_frame_flags[frame_index, :] = [frame_index, self.start_index, 1]
            self.key_frame_flags[self.start_index, 0] = frame_index
            self._calculate_frame_between(frame_index, self.start_index)
            self.visible_flags[frame_index:self.start_index] = True
            self.start_index = frame_index
        else:
            assert False, 'Program logical error!'

    def _modify_key_point_at(self, frame_index, point):
        self.rect_poly_points[frame_index, :] = point
        pre_, next_ = self.key_frame_flags[frame_index, :2]
        self._calculate_frame_between(pre_, frame_index, False)
        self._calculate_frame_between(frame_index, next_, False)

    def _clear_frame_between(self, start, end):
        for i in range(start+1, end):
            self.rect_poly_points[i, :, :] = -1.0
            self.visible_flags[i] = False
            self.key_frame_flags[i, :] = [-1, -1, -1]

    def remove_key_point_at(self, frame_index):
        pre_, next_, key = self.key_frame_flags[frame_index, :]
        if key == 0:
            self._L.error('帧%d为非关键帧，不支持删除哦!最近的两个关键帧: %d, %d' % (frame_index+1, pre_+1, next_+1))
            return
        if key == -1:
            self._L.error('该目标还没有标注到帧%d哦!' % (frame_index+1))
            return
        if pre_ == next_ == frame_index:
            self._L.error('该目标仅剩下此帧标注框，无法继续删除！')
            return

        if frame_index == pre_:
            self._clear_frame_between(self.start_index-1, next_)
            self.start_index = next_
            self.key_frame_flags[self.start_index, 0] = self.start_index
        elif frame_index == next_:
            self._clear_frame_between(pre_, frame_index+1)
            self.end_index = pre_
            self.key_frame_flags[self.end_index, 1] = self.end_index
        else:
            self._calculate_frame_between(pre_, next_)
        self.__changed_flag = True


# class TargetPoint(JsonTransBase, metaclass=LoggerMeta):
#     _L: Logger = None
#
#     targets_dict = {}
#     _seed = ''
#     _default_path = ''  # default_path
#     _max_length = 0    # sequence length
#
#     # @classmethod
#     # def NewTarget(cls, start_poly, class_name):
#     #     t = cls()
#     #     t.set_start_poly(start_poly)
#     @classmethod
#     def GetTargetsRange(cls, top, bottom, left, right):
#         target_list = []
#         for target in cls.targets_dict:
#             t = cls.targets_dict[target]
#             if t.is_in_the_range(top, bottom, left, right):
#                 target_list.append(t)
#         return target_list
#
#     @classmethod
#     def GetAllTargets(cls, path):
#         target_files = [os.path.join(path, i) for i in os.listdir(path) if i.endswith('.meta')]
#         for file in target_files:
#             t = Target.MakeNewFromJsonFile(file)
#             name, _ = file.strip().split('.')
#             cls.targets_dict[name] = t
#
#     @classmethod
#     def SaveAllTargets(cls):
#         for i, key, t in enumerate(cls.targets_dict.items()):
#             t.save_file()
#             cls._L.info('[%d/%d] Save target %s -> file: %s' % (i, len(cls.targets_dict), key, t.File))
#
#     def _rand_name_target(self):
#         hash_ = hashlib.md5()
#         hash_.update(('%s%.3f' % (self._seed, time.time())).encode('ascii'))
#         return hash_.hexdigest()
#
#     @classmethod
#     def SetDefaultSavingPath(cls, path):
#         cls._default_path = path
#
#     @classmethod
#     def SetTargetSeed(cls, new_seed_str):
#         cls._seed = new_seed_str
#
#     @classmethod
#     def SetLength(cls, length: int):
#         cls._max_length = length
#
#     def __init__(self):
#         assert self._max_length > 0, 'Please initialize sequence length by "Target.SetLength(max_length)"!'
#         self.poly_points = np.zeros((1,), dtype='float')
#         self.create_timestamp = time.time()
#         self.class_name = ''
#         self.rectangle = []
#         self.positions = np.zeros((self._max_length, 2), dtype='float')
#         self.name = self._rand_name_target()
#         self.start_index = -1
#         self.end_index = -1
#         self.visible_flags = np.ones(self._max_length, dtype='bool')
#         self.key_frame = -np.ones((self._max_length, 3), dtype='int')   # (pre_index, next_index, 1/0/-1)
#
#     @classmethod
#     def New(cls, points, start_index, class_name):
#         obj = cls()
#         obj.set_start_poly(points, start_index)
#         obj.class_name = class_name
#         cls.targets_dict[obj.name] = obj
#         cls._L.info('New target was created! [%s]' % obj.name)
#         return obj
#
#     @property
#     def File(self):
#         return os.path.join(self._default_path, '%s.meta' % self.name)
#
#     def save_file(self, path=None):
#         self.Json = path if path else self.File
#
#     def set_start_poly(self, points, start_index):
#         self.poly_points = copy.deepcopy(points)
#         self.start_index = start_index
#         self.end_index = start_index
#         self.rectangle = [np.max(points, axis=0).tolist(), np.max(points, axis=0).tolist()]
#         self.positions[start_index, 0] = (self.rectangle[0][0] + self.rectangle[1][0])/2
#         self.positions[start_index, 1] = (self.rectangle[0][1] + self.rectangle[1][1])/2
#         self.key_frame[start_index, :] = [start_index, start_index, 1]
#         if start_index > 0:
#             self.visible_flags[:start_index-1] = False
#
#     def set_visible_at(self, frame_index, visible):
#         self.visible_flags[frame_index] = visible
#
#     def set_key_point(self, frame_index, point):
#         key = self.key_frame[frame_index, 2]
#         if key == 1:
#             self._modify_key_point_at(frame_index, point)
#         elif key == 0:
#             self._add_key_point_between(frame_index, point)
#         elif key == -1:
#             self._add_new_key_point(frame_index, point)
#
#     def _add_key_point_between(self, frame_index, point):
#         # 在两个关键点之间添加新的关键点
#         self.positions[frame_index, :] = point
#         pre_, next_ = self.key_frame[frame_index, :2]
#         self._calculate_frame_between(pre_, frame_index)
#         self._calculate_frame_between(frame_index, next_)
#         self.key_frame[frame_index, 2] = 1
#         self.key_frame[pre_, 1] = frame_index
#         self.key_frame[next_, 0] = frame_index
#
#     def _calculate_frame_between(self, start, end, update=True):
#         k = end - start
#         if k > 1:
#             mini = (self.positions[end, :] - self.positions[start, :]) / k
#             for i in range(start+1, end):
#                 self.positions[i, :] = self.positions[i-1, :] + mini[:]
#                 if update:
#                     self.key_frame[i, :] = [start, end, 0]
#
#     def _add_new_key_point(self, frame_index, point):
#         self.positions[frame_index, :] = point
#         if frame_index > self.end_index:
#             self.key_frame[frame_index, :] = [self.end_index, frame_index, 1]
#             self.key_frame[self.end_index, 1] = frame_index
#             self._calculate_frame_between(self.end_index, frame_index)
#             self.visible_flags[self.end_index+1:frame_index+1] = True
#             self.end_index = frame_index
#         elif frame_index < self.start_index:
#             self.key_frame[frame_index, :] = [frame_index, self.start_index, 1]
#             self.key_frame[self.start_index, 0] = frame_index
#             self._calculate_frame_between(frame_index, self.start_index)
#             self.visible_flags[frame_index:self.start_index] = True
#             self.start_index = frame_index
#         else:
#             assert False, 'Program logical error!'
#
#     def _modify_key_point_at(self, frame_index, point):
#         self.positions[frame_index, :] = point
#         pre_, next_ = self.key_frame[frame_index, :2]
#         self._calculate_frame_between(pre_, frame_index, False)
#         self._calculate_frame_between(frame_index, next_, False)
#
#     def _clear_frame_between(self, start, end):
#         for i in range(start+1, end):
#             self.positions[i, :] = [-1, -1]
#             self.visible_flags[i] = False
#             self.key_frame[i, :] = [-1, -1, -1]
#
#     def remove_key_point_at(self, frame_index):
#         pre_, next_, key = self.key_frame[frame_index, :]
#         if key == 0:
#             return
#         if pre_ == next_ == frame_index:
#             self.positions[frame_index, :] = -1
#             self.key_frame[frame_index, :] = -1
#             self.visible_flags[frame_index] = False
#             self.start_index = self.end_index = -1
#
#         if frame_index == pre_:
#             self._clear_frame_between(self.start_index-1, next_)
#             self.start_index = next_
#             self.key_frame[self.start_index, 0] = self.start_index
#         elif frame_index == next_:
#             self._clear_frame_between(pre_, frame_index+1)
#             self.end_index = pre_
#             self.key_frame[self.end_index, 1] = self.end_index
#         else:
#             self._calculate_frame_between(pre_, next_)
#
#     def is_in_the_range(self, left, right, top, bottom):
#         if self.start_index == -1:
#             return None
#
#         index_ = (left <= self.positions[:, 0] <= right) & (top <= self.positions[:, 1] <= bottom)
#         return True if np.sum(index_) > 0 else False
#
#     def get_points_range_from(self, left, right, top, bottom):
#         if self.start_index == -1:
#             return None
#
#         index_ = (left <= self.positions[:, 0] <= right) & (top <= self.positions[:, 1] <= bottom)
#         i_index = np.argwhere(index_)
#         return min(i_index), max(i_index)