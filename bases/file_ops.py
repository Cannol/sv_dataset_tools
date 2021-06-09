from common import GLogger
import numpy as np
import cv2
import os

logger = GLogger.get('base.FileOperators', 'FileOperators')


def read_state_file(state_filename):
    state = np.loadtxt(state_filename, delimiter=",", dtype='int32')
    logger.debug('Read state file from: %s' % state_filename)
    return state


def write_state_file(state_file, np_array):
    try:
        np.savetxt(state_file, np_array, '%d', delimiter=",")
        logger.debug('Save state file to: %s' % state_file)
        return True
    except Exception as e:
        logger.error(e)
        return False


class Attr(object):
    def __init__(self, attrs_file):
        self.file = attrs_file
        self.attrs = []
        self.read_attrs()

    def read_attrs(self):
        with open(self.file) as f:
            lines = f.readlines()[0].strip()
        attrs_value = lines.split(',')
        self.attrs = list(map(int, attrs_value))
        logger.debug('Read attribute file from: %s' % self.file)

    def save_attrs(self, new_attrs):
        if new_attrs == self.attrs:
            pass
        else:
            a = []
            for item in new_attrs:
                a.append('1' if item else '0')
            a = ','.join(a)
            with open(self.file, 'w') as f:
                f.write(a)
            logger.info('-> Attr update: %s' % self.file)


def read_text(text_file):
    with open(text_file) as f:
        lines = f.readlines()
    results = []
    for i, line in enumerate(lines):
        numbers = line.strip().split(',')
        assert len(numbers) % 2 == 0, 'Wrong text format detected (cannot be 整除): %s --> line:%d' % (text_file, i+1)
        points = []
        for x in range(0, len(numbers), 2):
            points.append((float(numbers[x]), float(numbers[x+1])))
        results.append(points)
    return results


class Sequence:
    def __init__(self, img_path, poly_path, rect_path, state_path):
        imgs = [os.path.join(img_path, i) for i in os.listdir(img_path)]
        imgs.sort()
        poly_data = read_text(poly_path)
        rect_data = read_text(rect_path)

        assert len(poly_data) == len(rect_data) == len(imgs), 'length do not match! %d vs %d vs %d' \
                                                              % (len(poly_data), len(rect_data), len(imgs))
        tmp = cv2.imread(imgs[0])
        logger.info('---- length: %d, img_size: %d, %d, %d' % (len(imgs), tmp.shape[0], tmp.shape[1], tmp.shape[2]))
        self.imgs = imgs
        self.poly_data = poly_data
        self.rect_data = rect_data

        self.flags = np.zeros(len(imgs), dtype='int32')  # 0 normal 1 invisiable 2 occlusion
        if os.path.exists(state_path):
            self.flags[:] = read_state_file(state_path)
        else:
            logger.info(' ==> New state file will be created after labeled. %s' % state_path)

        self.state_path = state_path

        self.flag_curr = -1
        self.flag_index = -1

    def state_save(self):
        np.savetxt(self.state_path, self.flags, '%d', delimiter=",")
        print(' == update state file to: %s' % self.state_path)

    def get_gens(self):
        n = 0
        while True:
            img, poly, rect = self.imgs[n], self.poly_data[n], self.rect_data[n]
            flag = self.flags[n] if self.flag_curr < 0 else (self.flag_curr+5)
            inter = yield cv2.imread(img), poly, rect, n, flag
            n += inter
            n %= len(self.imgs)

    def record(self, value, index):
        if self.flag_curr < 0:
            self.start_record(value, index)
        elif self.flag_curr == value:
            self.end_record(index)
        else:
            self.end_record(index)
            self.start_record(value, index)

    def start_record(self, value, index):
        self.flag_curr = value
        self.flag_index = index
        print(' ++ Add new state [%d], starting at frame %d' % (self.flag_curr, self.flag_index+1))

    def end_record(self, index):
        if index < self.flag_index:
            self.flags[index: self.flag_index+1] = self.flag_curr
            print(' -- Add state [%d] range from frame %d to %d' % (self.flag_curr, index+1, self.flag_index+1))
        elif index == self.flag_index:
            self.flags[index] = self.flag_curr
            print(' -- Add state [%d] at frame %d' % (self.flag_curr, index + 1))
        else:
            self.flags[self.flag_index: index+1] = self.flag_curr
            print(' -- Add state [%d] range from frame %d to %d' % (self.flag_curr, self.flag_index+1, index+1))
        self.flag_curr = -1
