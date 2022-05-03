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
import platform

from bases.targets import Target

try:
    import tkinter as tk

    __screen = tk.Tk()
    DisplayHeight = __screen.winfo_screenheight()
    DisplayWidth = __screen.winfo_screenwidth()
    __screen.destroy()

except ImportError:
    DisplayHeight = -1
    DisplayWidth = -1

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

    AnnotatorWinHeight: int = 0
    AnnotatorWinWidth: int = 0

    TargetClasses: list = []

    StartScale: float = 1.0
    ScaleList: list = None



    _targets_dir = 'targets'

    _cache_data = ''
    _interpolations = []
    _video_info = None

    def __init__(self, image_list):
        self.image_list = image_list
        self.frame_image = None
        self.target_list = []

        self.WinWidth = self.WindowSize[0]
        self.WinHeight = self.WindowSize[1]

        self._selections = [ord('1'), ord('2'), ord('3'), ord('b'), ord('q')]
        self._select_actions = [self._multi_targets_annotations, self._reload,
                                self._make_video, self._judge_keys, self._quit]

        self.font1 = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 15)
        _, self.font1_height = self.font1.getsize('测试高度')
        self.font0 = ImageFont.truetype(VIDEO_TARGET_SELECTOR_FONT_FILE, 30)
        _, self.font0_height = self.font0.getsize('测试高度')

    # def _multi_targets_selection(self):
    def _judge_keys(self):
        return 1

    def _make_video(self):
        return 1

    def _reload(self):
        return 1

    def _quit(self):
        return 0

    def _multi_targets_annotations(self):
        from bases.graphic import AdvancedFrame as Frame
        from tools.fast_annotator import Annotator
        frames = Frame(image_list=self.image_list,
                       width_out=self.AnnotatorWinWidth,
                       height_out=self.AnnotatorWinHeight,
                       start_scale=self.StartScale,
                       zoom_scales=self.ScaleList
                       )
        annotator = Annotator('annotation', font=self.font1, font_height=self.font1_height, classes=self.TargetClasses)
        annotator.set_frame_obj(frames)
        frames.set_frame(0)
        win_loc = self._get_win_center(*frames.frame_out_size)
        annotator.run(window_location=win_loc)
        annotator.destroy()
        return 1

    def _center_text(self, text, font=None, h=None, w=None):
        font = font if font else self.font1
        width, height = font.getsize(text)
        w_center = (self.WinWidth - width) / 2 if w is None else w
        h_center = (self.WinHeight - height) / 2 if h is None else h
        return w_center, h_center

    def _draw_welcome(self):
        im = Image.new("RGB", (self.WindowSize[0], self.WindowSize[1]))  # 生成空白图像
        draw = ImageDraw.Draw(im)  # 绘图句柄
        start_y = self.WinHeight/2 - 250
        start_x = self.WinWidth*0.2 + 50
        welcome_text = u'欢迎使用遥感视觉标注工具 V%s' % VERSION
        x, y = self._center_text(welcome_text, font=self.font0, h=start_y)
        start_y += self.font0_height*2
        draw.text((x, y), welcome_text, font=self.font0)
        l_x, l_y, v_w, v_h = self._video_info['crop_area']
        video_info = [(u'视频名称：', os.path.basename(self._video_info['source_path'])),
                      (u'视频帧数：', '%d (%d fps)' % (self._video_info['frame_count'], self._video_info['fps'])),
                      (u'视频尺寸：', u'宽度 %d, 高度 %d (截取) / 宽度 %d, 高度 %d (原视频)' %
                       (v_w, v_h, self._video_info['width'], self._video_info['height'])),
                      (u'截取坐标：', u'左上 (%d, %d), 右下 (%d, %d)' % (l_x, l_y, l_x+v_w, l_y+v_h)),
                      (u'图像格式：', u'RGB彩色' if self._video_info['is_rgb'] else u'灰度图'),
                      (u'视频编码：', '%s' % self._video_info['fourcc']),
                      (u'目标标注：', u'%d (区域内) / %d (全图总计)' % (100, 200))]

        y_put = 0
        for i, info in enumerate(video_info):
            w, _ = self.font1.getsize(info[0])
            y_put = start_y+self.font1_height*1.5*i
            draw.text((start_x-w, y_put), info[0], font=self.font1)
            draw.text((start_x, y_put), info[1], font=self.font1)

        # 生成缩略图
        small_image = cv2.imread(self.image_list[0])
        y_put = int(y_put + 1.4*self.font0_height)
        v_small_height = 240
        v_small_width = int(v_small_height*v_w/v_h)
        small_image = cv2.resize(small_image, (v_small_width, v_small_height))

        self.frame_image = np.array(im)
        x_small_image_put = int((self.WindowSize[0]-v_small_width)/2)
        self.frame_image[y_put: y_put+v_small_height,
                         x_small_image_put: x_small_image_put+v_small_width, :] = small_image[:]
        return y_put+v_small_height

    def _start_selection_loop(self):
        cv2.setWindowTitle('main', 'Welcome')
        end_y = self._draw_welcome()
        tmp_image = cv2.cvtColor(self.frame_image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(tmp_image)
        draw = ImageDraw.Draw(image)  # 绘图句柄
        start_y = end_y + 20
        text = u'按1进入多目标标注模式，按2重新加载视频，按3制作标注结果视频，按b进入按键调试模式，按q退出工具'
        start_x, start_y = self._center_text(text, self.font1, h=start_y)
        draw.text((start_x, start_y), text, font=self.font1, fill='yellow')
        image_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        del tmp_image
        while True:
            cv2.imshow('main', image_np)
            print(cv2.getWindowImageRect('main'))
            key = cv2.waitKey(1000)
            if key in self._selections:
                break
            cv2.imshow('main', self.frame_image)
            key = cv2.waitKey(500)
            if key in self._selections:
                break
        index = self._selections.index(key)
        cv2.destroyWindow('main')
        return self._select_actions[index]()

    @staticmethod
    def _get_win_center(w, h):
        if DisplayHeight > 0:
            off_x = max(int((DisplayWidth - w) / 2), 0)
            if platform.system() == 'Darwin':
                off_y = 0
            else:
                off_y = max(int((DisplayHeight - h) / 2), 0)
            return off_x, off_y
        return 0, 0

    def run(self):
        selection = True
        while selection:
            cv2.namedWindow('main', flags=cv2.WINDOW_AUTOSIZE)
            off_x, off_y = self._get_win_center(self.WinWidth, self.WinHeight)
            cv2.moveWindow('main', off_x, off_y)
            selection = self._start_selection_loop()

        cv2.destroyAllWindows()

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
            Target.SetLength(len(image_list))
            Target.SetGlobalOffsize(*cls.SelectArea)
            Target.GetAllTargets(cls.SaveToDirectory)

            player.run()
        except KeyError as e:
            cls._L.error('Error Occurred in program! (%s)' % e.args)
            Target.SaveAllTargets()
            # save files automatically
        cls._L.info('Files are saved at: %s' % cls.SaveToDirectory)
        cls._L.info('Exit, good luck!')

if __name__ == '__main__':
    TargetSelector.StartVideo()

