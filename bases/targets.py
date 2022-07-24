import json

import tqdm

from common.json_helper import JsonTransBase
from common.logger import LoggerMeta
from logging import Logger
import os
import copy
import hashlib
import time
import numpy as np

import datetime


class Target(JsonTransBase, metaclass=LoggerMeta):
    _L: Logger = None

    targets_dict = {}
    total_num_add = 0
    _seed = ''
    _default_path = ''  # default_path
    _max_length = 0  # sequence length

    _global_off_x = 0
    _global_off_y = 0
    _global_off_xx = 0
    _global_off_yy = 0

    auto_save = False
    auto_th = None
    _working = False
    _pause = False

    NOR = 0
    INV = 1
    OCC = 2

    flag_dict = ['[NOR]正常可见', '[INV]与背景混淆难以分辨', '[OCC]遮挡不可见', '[UNK]未标注']
    flag_dict_en = ['Normal', 'Invisible', 'Occlusion', 'Unknown']
    key_frame_flag_dict_en = ['Non-Key Frame', 'Key Frame', 'AI', 'Unlabeled']

    def to_dict(self):
        self.start_index = int(self.start_index)
        self.end_index = int(self.end_index)
        dict_all = super(Target, self).to_dict()
        poly_global = self.rect_poly_points.copy()
        poly_global[self.start_index:self.end_index+1, :] += [self._global_off_x, self._global_off_y]
        dict_all['rect_poly_points'] = poly_global.tolist()
        dict_all['state_flags'] = self.state_flags.tolist()
        dict_all['key_frame_flags'] = self.key_frame_flags.tolist()

        return dict_all

    @classmethod
    def set_pause(cls, pause_value):
        if cls.auto_th is not None:
            if pause_value:
                while cls._working:
                    time.sleep(1.0)
            cls._pause = pause_value

    def from_dict(self, obj_dict):
        super(Target, self).from_dict(obj_dict)
        self.rect_poly_points[self.start_index:self.end_index+1] -= [self._global_off_x, self._global_off_y]

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
        cls.targets_dict.clear()
        os.makedirs(path, exist_ok=True)
        target_files = [os.path.join(path, i) for i in os.listdir(path) if i.endswith('.meta')]
        left = 0
        right = cls._global_off_xx - cls._global_off_x
        top = 0
        bottom = cls._global_off_yy - cls._global_off_y
        targets = tqdm.tqdm(target_files)
        for n, file in enumerate(targets):
            yes = False
            try:
                t = Target.MakeNewFromJsonFile(file)
            except json.decoder.JSONDecodeError as e:
                cls._L.error('Json file error: {}'.format(file))
                continue
            name, _ = file.strip().split('.')
            name = os.path.basename(name)
            for i in range(t.start_index, t.end_index+1):
                if t.is_in_the_range(i, left, right, top, bottom):
                    yes = True
                    break
            if yes:
                cls.targets_dict[name] = t
                t.__changed_flag = False
                targets.write('[OK] %s' % file)
            else:
                targets.write('[NO] %s' % file)
            targets.set_description('Searching...(%d | %d)' % (len(cls.targets_dict), n+1))
        cls.total_num_add = len(target_files) - len(cls.targets_dict)
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
    def SaveAllTargets(cls, pm=None):
        save_n = 0
        err_n = 0
        time_out = 0
        freeze = 0
        unchanged = 0
        while cls._working:
            time.sleep(1000)
            time_out += 1
            if time_out > 10:
                cls._pause = False
            if time_out > 20:
                cls._pause = False
                cls._L.error('Waiting auto thread time out, saving all targets in force manner.')
                break
        cls._pause = True
        for i, (key, t) in enumerate(cls.targets_dict.items()):
            if pm:
                pm.percentage = i / len(cls.targets_dict)
            try:
                if t.__changed_flag:
                    if t.freeze:
                        cls._L.debug('Skipped freeze target: %s' % t.File)
                        freeze += 1
                        unchanged += 1
                    else:
                        t.save_file()
                        t.__changed_flag = False
                        cls._L.info('[%d/%d] Save changed target %s -> file: %s' % (i+1, len(cls.targets_dict), key, t.File))
                        save_n += 1
                else:
                    cls._L.debug('Skipped unchanged target: %s' % t.File)
                    unchanged += 1
            except (TypeError, IOError) as e:
                cls._L.error('Save target error: %s' % t.name)
                cls._L.error(e)
                err_n += 1
                unchanged += 1
            if pm:
                pm.message = '已新保存目标: %d, 无变化被跳过目标： %d (其中包括 - 被冻结：%d个 | 保存出错: %d个)，总计处理: %d个目标' \
                             % (save_n, unchanged, freeze, err_n, len(cls.targets_dict))

        cls._L.info('|= Save All Summary ==> Saved Target: %d, Total: %d, Unchanged: %d (including freeze: %d, Error: %d)'
                    % (save_n, len(cls.targets_dict), unchanged, freeze, err_n))
        cls._pause = False
        if pm:
            pm.return_value = (save_n, unchanged, freeze, err_n, len(cls.targets_dict))
        else:
            return save_n, unchanged, freeze, err_n, len(cls.targets_dict)

    def change_target_class(self, new_class_name):
        if self.class_name != new_class_name:
            self._L.info('修改目标类别为：%s --> %s' % (self.class_name, new_class_name))
            self.class_name = new_class_name
            self.__changed_flag = True
        else:
            self._L.info('当前目标类别未修改')

    def get_nearest_key_frame_rects(self, frame_index):
        if frame_index > self.end_index:
            return self.end_index, -1, self.rect_poly_points[self.end_index].copy(), None
        elif frame_index < self.start_index:
            return -1, self.start_index, None, self.rect_poly_points[self.start_index].copy()
        else:
            before, after, _ = self.key_frame_flags[frame_index]
            if frame_index == self.end_index:
                after = -1
                after_poly = None
            else:
                after_poly = self.rect_poly_points[after].copy()

            if frame_index == self.start_index:
                before = -1
                before_poly = None
            else:
                before_poly = self.rect_poly_points[before].copy()
            return before, after, before_poly, after_poly

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
        self.state_flags = -np.ones(self._max_length, dtype='int')
        self.key_frame_flags = -np.ones((self._max_length, 3), dtype='int')  # (pre_index, next_index, -1 未知 1 关键帧 0 非关键帧 2 自动帧)

        self.__changed_flag = True
        self.__freeze = False

    @property
    def freeze(self):
        return True if self.__freeze else False

    @freeze.setter
    def freeze(self, value: bool):
        self.__freeze = value

    @property
    def freeze_msg(self):
        return self.__freeze

    def copy(self, freeze=False):
        obj = Target()
        if freeze:
            obj.freeze = 'making copy...'
        obj.rect_poly_points = self.rect_poly_points.copy()
        obj.class_name = self.class_name
        obj.start_index = self.start_index
        obj.end_index = self.end_index
        obj.state_flags = self.state_flags.copy()
        obj.key_frame_flags = self.key_frame_flags.copy()
        self.targets_dict[obj.name] = obj
        self._L.info('Copy target from [%s], new one is [%s].' % (self.name, obj.name))
        return obj

    def show_target_abs(self):
        
        abstract = """
                      ========== Target Abstract ===========
                        ID: %s
                        Class: %s
                        Start Frame: %d
                        End Frame: %d
                        Created Time: %s
                      ======================================
                   """ % (self.name, self.class_name, self.start_index + 1, self.end_index+1, datetime.datetime.fromtimestamp(self.create_timestamp).strftime("%Y-%m-%d %H:%M:%S.%f"))
        self._L.info(abstract)

    def set_start_poly(self, points, start_index):
        self.rect_poly_points[start_index, :, :] = points[:, :]
        self.start_index = start_index
        self.end_index = start_index
        self.state_flags[start_index] = self.NOR
        self.key_frame_flags[start_index] = [-1, -1, 1]
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

    def set_object_state(self, from_index, state, to_index=-1):
        if to_index < 0:
            self.state_flags[from_index] = state
            self._L.info('Set frame flag %s at frame %d' % (self.flag_dict[state], from_index))
            self.__changed_flag = True
        elif to_index > from_index:
            self.state_flags[from_index: to_index] = state
            self._L.info('Set frame flag %s from frame %d to frame %d' % (self.flag_dict[state], from_index, to_index))
            self.__changed_flag = True
        else:
            self._L.error('from_index must be less than to_index! from_index={}, to_index={}'
                          .format(from_index, to_index))

    @property
    def File(self):
        return os.path.join(self._default_path, '%s.meta' % self.name)

    def save_file(self, path=None):
        # self.rect_poly_points += [self._global_off_x, self._global_off_y]
        self.Json = path if path else self.File

    def set_key_point(self, frame_index, poly_points=None, refresh=True):
        key = self.key_frame_flags[frame_index, 2]
        if poly_points is None:
            if key == 1:
                return
            _, poly_points = self.get_rect_poly(frame_index)
            if key == 2:
                self._add_key_point_between(frame_index, poly_points)
                if refresh:
                    self.__changed_flag = True
                return

        if key == 1:
            self._modify_key_point_at(frame_index, poly_points)
        elif key == 0:
            self._add_key_point_between(frame_index, poly_points)
        elif key == -1:
            self._add_new_key_point(frame_index, poly_points)
        elif key == 2:
            # 自动帧则无需修改周边帧
            self._modify_key_point_at(frame_index, poly_points, False)
        if refresh:
            self.__changed_flag = True

    def set_auto_key_points(self, indexes, rects):
        if self.key_frame_flags[indexes[-1], 2] == -1:
            x, y, w, h = rects[-1]
            self._add_new_key_point(indexes[-1], [[x, y], [x+w, y], [x+w, y+h], [x, y+h]], False)

        for index, rect in zip(indexes[1:-1], rects[1:-1]):
            self.rect_poly_points[index, [0, 3], 0] = rect[0]
            self.rect_poly_points[index, [0, 1], 1] = rect[1]
            self.rect_poly_points[index, [1, 2], 0] = rect[0] + rect[2]
            self.rect_poly_points[index, [2, 3], 1] = rect[1] + rect[3]
            self.key_frame_flags[index, 2] = 2
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
            if self.key_frame_flags[start+1, 2] == 2 or self.key_frame_flags[end-1, 2] == 2:
                # 随便测试其中一帧的flag 如果是自动帧 则不修改
                if update:
                    for i in range(start + 1, end):
                        self.key_frame_flags[i, :] = [start, end, 2]
            else:
                mini = (self.rect_poly_points[end, :] - self.rect_poly_points[start, :]) / k
                for i in range(start+1, end):
                    self.rect_poly_points[i, :] = self.rect_poly_points[i-1, :] + mini[:]
                    if update:
                        self.key_frame_flags[i, :] = [start, end, 0]

    def _add_new_key_point(self, frame_index, poly_points, auto_animation=True):
        self.rect_poly_points[frame_index, :, :] = poly_points
        if frame_index > self.end_index:
            self.key_frame_flags[frame_index, :] = [self.end_index, -1, 1]
            self.key_frame_flags[self.end_index, 1] = frame_index
            if auto_animation:
                self._calculate_frame_between(self.end_index, frame_index)
            else:
                self.key_frame_flags[self.end_index+1:frame_index, :] = [self.end_index, frame_index, 0]
            self.state_flags[self.end_index+1:frame_index] = self.state_flags[self.end_index]
            self.state_flags[frame_index] = self.NOR
            self.end_index = frame_index
        elif frame_index < self.start_index:
            self.key_frame_flags[frame_index, :] = [frame_index, self.start_index, 1]
            self.key_frame_flags[self.start_index, 0] = frame_index
            if auto_animation:
                self._calculate_frame_between(frame_index, self.start_index)
            else:
                self.key_frame_flags[frame_index+1:self.start_index, :] = [frame_index, self.start_index, 0]
            self.state_flags[frame_index:self.start_index] = self.NOR
            self.start_index = frame_index
        else:
            print(frame_index, self.start_index, self.end_index)
            assert False, 'Program logical error!'

    def _modify_key_point_at(self, frame_index, point, with_side=True):
        self.rect_poly_points[frame_index, :] = point
        if with_side:
            pre_, next_ = self.key_frame_flags[frame_index, :2]
            self._calculate_frame_between(pre_, frame_index, False)
            self._calculate_frame_between(frame_index, next_, False)

    def _clear_frames_at(self, range_list):
        self.rect_poly_points[range_list, :, :] = -1.0
        self.state_flags[range_list] = -1
        self.key_frame_flags[range_list, :] = [-1, -1, -1]

    def _clear_frames(self, start, end):
        self.rect_poly_points[start:end, :, :] = -1.0
        self.state_flags[start:end] = -1
        self.key_frame_flags[start:end, :] = [-1, -1, -1]

    def delete_auto_frames_at(self, frame_index):
        pre_, next_, key = self.key_frame_flags[frame_index]
        if key == 2:
            self._clear_auto_frames_between(pre_, next_)
            self.__changed_flag = True

    def _clear_auto_frames_between(self, start, end):
        self.key_frame_flags[start+1: end, 2] = 0
        self._calculate_frame_between(start, end)

    def remove_key_point_at(self, frame_index):
        pre_, next_, key = self.key_frame_flags[frame_index, :]
        if key == 0:
            self._L.error('帧%d为非关键帧，不支持删除哦!最近的两个关键帧: %d, %d' % (frame_index+1, pre_+1, next_+1))
            return
        if key == -1:
            self._L.error('该目标还没有标注到帧%d哦!' % (frame_index+1))
            return
        if self.start_index == self.end_index == frame_index:
            self._L.error('该目标仅剩下此帧标注框，无法继续删除，您可以按delete删除该目标！')
            return

        if frame_index == self.start_index:
            self._clear_frames(self.start_index, next_)
            self.start_index = int(next_)
            self.key_frame_flags[self.start_index, 0] = -1
        elif frame_index == self.end_index:
            self._clear_frames(pre_+1, frame_index+1)
            self.end_index = int(pre_)
            self.key_frame_flags[self.end_index, 1] = -1
        else:
            self._calculate_frame_between(pre_, next_)
            self.key_frame_flags[pre_, 1] = next_
            self.key_frame_flags[next_, 0] = pre_
            self.set_object_state(pre_, self.state_flags[pre_], next_)
            
        self.__changed_flag = True
    
    def remove_after_frame(self, index):
        if self.start_index <= index < self.end_index:
            self.set_key_point(index, refresh=False)
            self._clear_frames(index+1, self.end_index+1)
            self.key_frame_flags[index, 1] = -1
            self.end_index = index
            self.__changed_flag = True

    def remove_before_frame(self, index):
        if self.start_index < index <= self.end_index:
            self.set_key_point(index, refresh=False)
            self._clear_frames(self.start_index, index)
            self.key_frame_flags[index, 0] = -1
            self.start_index = index
            self.__changed_flag = True

    @classmethod
    def auto_saving_thread_func(cls, detect_delay=10000):
        """
        此线程最好使用消息队列信号机制，减少没有必要的遍历开销
        """
        import time
        _delay = int(round(detect_delay / 1000))
        cls.auto_save = True
        cls._L.info('Auto save thread start! detect_delay == %d mm' % detect_delay)
        while cls.auto_save:
            for _ in range(_delay):
                time.sleep(1.0)
                while cls._pause:
                    time.sleep(1.0)
                if not cls.auto_save:
                    break
            cls._working = True
            if not cls.auto_save:
                cls._working = False
                break
            for target in cls.targets_dict:
                t: cls = cls.targets_dict[target]
                if t.__changed_flag and not t.freeze:
                    try:
                        t.save_file()
                        t.__changed_flag = False
                        t._L.info('Autosaved: %s' % t.name)
                    except (IOError, TypeError) as e:
                        cls._L.error('Save target error: %s' % t.name)
                        cls._L.error(e)
            cls._working = False
        cls._L.info('Auto save thread exit!')

    @classmethod
    def start_auto(cls, detect_delay=10000):
        import threading
        if cls.auto_th is None:
            cls.auto_th = threading.Thread(name='auto_saving', target=cls.auto_saving_thread_func, daemon=True,
                                           kwargs={'detect_delay': detect_delay})
            cls.auto_th.start()

        else:
            cls._L.error('You have opened the auto saving thread!')

    @classmethod
    def stop_auto(cls):
        if cls.auto_th is not None:
            cls.auto_save = False
            cls._L.info('Stopping auto-saving thread...')
            cls.auto_th.join()
            cls._L.info('Auto-saving thread has been stopped!')
            cls.auto_th = None
        else:
            cls._L.error('Auto-saving thread was not started yet!')

    @classmethod
    def merge_target(cls, target_a, target_b, frame_index):
        """
        target_a从frame_index开始往后添加target_b的关键帧
        """
        assert isinstance(target_a, cls)
        assert isinstance(target_b, cls)
        assert target_b.class_name == target_a.class_name

        if target_b.end_index <= frame_index:
            cls._L.error('无效的合并，由于选择的第二个目标的end_index比当前插入的位置小！')
            return None

        obj = target_a.copy()
        obj.remove_after_frame(frame_index)

        insert_index = target_b.start_index
        if target_b.start_index <= frame_index:
            insert_index = frame_index + 1
            _, next_, key = target_b.key_frame_flags[insert_index]

            if key != 1:
                insert_index = next_
            # target_b.remove_before_frame(insert_index)

        obj.set_key_point(insert_index, target_b.rect_poly_points[insert_index])
        start = insert_index + 1
        if start > target_b.end_index:
            pass
        else:
            end = target_b.end_index+1
            obj.rect_poly_points[start: end] = target_b.rect_poly_points[start: end]
            obj.key_frame_flags[start: end] = target_b.key_frame_flags[start: end]
            obj.state_flags[start: end] = target_b.state_flags[start: end]
            obj.end_index = target_b.end_index
            obj.key_frame_flags[insert_index, 1] = target_b.key_frame_flags[insert_index, 1]

        cls.RemoveTarget(target_a)
        cls.RemoveTarget(target_b)
        obj.frseeze = ''
        return obj

    def get_center_point(self, index):
        return np.average(self.rect_poly_points[index], axis=0)

    def get_route(self, start_index=None, end_index=None):
        start_index = self.start_index if start_index is None else max(start_index, self.start_index)
        end_index = self.end_index if end_index is None else min(end_index, self.end_index)
        polys: np.ndarray = self.rect_poly_points[start_index: end_index+1]
        center_points = np.average(polys, axis=1)
        return center_points

    def get_route_indexes(self, indexes):
        polys = self.rect_poly_points[indexes]
        center_points = np.average(polys, axis=1)
        return center_points


