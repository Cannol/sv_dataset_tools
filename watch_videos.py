import os
import numpy as np
import cv2
from paths import SUB_VIDEOS
from attrs_window import Window

SEQUENCE_STR = 'sequence'
IMG_DIR = 'img'
ATTRS_STR = 'attribute'
GT_RECT = 'groundtruth_rect.txt'
GT_POLY = 'groundtruth.txt'
FRAME_FLAG = 'frame_flags.txt'
WIN_HEIGHT = 960
WIN_WIDTH = 1024

SCALE_START = 3.0

SELECT_VIDEO = 3

SEARCH_RANGE = 2.5

FLAG = {0: 'NOR',
        1: 'INV',
        2: 'OCC',
        5: '*NOR',
        6: '*INV',
        7: '*OCC'}


ATTRS_CH = ['短时遮挡：出现过遮挡帧数不超过50帧的短时遮挡现象至少1次',
            '长时遮挡：出现过遮挡帧数超过50帧的长时遮挡现象至少1次',
            '*相似干扰：在被跟踪目标周围[目标大小的2.5倍范围内]出现至少一个相似目标',  # 确定一个范围2.5
            '*亮度变化：出现过目标亮度或颜色发生明显的变化的现象至少1次',
            '*目标背景变化：目标周围道路出现阴影或地面颜色变化',
            '慢速运动：目标运动速度低于每帧X个像素',     # X有待确定
            '*自然干扰：云雾遮挡，雾霾，画面抖动，影像模糊',
            '连续遮挡：出现过3次或3次以上长短时遮挡',
            '背景相似：目标与背景融为一体，且无明显遮挡物',
            '*平面内旋转：在平面内旋转，车辆发生大于30（马路口，环岛，匝道等）']

ATTRS_EN = ['[STO] Short-Term Occlusion',
            '[LTO] Long-Term Occlusion',
            '[DS] Dense Similarity',
            '[IV] Illumination Variation',
            '[BCH] Background Change',
            '[SM] Slow Motion',
            '[ND] Natural Disturbance',
            '[CO] Continuous Occlusion',
            '[BCL] Background Cluster',
            '[IPR] In-Plane Rotation']

# select language
ATTRS = ATTRS_CH


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
        print('---- length: %d, img_size: %d, %d, %d' % (len(imgs), tmp.shape[0], tmp.shape[1], tmp.shape[2]))
        self.imgs = imgs
        self.poly_data = poly_data
        self.rect_data = rect_data

        self.flags = np.zeros(len(imgs), dtype='int32')  # 0 normal 1 invisiable 2 occlusion
        if os.path.exists(state_path):
            self.flags[:] = np.loadtxt(state_path, delimiter=",", dtype='int32')[:]
            print(' == state file read from: %s' % state_path)
        else:
            print(' == make new state file.')

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


def read_seqs_with_label(img_path, poly_path, rect_path):
    imgs = [os.path.join(img_path, i) for i in os.listdir(img_path)]
    imgs.sort()
    poly_data = read_text(poly_path)
    rect_data = read_text(rect_path)

    assert len(poly_data) == len(rect_data) == len(imgs), 'length do not match! %d vs %d vs %d' \
                                                          % (len(poly_data), len(rect_data), len(imgs))
    tmp = cv2.imread(imgs[0])
    print('---- length: %d, img_size: %d, %d, %d' % (len(imgs), tmp.shape[0], tmp.shape[1], tmp.shape[2]))
    # for img, poly, rect in zip(imgs, poly_data, rect_data):
    #     # print('------------ img:', img)
    #     yield cv2.imread(img), poly, rect

    n = 0
    while True:
        img, poly, rect = imgs[n], poly_data[n], rect_data[n]
        interval = yield cv2.imread(img), poly, rect, n
        n += interval
        n = min(len(imgs), max(n, 0))


class Attr:

    def __init__(self, attrs_file):
        self.file = attrs_file
        self.attrs = []
        self.read_attrs()

    def read_attrs(self):
        with open(self.file) as f:
            lines = f.readlines()[0].strip()
        attrs_value = lines.split(',')
        for i in range(len(ATTRS)):
            try:
                x = attrs_value[i]
                if x == '0':
                    self.attrs.append(False)
                else:
                    self.attrs.append(True)
            except IndexError:
                self.attrs.append(False)

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
            print('-> Attr update: %s' % self.file)


def read_one_video(video_name, video_root, special=None):
    print('- Video: %s (%s)' % (video_name, video_root))
    seqs_dir = os.path.join(video_root, SEQUENCE_STR)

    if special is None:
        seqs = os.listdir(seqs_dir)
        seqs.sort()
    else:
        seqs = special
    seqs.sort()
    for seq in seqs:
        print('-- seq_name:', seq)
        img_path = os.path.join(seqs_dir, seq, IMG_DIR)
        poly_path = os.path.join(seqs_dir, seq, GT_POLY)
        rect_path = os.path.join(seqs_dir, seq, GT_RECT)
        state_path = os.path.join(seqs_dir, seq, FRAME_FLAG)
        yield Attr(os.path.join(video_root, 'attribute', '%s.txt' % seq)), Sequence(img_path, poly_path, rect_path, state_path)


