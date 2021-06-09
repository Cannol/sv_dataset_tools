import cv2
import numpy as np
from bases.sv_dataset import DatasetBase
from attrs_window import Window
from configs import VIDEOPLAYER_CONFIG_FILE
from bases.file_ops import Sequence, Attr


class VideoPlayer(DatasetBase):

    """ DatasetBase has these attrs:
    DataRoot: str = ''
    VideoList: list = []

    AnnosDirName: str = ''
    SeqDirName: str = ''
    AttrPostfix: str = ''
    StatePostfix: str = ''
    RectPostfix: str = ''
    PolyPostfix: str = ''

    D = {}
    """

    ScaleStart: float = 3.0
    SearchRange: float = 2.5

    WinHeight: int = 960
    WinWidth: int = 1024

    Attrs = 'ch'

    _ATTRS = []

    _FLAG = {0: 'NOR',
             1: 'INV',
             2: 'OCC',
             5: '*NOR',
             6: '*INV',
             7: '*OCC'}

    SameNext = False

    _window_attr = None
    _show_obj = True
    _wait_time = 0

    @classmethod
    def InitializedPlayer(cls):
        if cls._window_attr is None:
            cls._window_attr = Window()
            cls._window_attr.daemon = True
            if cls.Attrs == 'ch':
                cls._ATTRS = cls.AttrsCH
            elif cls.Attrs == 'en':
                cls._ATTRS = cls.AttrsEN
            cls._window_attr.ATTRS = cls._ATTRS
            cls._window_attr.start()
            while not hasattr(cls._window_attr, 'boxes'):
                cls._window_attr.join(1)

    @classmethod
    def ParseNameList(cls, name_list, result=None):
        if isinstance(name_list, str):
            name_list = [name_list]
        if result is None:
            result = []
        for name in name_list:
            v, seq = name.split('.')
            if v == '*':
                a = '%%s.%s' % seq
                sub_list = [a % i for i in cls.VideoList]
                cls.ParseNameList(sub_list, result)
            elif seq == '*':
                a = '%s.' % v
                sub_list = [i for i in cls.D if i.startswith(a)]
                sub_list.sort()
                cls.ParseNameList(sub_list, result)
            elif name not in result:
                result.append(name)
        return result

    @classmethod
    def MakePlayList(cls, name_list):
        v_list = []
        _list = cls.ParseNameList(name_list)
        for vs_name in _list:
            vs = cls.WriteIntoObj(vs_name)
            if vs:
                v_list.append([vs_name, vs])
            else:
                v, seq = vs_name.split('.')
                cls._L.error('[Video %s - sequence %s] does not exist, skipped!' % (v, seq))
        return v_list

    @classmethod
    def PlayList(cls, play_list):
        i = 0
        cls._L.info('======================= Start ========================')
        cc = None
        while True:
            name, vs = play_list[i]
            if cls.SameNext:
                vs.set_config(cc)

            r = vs.play()
            if r == -2:
                break
            else:
                if cls.SameNext:
                    cc = vs.get_config()
                i += r
                i %= len(play_list)
        cls._L.info('===================== END ======================')

    def __init__(self):
        super().__init__()
        self.seq_name = ''
        self.img_dir = ''
        self.attr = ''
        self.state = ''
        self.rect = ''
        self.poly = ''

        self.frame = 0
        self.scale = self.ScaleStart

        self.data_gen = None
        self.data_attr = None
        self.center_mode = False

    def get_config(self):
        return self._show_obj, self._wait_time, self.center_mode

    def set_config(self, v):
        if v is None:
            return
        else:
            self._show_obj, self._wait_time, self.centern_mode = v

    def init_data(self):
        self.data_gen = Sequence(self.img_dir, self.poly, self.rect, self.state)
        self.data_attr = Attr(self.attr)

    def _draw(self, img, poly, rect, n, scale=1.0, state=0, show_obj=True, center_obj=False):
        poly_np = np.array(poly, np.float)
        rect_np = np.array(rect, np.float)
        rect_np[1, :] += rect_np[0, :]

        if scale != 1.0:
            poly_np *= scale
            rect_np *= scale
            img = cv2.resize(img, (round(img.shape[1] * scale), round(img.shape[0] * scale)), cv2.INTER_LINEAR)
        A = max(rect_np[1, 0] - rect_np[0, 0], rect_np[1, 1] - rect_np[0, 1]) * self.SearchRange

        search_rect_pt1 = [round(rect_np[0, 0] + 0.5 * (rect_np[1, 0] - rect_np[0, 0] - A)),
                           round(rect_np[0, 1] + 0.5 * (rect_np[1, 1] - rect_np[0, 1] - A))]
        search_rect_pt2 = [round(rect_np[0, 0] + 0.5 * (rect_np[1, 0] - rect_np[0, 0] + A)),
                           round(rect_np[0, 1] + 0.5 * (rect_np[1, 1] - rect_np[0, 1] + A))]
        poly_np = poly_np.astype('int')
        rect_np = rect_np.astype('int')

        poly_np = poly_np.reshape((-1, 1, 2))
        if show_obj:
            cv2.rectangle(img, (rect_np[0, 0], rect_np[0, 1]), (rect_np[1, 0], rect_np[1, 1]), (0, 0, 255))
            cv2.polylines(img, [poly_np], True, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.rectangle(img, search_rect_pt1, search_rect_pt2, (255, 0, 255))

        cv2.putText(img, '[%s]Frame: %d' % (self._FLAG[state], n), (search_rect_pt1[0], search_rect_pt1[1] - 10), 0, 0.5,
                    [255, 255, 255], 2)

        if center_obj:
            l_x = max((rect_np[1, 0] + rect_np[0, 0] - self.WinWidth) // 2, 0)
            l_y = max((rect_np[1, 1] + rect_np[0, 1] - self.WinHeight) // 2, 0)
            return img[l_y:l_y+self.WinHeight, l_x:l_x+self.WinWidth]

        return img

    @classmethod
    def CreateGlobalWindow(cls, win_name):
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, cls.WinWidth, cls.WinHeight)

    def play(self, win_name=None):

        self.InitializedPlayer()

        if win_name is None:
            win_name = self.seq_name
            cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_name, self.WinWidth, self.WinHeight)

        self._L.info('Video Sequence Name: %s' % self.seq_name)
        self.init_data()

        self._L.info('------ ATTRS: {}'.format(self.data_attr.attrs))
        self._window_attr.set_attrs(self.data_attr.attrs)

        isGoing = True
        refresh = True

        interval = 1
        iter_seqs = self.data_gen.get_gens()
        img, poly, rect, self.frame, state = iter_seqs.send(None)

        return_value = 0

        try:
            while isGoing:
                if refresh:
                    img_ = self._draw(img.copy(), poly, rect, self.frame+1, self.scale, state, self._show_obj, self.center_mode)
                    cv2.imshow(win_name, img_)
                key = cv2.waitKey(self._wait_time)

                if key == ord('a'):  # 空格
                    interval = -1
                elif key == ord('s'):
                    interval = 1

                elif key == ord('h'):
                    interval = 0
                    self._show_obj = not self._show_obj

                elif key == ord('p'):
                    if self._wait_time == 0:
                        self._wait_time = 1
                        interval = 1
                    else:
                        self._wait_time = 0
                        refresh = False
                        continue
                elif key == ord('o'):
                    if self._wait_time == 0:
                        self._wait_time = 1
                        interval = -1
                    else:
                        self._wait_time = 0
                        refresh = False
                        continue

                elif key == ord('z'):
                    self.scale -= 0.1
                    print('# change to %.2f' % self.scale)
                    refresh = True
                    continue
                elif key == ord('x'):
                    self.scale += 0.1
                    print('# change to %.2f' % self.scale)
                    refresh = True
                    continue
                elif key == ord('n'):
                    return_value = 1
                    break
                elif key == ord('b'):
                    return_value = -1
                    break
                elif key == ord('r'):
                    return_value = 0
                    break
                elif key == ord(' '):
                    interval = 0
                    self.center_mode = not self.center_mode

                elif key == ord('q'):
                    iter_seqs.close()
                    raise Exception('正常退出！')
                elif self._wait_time > 0:
                    pass
                elif key == ord('1'):
                    self.data_gen.record(1, self.frame)
                    interval = 0
                elif key == ord('2'):
                    self.data_gen.record(2, self.frame)
                    interval = 0
                elif key == ord('0'):
                    self.data_gen.record(0, self.frame)
                    interval = 0
                else:
                    refresh = False
                    continue
                img, poly, rect, self.frame, state = iter_seqs.send(interval)
                refresh = True
            attrs_new = self._window_attr.get_attrs()
            self.data_attr.save_attrs(attrs_new)
            self.data_gen.state_save()

        except Exception as e:
            cv2.destroyAllWindows()
            print(e)
            return_value = -2
            while True:
                ans = input('[EXIT] 是否要保存最后修改的序列的Attribute和Flag文件？(Y/N)')
                if ans == 'Y':
                    attrs_new = self._window_attr.get_attrs()
                    self.data_attr.save_attrs(attrs_new)
                    self.data_gen.state_save()
                    break
                elif ans == 'N':
                    break
                else:
                    pass
        cv2.destroyAllWindows()
        return return_value


VideoPlayer.Load(VIDEOPLAYER_CONFIG_FILE)

if __name__ == '__main__':
    VideoPlayer.PlayList(VideoPlayer.MakePlayList(['*.*']))

