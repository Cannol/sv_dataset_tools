import os
import cv2
import numpy as np
from configs import VIDEO_TARGET_SELECTOR_CONFIG_FILE, VIDEO_TARGET_SELECTOR_FONT_FILE
from common.yaml_helper import YamlConfigClassBase
from common.json_helper import SaveToFile, ReadFromFile
from common.logger import LoggerMeta
from logging import Logger
import hashlib
import tqdm
import struct
import shutil
from PIL import Image, ImageFont, ImageDraw

VERSION = '1.0 beta'


class TargetSelector(YamlConfigClassBase, metaclass=LoggerMeta):
    _L: Logger = None

    VideoFilePath: str = ''
    ImageSequence: str = ''
    SelectArea: list = [0, 0, 0, 0]

    SaveToDirectory: str = ''  # label result save path

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

        self.WinWidth = self.WindowSize[0]
        self.WinHeight = self.WindowSize[1]

        self._selections = [ord('1'), ord('2'), ord('b'), ord('q')]

        self.font1 = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 15)
        _, self.font1_height = self.font1.getsize('测试高度')
        self.font0 = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 30)
        _, self.font0_height = self.font0.getsize('测试高度')

    # def _multi_targets_selection(self):
    #

    def _center_text(self, text, font=None, h=None, w=None):
        font = font if font else self.font1
        width, height = font.getsize(text)
        w_center = (self.WinWidth - width) / 2 if w is None else w
        h_center = (self.WinHeight - height) / 2 if h is None else h
        return w_center, h_center

    def _draw_welcome(self):
        im = Image.new("RGB", (self.WindowSize[0], self.WindowSize[1]))  # 生成空白图像
        draw = ImageDraw.Draw(im)  # 绘图句柄
        start_y = self.WinHeight/2 - 200
        start_x = self.WinWidth*0.2 + 50
        welcome_text = u'欢迎使用遥感视觉标注工具 V%s' % VERSION
        x, y = self._center_text(welcome_text, font=self.font0, h=start_y)
        start_y += self.font0_height*2
        draw.text((x, y), welcome_text, font=self.font0)
        l_x, l_y, v_w, v_h = self._video_info['crop_area']
        video_info = [(u'视频名称：', os.path.basename(self._video_info['source_path'])),
                      (u'视频帧数：', '%d' % self._video_info['frame_count']),
                      (u'视频尺寸：', u'宽度 %d, 高度 %d' % (v_w, v_h)),
                      (u'来源坐标：', u'左上 (%d, %d), 右下 (%d, %d)' % (l_x, l_y, l_x+v_w, l_y+v_h)),
                      (u'图像格式：', u'RGB彩色' if self._video_info['is_rgb'] else u'灰度图'),
                      (u'原视频编码方式：', '%s' % self._video_info['fourcc'])]
        for i, info in enumerate(video_info):
            w, _ = self.font1.getsize(info[0])
            y_put = start_y+self.font1_height*1.5*i
            draw.text((start_x-w, y_put), info[0], font=self.font1)
            draw.text((start_x, y_put), info[1], font=self.font1)

        self.frame_image = np.array(im)

    def _start_selection_loop(self):
        cv2.setWindowTitle('main', 'Welcome')
        self._draw_welcome()
        image = Image.fromarray(self.frame_image)
        draw = ImageDraw.Draw(image)  # 绘图句柄
        start_y = self.WinHeight / 2 + 200
        text = u'按1进入多目标框选模式，按2进入单目标精调模式，按b进入按键调试模式，按q退出工具'
        start_x, start_y = self._center_text(text, self.font1, h=start_y)
        draw.text((start_x, start_y), text, font=self.font1, fill='yellow')
        image_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        while True:
            cv2.imshow('main', image_np)
            key = cv2.waitKey(1000)
            if key in self._selections:
                break
            cv2.imshow('main', self.frame_image)
            key = cv2.waitKey(500)
            if key in self._selections:
                break
        if key == self._selections[-1]:
            return 0
        return key

    def run(self):
        cv2.namedWindow('main', flags=cv2.WINDOW_AUTOSIZE)

        selection = self._start_selection_loop()
        while selection:
            selection = self._start_selection_loop()

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
                      'frames': frames,
                      'crop_area': [x1, y1, x2-x1, y2-y1]
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
                      'frames': frames,
                      'crop_area': [x1, y1, x2 - x1, y2 - y1]
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