def draw_all(img, poly, rect, n, scale=1.0, state=0):
    poly_np = np.array(poly, np.float)
    rect_np = np.array(rect, np.float)
    rect_np[1, :] += rect_np[0, :]

    if scale != 1.0:
        poly_np *= scale
        rect_np *= scale
        img = cv2.resize(img, (round(img.shape[1]*scale), round(img.shape[0]*scale)), cv2.INTER_LINEAR)

    search_rect_pt1 = [round(rect_np[0, 0]+0.5*(rect_np[1, 0]-rect_np[0, 0])*(1-SEARCH_RANGE)),
                       round(rect_np[0, 1]+0.5*(rect_np[1, 1]-rect_np[0, 1])*(1-SEARCH_RANGE))]
    search_rect_pt2 = [round(rect_np[0, 0]+0.5*(rect_np[1, 0]-rect_np[0, 0])*(1+SEARCH_RANGE)),
                       round(rect_np[0, 1]+0.5*(rect_np[1, 1]-rect_np[0, 1])*(1+SEARCH_RANGE))]
    poly_np = poly_np.astype('int')
    rect_np = rect_np.astype('int')

    poly_np = poly_np.reshape((-1, 1, 2))
    cv2.rectangle(img, (rect_np[0, 0], rect_np[0, 1]), (rect_np[1, 0], rect_np[1, 1]), (0, 0, 255))
    cv2.polylines(img, [poly_np], True, (0, 255, 0), 1, cv2.LINE_AA)
    cv2.rectangle(img, search_rect_pt1, search_rect_pt2, (255, 0, 255))

    cv2.putText(img, '[%s]Frame: %d' % (FLAG[state], n), (rect_np[0, 0], rect_np[0, 1]-10), 0, 0.5, [255, 255, 255], 2)

    return img


cv2.namedWindow("show_pic", cv2.WINDOW_NORMAL)
cv2.resizeWindow("show_pic", WIN_WIDTH, WIN_HEIGHT)
attrs_window = Window()

attrs_window.daemon = True
attrs_window.ATTRS = ATTRS
attrs_window.start()
while not hasattr(attrs_window, 'boxes'):
    attrs_window.join(1)
scale = SCALE_START

wait_time = 0
refresh = True

try:
    for attrs, seqs in read_one_video(*SUB_VIDEOS[SELECT_VIDEO]):
        print('------ ATTRS: {}'.format(attrs.attrs))
        attrs_window.set_attrs(attrs.attrs)
        # seq_content = []
        # for img, poly, rect in seqs:
        #     seq_content.append([img, poly, rect])
        stay = True
        interval = 1
        iter_seqs = seqs.get_gens()
        img, poly, rect, frame, state = iter_seqs.send(None)

        while True:
            if refresh:
                img_ = draw_all(img.copy(), poly, rect, frame+1, scale, state)
                cv2.imshow('show_pic', img_)

            key = cv2.waitKey(wait_time)

            if key == ord('a'):  # 空格
                interval = -1
            elif key == ord('s'):
                interval = 1

            elif key == ord('p'):
                if wait_time == 0:
                    wait_time = 1
                    interval = 1
                else:
                    wait_time = 0
                    refresh = False
                    continue
            elif key == ord('o'):
                if wait_time == 0:
                    wait_time = 1
                    interval = -1
                else:
                    wait_time = 0
                    refresh = False
                    continue
            elif key == ord('z'):
                scale -= 0.1
                print('# change to %.2f' % scale)
                refresh = True
                continue
            elif key == ord('x'):
                scale += 0.1
                print('# change to %.2f' % scale)
                refresh = True
                continue
            elif key == ord('n'):
                break
            elif key == ord('q'):
                iter_seqs.close()
                raise Exception('exit!')
            elif wait_time > 0:
                pass
            elif key == ord('1'):
                seqs.record(1, frame)
                interval = 0
            elif key == ord('2'):
                seqs.record(2, frame)
                interval = 0
            elif key == ord('0'):
                seqs.record(0, frame)
                interval = 0
            else:
                refresh = False
                continue
            img, poly, rect, frame, state = iter_seqs.send(interval)
            refresh = True
        attrs_new = attrs_window.get_attrs()
        attrs.save_attrs(attrs_new)
        seqs.state_save()
except Exception:
    cv2.destroyAllWindows()
    while True:
        ans = input('[EXIT] 是否要保存最后修改的序列的Attribute和Flag文件？(Y/N)')
        if ans == 'Y':
            attrs_new = attrs_window.get_attrs()
            attrs.save_attrs(attrs_new)
            seqs.state_save()
        elif ans == 'N':
            break
        else:
            pass
