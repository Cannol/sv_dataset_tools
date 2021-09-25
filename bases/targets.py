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

    _targets_dict = {}
    _seed = ''
    _default_path = ''  # default_path
    _max_length = 0    # sequence length

    @classmethod
    def GetAllTargets(cls, path):
        target_files = [os.path.join(path, i) for i in os.listdir(path) if i.endswith('.meta')]
        for file in target_files:
            t = Target.MakeNewFromJsonFile(file)
            name, _ = file.strip().split('.')
            cls._targets_dict[name] = t

    @classmethod
    def SaveAllTargets(cls):
        for i, key, t in enumerate(cls._targets_dict.items()):
            t.save_file()
            cls._L.info('[%d/%d] Save target %s -> file: %s' % (i, len(cls._targets_dict), key, t.File))

    def _rand_name_target(self):
        hash_ = hashlib.md5()
        hash_.update(('%s%.3f' % (self._seed, time.time())).encode('ascii'))
        return hash_.hexdigest()

    @classmethod
    def SetDefaultSavingPath(cls, path):
        cls._default_path = path

    @classmethod
    def SetTargetSeed(cls, new_seed_str):
        cls._seed = new_seed_str

    @classmethod
    def SetLength(cls, length: int):
        cls._max_length = length

    def __init__(self):
        assert self._max_length > 0, 'Please initialize sequence length by "Target.SetLength(max_length)"!'
        self.poly_points = np.zeros((1,), dtype='float')
        self.create_timestamp = time.time()
        self.rectangle = []
        self.positions = -np.ones((self._max_length, 2), dtype='float')
        self.name = self._rand_name_target()
        self.start_index = -1
        self.end_frame = -1
        self.visible_flags = np.ones(self._max_length, dtype='bool')
        self.key_frame = -np.ones((self._max_length, 3), dtype='int')   # (pre_index, next_index, 1/0/-1)

    @classmethod
    def New(cls, points, start_index):
        obj = cls()
        obj.set_start_poly(points, start_index)
        cls._targets_dict[obj.name] = obj
        cls._L.info('New target was created! [%s]' % obj.name)
        return obj

    @property
    def File(self):
        return os.path.join(self._default_path, '%s.meta' % self.name)

    def save_file(self, path=None):
        self.Json = path if path else self.File

    def set_start_poly(self, points, start_index):
        self.poly_points = copy.deepcopy(points)
        self.start_index = start_index
        self.end_frame = start_index
        self.rectangle = [np.max(points, axis=0).tolist(), np.max(points, axis=0).tolist()]
        self.positions[start_index, 0] = (self.rectangle[0][0] + self.rectangle[1][0])/2
        self.positions[start_index, 1] = (self.rectangle[0][1] + self.rectangle[1][1])/2
        self.key_frame[start_index, :] = [start_index, start_index, 1]
        if start_index > 0:
            self.visible_flags[:start_index-1] = False

    def set_visible_at(self, frame_index, visible):
        self.visible_flags[frame_index] = visible

    def set_key_point(self, frame_index, point):
        key = self.key_frame[frame_index, 2]
        if key == 1:
            self._modify_key_point_at(frame_index, point)
        elif key == 0:
            self._add_key_point_between(frame_index, point)
        elif key == -1:
            self._add_new_key_point(frame_index, point)

    def _add_key_point_between(self, frame_index, point):
        # 在两个关键点之间添加新的关键点
        self.positions[frame_index, :] = point
        pre_, next_ = self.key_frame[frame_index, :2]
        self._calculate_frame_between(pre_, frame_index)
        self._calculate_frame_between(frame_index, next_)
        self.key_frame[frame_index, 2] = 1
        self.key_frame[pre_, 1] = frame_index
        self.key_frame[next_, 0] = frame_index

    def _calculate_frame_between(self, start, end, update=True):
        k = end - start
        if k > 1:
            mini = (self.positions[end, :] - self.positions[start, :]) / k
            for i in range(start+1, end):
                self.positions[i, :] = self.positions[i-1, :] + mini[:]
                if update:
                    self.key_frame[i, :] = [start, end, 0]

    def _add_new_key_point(self, frame_index, point):
        self.positions[frame_index, :] = point
        if frame_index > self.end_frame:
            self.key_frame[frame_index, :] = [self.end_frame, frame_index, 1]
            self.key_frame[self.end_frame, 1] = frame_index
            self._calculate_frame_between(self.end_frame, frame_index)
            self.visible_flags[self.end_frame+1:frame_index+1] = True
            self.end_frame = frame_index
        elif frame_index < self.start_index:
            self.key_frame[frame_index, :] = [frame_index, self.start_index, 1]
            self.key_frame[self.start_index, 0] = frame_index
            self._calculate_frame_between(frame_index, self.start_index)
            self.visible_flags[frame_index:self.start_index] = True
            self.start_index = frame_index
        else:
            assert False, 'Program logical error!'

    def _modify_key_point_at(self, frame_index, point):
        self.positions[frame_index, :] = point
        pre_, next_ = self.key_frame[frame_index, :2]
        self._calculate_frame_between(pre_, frame_index, False)
        self._calculate_frame_between(frame_index, next_, False)

    def _clear_frame_between(self, start, end):
        for i in range(start+1, end):
            self.positions[i, :] = [-1, -1]
            self.visible_flags[i] = False
            self.key_frame[i, :] = [-1, -1, -1]

    def remove_key_point_at(self, frame_index):
        pre_, next_, key = self.key_frame[frame_index, :]
        if key == 0:
            return
        if pre_ == next_ == frame_index:
            self.positions[frame_index, :] = -1
            self.key_frame[frame_index, :] = -1
            self.visible_flags[frame_index] = False
            self.start_index = self.end_frame = -1

        if frame_index == pre_:
            self._clear_frame_between(self.start_index-1, next_)
            self.start_index = next_
            self.key_frame[self.start_index, 0] = self.start_index
        elif frame_index == next_:
            self._clear_frame_between(pre_, frame_index+1)
            self.end_frame = pre_
            self.key_frame[self.end_frame, 1] = self.end_frame
        else:
            self._calculate_frame_between(pre_, next_)

    def get_points_range_from(self, left, right, top, bottom):
        if self.start_index == -1:
            return None

        index_ = (left <= self.positions[:, 0] <= right) & (top <= self.positions[:, 1] <= bottom)
        i_index = np.argwhere(index_)
        return min(i_index), max(i_index)