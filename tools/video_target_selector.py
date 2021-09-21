import os
import cv2
import numpy as np
from configs import VIDEO_TARGET_SELECTOR_CONFIG_FILE, VIDEO_TARGET_SELECTOR_FONT_FILE
from common.yaml_helper import YamlConfigClassBase
from common.json_helper import JsonTransBase, SaveToFile, ReadFromFile
from common.logger import LoggerMeta
from logging import Logger
import hashlib
import copy
import tqdm
import struct
import shutil
import time
from PIL import Image, ImageFont, ImageDraw

VERSION = '1.0 beta'


class Target(JsonTransBase, metaclass=LoggerMeta):
    _L: Logger = None

    _targets_dict = {}
    _seed = ''
    _default_path = ''
    _max_length = 0

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
            cls._L.info('[%d/%d] Save target %s -> file: %s' % (i ,len(cls._targets_dict), key, t.File))

    def _rand_name_target(self):
        hash_ = hashlib.md5()
        hash_.update(('%s%.3f' % (self._seed, time.time())).encode('ascii'))
        return hash_.hexdigest()

    @classmethod
    def Seed(cls, seed_str):
        cls._seed = seed_str

    @classmethod
    def Length(cls, length: int):
        cls._max_length = length

    def __init__(self):
        assert self._max_length > 0, 'Please initialize sequence length by "obj.Length(max_length)"!'
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