def normalizing_targets(path):
    """
    将上一版本中所有目标转换为标准格式，以防止出现迭代bug
    """
    target_files = [os.path.join(path, i) for i in os.listdir(path) if i.endswith('.meta')]
    error = []
    for file in target_files:
        try:
            target = Target.MakeNewFromJsonFile(file)
            target.rect_poly_points[:target.start_index, :] = -1
            target.rect_poly_points[target.end_index+1:] = -1
            target.key_frame_flags[target.end_index, 1] = -1
            target.key_frame_flags[target.start_index, 0] = -1
            target.save_file(file)

        except Exception as e:
            print('ERROR--> %s' % file)
            error.append(file)
            continue
    return error


def get_all_targets_max_range(path):
    import math
    target_files = [os.path.join(path, i) for i in os.listdir(path) if i.endswith('.meta')]
    left = []
    right = []
    bottom = []
    top = []
    cls = {}
    error = 0
    for file in target_files:
        try:
            target = Target.MakeNewFromJsonFile(file)
        except Exception as e:
            print('ERROR--> %s' % file)
            error += 1
            continue

        if cls.get(target.class_name, None) is None:
            cls[target.class_name] = 1
        else:
            cls[target.class_name] += 1
        polys = target.rect_poly_points[target.start_index: target.end_index+1]
        points = polys.reshape((-1, 2))
        right.append(float(np.max(points[:, 0])))
        left.append(float(np.min(points[:, 0])))
        bottom.append(float(np.max(points[:, 1])))
        top.append(float(np.min(points[:, 1])))
    print(path)
    print('--> cls: {}'.format(cls))
    print('--> Range: left {}, right {}, top {}, bottom {}'.format(math.floor(min(left)), math.ceil(max(right)),
                                                                   math.floor(min(top)), math.ceil(max(bottom))))

    return cls, error, math.floor(min(left)), math.ceil(max(right)), math.floor(min(top)), math.ceil(max(bottom))
