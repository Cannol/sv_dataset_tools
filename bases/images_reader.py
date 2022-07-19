import sys
import cv2

from collections import OrderedDict

from logging import Logger
from common.logger import LoggerMeta


class ImageSeqReader(object, metaclass=LoggerMeta):

    _L: Logger = None

    def __init__(self, image_files_list, cache_max_memory):
        """
        image_files_list: image file paths
        cache_max_memory: unit is MB
        """
        assert len(image_files_list) > 0
        self._image_cache = OrderedDict()
        self._image_files = image_files_list

        self._total_memory = 0
        self._max_memory = int(cache_max_memory * 1024 * 1024)   # 转换为字节

    def _read(self, index):
        image_file = self._image_files[index]
        img = cv2.imread(image_file)
        if img is None:
            raise FileNotFoundError(image_file)
        img_size = sys.getsizeof(img)
        while self._total_memory + img_size > self._max_memory:
            if not self._image_cache:
                self._L.warning('您设置的缓存最大空间小于单帧图像的存储，缓冲区无效！（缓冲区最大：%.2f MB，单帧约为：%.2f MB）'
                                % (self._max_memory/1024/1024, img_size/1024/1024))
                return img
            index_, img_obj = self._image_cache.popitem(False)
            self._total_memory -= sys.getsizeof(img_obj)
            self._L.debug('推出帧: %d (mem: %d / %d)' % (index_, self._total_memory, self._max_memory))
        self._image_cache[index] = img
        self._total_memory += img_size
        self._L.debug('放入帧: %d (mem: %d / %d)' % (index, self._total_memory, self._max_memory))
        return img

    def __len__(self):
        return len(self._image_cache)

    def __sizeof__(self):
        return self._total_memory

    def __str__(self):
        return "%.2f MB / %.2f MB" % (self._total_memory/1024/1024, self._max_memory/1024/1024)

    def __getitem__(self, item):
        # assert isinstance(item, int)
        img = self._image_cache.get(int(item), None)
        if img is None:
            img = self._read(item)
        return img.copy()