class TargetSelector(YamlConfigClassBase, metaclass=LoggerMeta):
    _L: Logger = None

    VideoFilePath: str = ''
    ImageSequence: str = ''
    SelectArea: list = [0, 0, 0, 0]
    # AreaFormat: str = ''     # xywh or xyxy
    SaveToDirectory: str = ''

    WindowSize: list = [0, 0]  # width, height
    VideoFormat: list = []
    CacheDirectory: str = ''
    CacheImage: str = ''

    ErrorFrame: str = ''

    _cache_data = ''
    _interpolations = []
    _video_info = None

    def __init__(self, image_list):
        self.image_list = image_list
        self.frame_image = None
        self.index = -1
        self.target_list = []

    def _refresh(self):
        pass

    def _draw_welcome(self):
        font = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 10)  # 使用自定义的字体，第二个参数表示字符大小
        im = Image.new("RGB", (self.WindowSize[0], self.WindowSize[1]))  # 生成空白图像
        draw = ImageDraw.Draw(im)  # 绘图句柄
        x, y = (0, 0)  # 初始左上角的坐标
        draw.text((x, y), '这是一个测试文本1231231231245abcdefg', font=font)  # 绘图
        # offsetx, offsety = font.getoffset('3')  # 获得文字的offset位置
        # width, height = font.getsize('3')  # 获得文件的大小
        self.frame_image = np.zeros((self.WindowSize[0], self.WindowSize[1]), dtype='uint8')

    def run(self):
        # print('55556666')
        # cv2.namedWindow('gogogo', flags=cv2.WINDOW_NORMAL)
        # print('!')
        # cv2.setWindowTitle('gogogo', 'Welcome')
        self._draw_welcome()
        cv2.imshow('gogogo', self.frame_image)
        cv2.waitKey(0)

        # while True:
        #     self._refresh()

    @classmethod
    def _DoWithErrorFrame(cls, i, frames):
        if i == 0 or i == len(frames) or cls.ErrorFrame == 'skip':
            return
        elif cls.ErrorFrame == 'interpolation':
            cls._interpolations.append(i)
            return
        elif cls.ErrorFrame == 'stop':
            pass
        else:
            cls._L.error('Error setting "ErrorFrame" value, it should be in [skip, interpolation, stop].')
            cls._L.info('Using default value: stop')
        raise IOError('Early ending at frame: %d' % (i + 1))

    @classmethod
    def _ReadVideo(cls, start_from_index=0):
        cap = cv2.VideoCapture(cls.VideoFilePath)
        x1, y1, x2, y2 = cls.SelectArea

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames = ['%06d%s' % (i+1, cls.CacheImage) for i in range(frame_count)]

        video_info = {'source_path': cls.VideoFilePath,
                      'fourcc': struct.pack('i', int(cap.get(cv2.CAP_PROP_FOURCC))).decode('ascii'),
                      'fps': int(cap.get(cv2.CAP_PROP_FPS)),
                      'frame_count': frame_count,
                      'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                      'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                      'is_rgb': not bool(cap.get(cv2.CAP_PROP_CONVERT_RGB)),
                      'frames': frames
                      }

        json_path = os.path.join(cls._cache_data, 'source_file.json')
        SaveToFile(json_path, video_info, True, 'Video information is writen to json file: %s' % json_path)
        cls._L.info('Using cache directory: %s' % cls._cache_data)

        progress = tqdm.tqdm(range(frame_count))
        change = []
        for i in progress:
            name = frames[i]
            ret, frame = cap.read()
            if ret == 0:
                cls._DoWithErrorFrame(i, frames)
                progress.set_description('Error occurred in reading frame (mode: %s): %d' % (cls.ErrorFrame, i+1))
                change.append(i)
                continue
            if i >= start_from_index:
                path = os.path.join(cls._cache_data, name)
                progress.set_description('Caching frame to image: %s' % name)
                cv2.imwrite(path, frame[y1:y2, x1:x2])
            else:
                progress.set_description('Skipping image: %s' % name)

        for index in change[::-1]:
            frames.pop(index)
        if len(change) > 0:
            video_info['frame_count'] = len(frames)
            SaveToFile(json_path, video_info, True, 'Video information is rewritten to json file: %s' % json_path)
        cls._L.info('Caching files successfully!')
        cls._video_info = video_info

    @classmethod
    def _ReadImages(cls, start_from_index=0):
        img_list = [os.path.join(cls.VideoFilePath, i)
                    for i in os.listdir(cls.VideoFilePath) if i.endswith(cls.ImageSequence)]
        img_list.sort()
        x1, y1, x2, y2 = cls.SelectArea
        frame_count = len(img_list)
        if frame_count <= 0:
            raise FileNotFoundError('Cannot read any (%s) file in directory: %s'
                                    % (cls.ImageSequence, cls.VideoFilePath))
        tmp = cv2.imread(img_list[0])
        if tmp is None:
            raise IOError('Error reading image: %s' % img_list[0])

        frames = ['%06d%s' % (i+1, cls.CacheImage) for i in range(frame_count)]
        height, width, channel = tmp.shape
        video_info = {'source_path': cls.VideoFilePath,
                      'fourcc': 'MJPG',
                      'fps': 10,
                      'frame_count': frame_count,
                      'width': width,
                      'height': height,
                      'is_rgb': channel == 3,
                      'frames': frames
                      }

        json_path = os.path.join(cls._cache_data, 'source_file.json')
        SaveToFile(json_path, video_info, True, 'Video information is writen to json file: %s' % json_path)
        cls._L.info('Using cache directory: %s' % cls._cache_data)

        progress = tqdm.tqdm(range(frame_count))
        for i in progress:
            name = frames[i]
            if i >= start_from_index:
                image_file = img_list[i]
                frame = cv2.imread(image_file)
                if frame is None:
                    raise IOError('Read file error (return None): %s' % image_file)
                path = os.path.join(cls._cache_data, name)
                progress.set_description('Caching frame to image: %s' % name)
                cv2.imwrite(path, frame[y1:y2, x1:x2])
            else:
                progress.set_description('Skipping image: %s' % name)
        cls._L.info('Caching files successfully!')

    @classmethod
    def _CheckingCache(cls):
        video_info = ReadFromFile(os.path.join(cls._cache_data, 'source_file.json'))
        if video_info is None:
            cls._L.error('Detected source_file.json missing, try rebuild the cache directory!')
            shutil.rmtree(cls._cache_data)
            os.makedirs(cls._cache_data)
            return 0

        for i, image_name in enumerate(video_info['frames']):
            image_file = os.path.join(cls._cache_data, image_name)
            if not os.path.exists(image_file):
                cls._L.error('Detected frame missing, try restore from source file. (break from frame %d)' % (i+1))
                return i
        cls._L.info('Congratulations! All frames have passed checking!')
        cls._video_info = video_info
        return -1

    @classmethod
    def LoadData(cls):
        h = hashlib.md5()
        h.update(('%s%d%d%d%d' % (cls.VideoFilePath,
                                 cls.SelectArea[0], cls.SelectArea[1], cls.SelectArea[2], cls.SelectArea[3])).encode())
        hash_file = h.hexdigest()
        cls._cache_data = os.path.join(cls.CacheDirectory, hash_file)
        index = 0
        if os.path.exists(cls._cache_data):
            index = cls._CheckingCache()
            if index < 0:
                return

        if os.path.exists(cls.VideoFilePath):
            if os.path.isfile(cls.VideoFilePath) and cls.VideoFilePath.endswith(tuple(cls.VideoFormat)):
                cls._ReadVideo(start_from_index=index)
            elif os.path.isdir(cls.VideoFilePath):
                cls._ReadImages(start_from_index=index)
            else:
                cls._L.error('Load data error! Wrong video path configuration. (%s)' % cls.VideoFilePath)
                raise IOError('Read file or dir: %s' % cls.VideoFilePath)
        else:
            cls._L.error('Load data error! Path not exist. (%s)' % cls.VideoFilePath)
            raise FileExistsError(cls.VideoFilePath)

    @classmethod
    def StartVideo(cls):
        cls._L.info('Running Target Selector Version %s, Welcome!' % VERSION)
        cls.Load(VIDEO_TARGET_SELECTOR_CONFIG_FILE)
        cls._L.info('Loaded configuration file from: %s' % VIDEO_TARGET_SELECTOR_CONFIG_FILE)

        try:
            cls._L.info('Loading data...')
            cls.LoadData()
            cls._L.info('Data loaded successfully!')
            image_list = [os.path.join(cls._cache_data, i)
                          for i in cls._video_info['frames']]
            player = cls(image_list)
            player.run()
        except Exception as e:
            cls._L.error('Error Occurred in program! (%s)' % e.args)
            # save files automatically
        cls._L.info('Files are saved at: %s' % cls.SaveToDirectory)
        cls._L.info('Exit, good luck!')

if __name__ == '__main__':
    TargetSelector.StartVideo()

