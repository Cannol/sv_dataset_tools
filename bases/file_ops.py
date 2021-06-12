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


def save_text(text_file, data):
    lines = []
    for row in data:
        line = ['%.3f,%.3f' % (i, j) for i, j in row]
        lines.append(','.join(line) + '\n')

    with open(text_file, 'w') as f:
        f.writelines(lines)


class Sequence:
    def __init__(self, img_path, poly_path, rect_path, state_path):
        imgs = [os.path.join(img_path, i) for i in os.listdir(img_path)]
        imgs.sort()
        poly_data = read_text(poly_path)
        rect_data = read_text(rect_path)

        self.poly_path = poly_path
        self.rect_path = rect_path

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

        self.edit_mode = False
        self.tmp_save = []
        self.start_index = -1
        self._has_changed = False

    def label_new(self, n):
        poly, rect = self.poly_data[n], self.rect_data[n]
        self.tmp_save = [poly.copy(), rect.copy()]
        self.start_index = n
        self.edit_mode = True

    def label_end(self, n):
        if n == self.start_index:
            self.rect_data[n] = self.tmp_save[1].copy()
            self.poly_data[n] = self.tmp_save[0].copy()
        else:
            self.poly_data[n] = self.tmp_save[0].copy()
            self.rect_data[n] = self.tmp_save[1].copy()
            if n > self.start_index:
                start = self.start_index
                end = n
                start_poly = self.poly_data[start]
                end_poly = self.tmp_save[0]
            else:
                start = n
                end = self.start_index
                end_poly = self.poly_data[start]
                start_poly = self.tmp_save[0]
            diff_num = end - start
            if diff_num > 1:
                diff_poly = []
                for p1, p2 in zip(start_poly, end_poly):
                    diff_poly.append(((p2[0]-p1[0])/diff_num, (p2[1]-p1[1])/diff_num))

                # 只需要修改中间位置的值
                for i, index in enumerate(range(start+1, end)):
                    poly = []
                    for p, dp in zip(start_poly, diff_poly):
                        poly.append((p[0]+(i+1)*dp[0], p[1]+(i+1)*dp[1]))
                    tmp = np.array(poly)
                    p = np.min(tmp, axis=0)
                    q = np.max(tmp, axis=0)
                    rect = [(p[0], p[1]), (q[0] - p[0], q[1] - p[1])]
                    self.poly_data[index] = poly
                    self.rect_data[index] = rect

        self.edit_mode = False
        self.start_index = -1
        self._has_changed = True

    def reset_poly(self):
        poly, rect = self.poly_data[self.start_index], self.rect_data[self.start_index]
        self.tmp_save = [poly.copy(), rect.copy()]
        return self.tmp_save

    def move_poly(self, dx, dy):
        all_points = self.tmp_save[0]
        for i in range(len(all_points)):
            all_points[i] = (all_points[i][0]+dx, all_points[i][1]+dy)
        tmp = np.array(self.tmp_save[0])
        p = np.min(tmp, axis=0)
        q = np.max(tmp, axis=0)
        self.tmp_save[1] = [(p[0], p[1]), (q[0] - p[0], q[1] - p[1])]
        return self.tmp_save

    def detect_point(self, x, y, scale):
        points = np.array(self.tmp_save[0], dtype='float')
        l = np.square(points[:, 0]*scale - x) + np.square(points[:, 1]*scale - y)
        n = np.argmin(l)
        if l[n] < 25:
            return n
        else:
            return -1

    def update_poly(self, n, x, y, scale):
        self.tmp_save[0][n] = (x / scale, y / scale)
        tmp = np.array(self.tmp_save[0])
        p = np.min(tmp, axis=0)
        q = np.max(tmp, axis=0)
        self.tmp_save[1] = [(p[0], p[1]), (q[0] - p[0], q[1] - p[1])]
        return self.tmp_save

    def label_save(self):
        save_text(self.poly_path, self.poly_data)
        save_text(self.rect_path, self.rect_data)

    def state_save(self):
        np.savetxt(self.state_path, self.flags, '%d', delimiter=",")
        print(' == update state file to: %s' % self.state_path)

    def get_gens(self):
        n = 0
        while True:
            img = self.imgs[n]
            if self.edit_mode:
                poly, rect = self.tmp_save
            else:
                poly, rect = self.poly_data[n], self.rect_data[n]
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
