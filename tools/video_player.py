import cv2
import numpy as np
from bases.sv_dataset import DatasetBase
from attrs_window import Window
from configs import VIDEOPLAYER_CONFIG_FILE
from bases.file_ops import Sequence, Attr

from tools.auto_label_attrs import LabelDataAttr


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

    CtrlKey: int = 8
    EscKey: int = 27
    EnterKey: int = 10
    Backspace: int = 20

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

        self.l_x = 0
        self.l_y = 0

        self.win_name = 'None'

        self._mouse_down = False
        self._select_point = -1
        self._state = None
        self.img = None
        self._start_point = [-1, -1]
        self.show_ref = False

        self._move_th = [0, 0]

        self._mini_img = None
        self._new_poly = []

    def get_config(self):
        return self._show_obj, self._wait_time, self.center_mode

    def set_config(self, v):
        if v is None:
            return
        else:
            self._show_obj, self._wait_time, self.center_mode = v

    def init_data(self):
        self.data_gen = Sequence(self.img_dir, self.poly, self.rect, self.state)
        self.data_attr = Attr(self.attr)

    def _mouse_event_new_object(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self._new_poly.append([x, y])
            self._refresh_new_object()
            self._mouse_down = True
        elif event == cv2.EVENT_MOUSEMOVE:
            self._new_poly[-1][0] = x
            self._new_poly[-1][1] = y
            self._refresh_new_object()
        elif event == cv2.EVENT_LBUTTONUP and self._mouse_down:
            self._mouse_down = False
            self._refresh_new_object()

    def _refresh_new_object(self):
        img_ = self._mini_img.copy()
        if len(self._new_poly) > 0:
            if len(self._new_poly) > 2:
                poly = np.array(self._new_poly[:-1], 'int')
                poly = poly.reshape((-1, 1, 2))
                cv2.polylines(img_, [poly], True, (0, 255, 0), 1, cv2.LINE_AA)
            if len(self._new_poly) > 1:
                cv2.line(img_, self._new_poly[-1], self._new_poly[-2], (128, 128, 128), 1, cv2.LINE_AA)
            if len(self._new_poly) > 2:
                cv2.line(img_, self._new_poly[-1], self._new_poly[0], (128, 128, 128), 1, cv2.LINE_AA)
            for point in self._new_poly[:-1]:
                cv2.circle(img_, point, 5, [128, 255, 128], -1)
            cv2.circle(img_, self._new_poly[-1], 5, [255, 255, 255], -1)
        cv2.imshow(self.win_name, img_)

    def _make_new_mode(self):
        img = cv2.resize(self.img, (round(self.img.shape[1] * self.scale), round(self.img.shape[0] * self.scale)), cv2.INTER_LINEAR)
        self._mini_img = img[self.l_y:min(img.shape[0], self.l_y+self.WinHeight),
                             self.l_x:min(img.shape[1], self.l_x+self.WinWidth)]
        self._refresh_new_object()
        self._new_poly = [[0, 0]]
        cv2.setMouseCallback(self.win_name, self._mouse_event_new_object)

        while True:
            key = cv2.waitKey(0)
            if key == self.EscKey:
                cv2.setMouseCallback(self.win_name, self._empty)
                self._L.info('You cancel the new object label operation, nothing changed.')
                break
            elif key == self.Backspace:
                if len(self._new_poly) > 1:
                    self._new_poly.pop(-1)
                    self._refresh_new_object()
            elif key == self.EnterKey:
                cv2.setMouseCallback(self.win_name, self._empty)
                self.data_gen.add_new_at_frame(self._new_poly[:-1], self.frame, self.scale, self.l_x, self.l_y)
                self._L.info('New poly has been recorded in frame %d' % self.frame)
                break

    def _draw(self, img, poly, rect, n, scale=1.0, state=0, show_obj=True, center_obj=False,
              edit_mode=False, update_off=True):
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
        if show_obj and not edit_mode:
            cv2.rectangle(img, (rect_np[0, 0], rect_np[0, 1]), (rect_np[1, 0], rect_np[1, 1]), (0, 0, 255))
            cv2.polylines(img, [poly_np], True, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.rectangle(img, search_rect_pt1, search_rect_pt2, (255, 0, 255))

        cv2.putText(img, '[%s]Frame: %d' % (self._FLAG[state], n), (search_rect_pt1[0], search_rect_pt1[1] - 10), 0, 0.5,
                    [255, 255, 255], 2)
        if edit_mode:
            if self.show_ref:
                ori_poly = np.array(self.data_gen.poly_data[self.frame], 'float')
                ori_poly *= scale
                ori_poly = ori_poly.astype('int')
                ori_poly = ori_poly.reshape((-1, 1, 2))
                cv2.polylines(img, [ori_poly], True, (202, 235, 216), 1, cv2.LINE_AA)
                for point in ori_poly:
                    cv2.circle(img, (point[0, 0], point[0, 1]), 5, [128, 138, 135], -1)
                if 0 <= self._select_point < len(ori_poly):
                    point = ori_poly[self._select_point]
                    cv2.circle(img, (point[0, 0], point[0, 1]), 6, [128, 255, 135], 3)
            cv2.rectangle(img, (rect_np[0, 0], rect_np[0, 1]), (rect_np[1, 0], rect_np[1, 1]), (255, 0, 0))
            cv2.polylines(img, [poly_np], True, (255, 255, 255), 1, cv2.LINE_AA)
            for point in poly_np:
                cv2.circle(img, (point[0, 0], point[0, 1]), 5, [0, 0, 255], -1)
            if 0 <= self._select_point < len(poly_np):
                point = poly_np[self._select_point]
                cv2.circle(img, (point[0, 0], point[0, 1]), 6, [0, 255, 0], 3)

        if center_obj:
            if update_off:
                self.l_x = max((rect_np[1, 0] + rect_np[0, 0] - self.WinWidth) // 2, 0)
                self.l_y = max((rect_np[1, 1] + rect_np[0, 1] - self.WinHeight) // 2, 0)
            return img[self.l_y:min(img.shape[0], self.l_y+self.WinHeight),
                       self.l_x:min(img.shape[1], self.l_x+self.WinWidth)]

        return img

    @classmethod
    def CreateGlobalWindow(cls, win_name):
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_name, cls.WinWidth, cls.WinHeight)

    def _mouse_event(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if flags == self.CtrlKey:
                self._start_point[0] = x
                self._start_point[1] = y
                self._mouse_down = True
            else:
                self._select_point = self.data_gen.detect_point(x + self.l_x, y + self.l_y, self.scale)
                if self._select_point >= 0:
                    self._mouse_down = True
        elif event == cv2.EVENT_LBUTTONUP and self._mouse_down:
            self._mouse_down = False
            self._select_point = -1
            poly, rect = self.data_gen.tmp_save
            img_ = self._draw(self.img.copy(), poly, rect, self.frame + 1, self.scale, self._state,
                              self._show_obj, self.center_mode, True)
            cv2.imshow(self.win_name, img_)
            self._start_point[0] = -1
        elif event == cv2.EVENT_MOUSEMOVE:
            if self._mouse_down:
                if self._start_point[0] >= 0:
                    dx = x - self._start_point[0]
                    dy = y - self._start_point[1]
                    self._start_point[0] = x
                    self._start_point[1] = y
                    poly, rect = self.data_gen.move_poly(dx/self.scale, dy/self.scale)
                    if flags == self.CtrlKey:
                        img_ = self._draw(self.img.copy(), poly, rect, self.frame + 1, self.scale, self._state,
                                          self._show_obj, self.center_mode, True, False)
                    else:
                        self._start_point[0] = -1
                        self._mouse_down = False
                        img_ = self._draw(self.img.copy(), poly, rect, self.frame + 1, self.scale, self._state,
                                          self._show_obj, self.center_mode, True, True)
                    cv2.imshow(self.win_name, img_)

                else:
                    poly, rect = self.data_gen.update_poly(self._select_point, x+self.l_x, y+self.l_y, self.scale)
                    img_ = self._draw(self.img.copy(), poly, rect, self.frame + 1, self.scale, self._state,
                                      self._show_obj, self.center_mode, True, False)
                    cv2.imshow(self.win_name, img_)
            else:
                if -10 < x-self._move_th[0] < 10 and -10 < y-self._move_th[1] < 10:
                    self._move_th[0] = x
                    self._move_th[1] = y
                    # print('???')
                else:
                    self._move_th[0] = x
                    self._move_th[1] = y
                    # print('!!!')
                    return
                sp = self.data_gen.detect_point(x+self.l_x, y+self.l_y, self.scale)
                if self._select_point == sp:
                    return
                self._select_point = sp
                poly, rect = self.data_gen.tmp_save
                img_ = self._draw(self.img.copy(), poly, rect, self.frame + 1, self.scale, self._state,
                                  self._show_obj, self.center_mode, True, False)
                cv2.imshow(self.win_name, img_)

    def _empty(self, event, x, y, flags, param):
        pass

    def _edit_mode(self, set_mode, n):
        if set_mode:
            self.data_gen.label_new(n)
            cv2.setMouseCallback(self.win_name, self._mouse_event)
        else:
            self.data_gen.label_end(n)
            cv2.setMouseCallback(self.win_name, self._empty)

    def update_auto_attrs(self):
        attrs = self._window_attr.get_attrs()
        LabelDataAttr.SetAll(rect=self.data_gen.rect_data,
                             state=self.data_gen.flags,
                             attr=attrs)
        self._window_attr.set_attrs(attrs)
        self._L.info('-- update attr: {}'.format(attrs))

    def play(self, win_name=None):

        self.InitializedPlayer()

        self._window_attr.bind_func = self.update_auto_attrs

        if win_name is None:
            self.win_name = self.seq_name
            cv2.namedWindow(self.win_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.win_name, self.WinWidth, self.WinHeight)
        else:
            self.win_name = win_name

        self._L.info('Video Sequence Name: %s' % self.seq_name)
        self.init_data()

        self._L.info('------ ATTRS: {}'.format(self.data_attr.attrs))
        self._window_attr.set_attrs(self.data_attr.attrs)

        isGoing = True
        refresh = True

        interval = 1
        iter_seqs = self.data_gen.get_gens()
        self.img, poly, rect, self.frame, self._state = iter_seqs.send(None)

        return_value = 0
        edit_mode = False
        self.show_ref = False

        try:
            while isGoing:
                if refresh:
                    img_ = self._draw(self.img.copy(), poly, rect, self.frame+1, self.scale, self._state,
                                      self._show_obj, self.center_mode, edit_mode)
                    cv2.imshow(self.win_name, img_)
                key = cv2.waitKey(self._wait_time)
                # print(key)
                if key == ord('e'):
                    edit_mode = not edit_mode
                    # 进入编辑模式
                    self._edit_mode(edit_mode, self.frame)
                    interval = 0

                elif key == ord('r') and edit_mode:
                    self.data_gen.reset_poly()
                    interval = 0
                elif key == ord('[') and edit_mode:
                    self.data_gen.rotate(-1)
                    interval = 0
                elif key == ord(']') and edit_mode:
                    self.data_gen.rotate(1)
                    interval = 0
                elif key == ord('`') and edit_mode:
                    self.show_ref = not self.show_ref
                    interval = 0
                elif key == self.EscKey and edit_mode:
                    self._edit_mode(False, -1)
                    edit_mode = False
                    interval = 0
                elif not edit_mode and key == ord('v'):
                    img_ = self._draw(self.img.copy(), poly, rect, self.frame + 1, self.scale, self._state,
                                      True, True, False)
                    cv2.imshow(self.win_name, img_)
                    self._make_new_mode()
                    interval = 0
                elif key == ord('a'):  # 空格
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
                self.img, poly, rect, self.frame, self._state = iter_seqs.send(interval)
                refresh = True
            attrs_new = self._window_attr.get_attrs()
            self.data_attr.save_attrs(attrs_new)
            self.data_gen.state_save()
            self.data_gen.label_save()

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
                    self.data_gen.label_save()
                    break
                elif ans == 'N':
                    break
                else:
                    pass
        cv2.destroyAllWindows()
        return return_value


VideoPlayer.Load(VIDEOPLAYER_CONFIG_FILE)

if __name__ == '__main__':
    # VideoPlayer.PlayList(VideoPlayer.MakePlayList(['*.*']))
    VideoPlayer.PlayList(VideoPlayer.MakePlayList(['04.000017']))

