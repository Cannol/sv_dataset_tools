import os
import os.path as path

import matplotlib.pyplot as plt
import numpy as np
import tqdm
from common.yaml_helper import YamlConfigClassBase
from bases.sv_dataset import DatasetBase
from configs import RESULTS_ANALYSIS_CONFIG_FILE
from configs import TMP_CONFIG_FILE
from bases.file_ops import read_text
import matplotlib
from PIL import Image
import cv2
from bases.abs_file import Abstract
from bases.file_ops import Attr

color_panel = [
    [255, 255, 0],
    [255, 0, 0],
    [255, 0, 255],
[0, 0, 255],
[0, 255, 255],
[232, 134, 74],
[255, 0, 153],
[0, 0, 152],

    [0, 153, 255],
]

color_panel_16 = [

    '#00ffff',

    '#0000ff',

    '#ff00ff',
'#ff0000',
'#ffff00',
'#4a86e8',
'#9900ff',
    '#980000',

    '#ff9900'
]

class TmpConfigs(YamlConfigClassBase):
    video_seq: str = ''
    frame_index: int = 0
    scale: float = 0.0
    win_width: int = 0
    win_height: int = 0
    show_frame_num: bool = True
    show_attrs: bool = True
    show_gt: bool = True
    save_ori: str = ''


def _read_result_file(file_path):
    with open(file_path) as f:
        lines = f.readlines()

    if len(lines[1].split(',')) == 4:
        result = -np.ones((len(lines), 4))
        for i in range(1, len(lines)):
            line = lines[i]
            result[i, :] = np.array(list(map(float, line.split(','))))
    else:
        result = -np.ones((len(lines), len(lines[1].split(',')) // 2, 2))
        for i in range(1, len(lines)):
            line = lines[i]
            result[i, :, :] = np.array(list(map(float, line.split(',')))).reshape((-1, 2))

    return result


class ResultsAnalysis(DatasetBase):
    ResultDir: str = ''
    SubDir: str = ''
    Trackers: dict = {}
    ResultFileNamePostfix: str = ''

    _tracker_enabled: dict = {}

    _attrs = [i.split(']')[0][1:] for i in DatasetBase.AttrsEN]

    _image_last = None

    @classmethod
    def Read(cls):
        super(ResultsAnalysis, cls).Read()
        all_items = tqdm.tqdm(list(cls.D))
        for seq in all_items:
            all_items.set_description(seq)
            vid, seq_id = seq.split('.')
            results = {}
            for tracker in cls.Trackers:
                result_file = path.join(cls.ResultDir, vid, tracker, cls.SubDir, seq_id,
                                        '%s_%s.txt' % (seq_id, cls.ResultFileNamePostfix))
                results[tracker] = result_file
                assert path.exists(result_file), 'File not exists: %s' % result_file

            cls.D[seq]['results'] = results

    # @classmethod
    # def playing(cls):
    #     TmpConfigs.Load(TMP_CONFIG_FILE)
    #     plt.close()
    #     seq = cls.D[TmpConfigs.video_seq]
    #     abstract = Abstract.MakeNewFromJsonFile(seq['abs'])
    #     start_frame, end_frame = abstract.source_info.frame_range
    #
    #     for i in range(start_frame, end_frame + 1):
    #         TmpConfigs.frame_index = i
    #         cls._refresh(abstract, seq)
    #
    # @classmethod
    # def on_play(cls):

    @classmethod
    def _multi_refresh(cls, abstract: Abstract, seq: dict):
        assert isinstance(TmpConfigs.frame_index, list)

        # start_frame, end_frame = abstract.source_info.frame_range
        TmpConfigs.frame_index = np.array(TmpConfigs.frame_index, dtype='int')

        if all(TmpConfigs.frame_index <= abstract.details.length):
            pass
        else:
            cls._L.error('超出范围！ length == %d'
                         % abstract.details.length)
            return

        n_pic = len(TmpConfigs.frame_index)
        image_out = np.zeros((TmpConfigs.win_height, TmpConfigs.win_width*n_pic, 3), dtype='uint8')

        plt.figure('%s' % TmpConfigs.video_seq, figsize=(10*n_pic, 10))
        a = np.array([0, 1])
        b = a * 1
        plt.plot(a, b, color='#00ff00', label='GroundTruth')
        trackers_leg = []

        for i, frame_num in enumerate(TmpConfigs.frame_index):
            index = frame_num - 1
            pic_file = '%06d.tiff' % frame_num
            img_path = path.join(seq['img_dir'], pic_file)

            # image = Image.open(img_path)
            img = cv2.imread(img_path)
            img_big = cv2.resize(img, None, fx=TmpConfigs.scale, fy=TmpConfigs.scale, interpolation=cv2.INTER_LANCZOS4)
            h, w, _ = img_big.shape

            poly = np.array(read_text(seq['poly'])[index])
            rect = np.array(read_text(seq['rect'])[index])

            # rect = rect.reshape((-1))

            poly *= TmpConfigs.scale
            rect *= TmpConfigs.scale

            if rect[1, 0] > TmpConfigs.win_width or rect[1, 1] > TmpConfigs.win_height:
                cls._L.error('窗体尺寸小于目标框范围！请减少scale！')

            off_x = int(round(min(max(rect[0, 0] + (rect[1, 0] - TmpConfigs.win_width) / 2, 0), w - rect[1, 0])))
            off_y = int(round(min(max(rect[0, 1] + (rect[1, 1] - TmpConfigs.win_height) / 2, 0), h - rect[1, 1])))

            poly = poly.astype('int')
            poly = poly.reshape((-1, 1, 2))
            if TmpConfigs.show_gt:
                cv2.polylines(img_big, [poly], True, (0, 255, 0), 1, cv2.LINE_AA)

            if index > 0:
                n = 0
                trackers_leg = []
                for tracker in cls.Trackers:

                    if cls._tracker_enabled[tracker].get() == 1:

                        color = color_panel[n] if n < len(color_panel) else [0, 0, 0]
                        color16 = color_panel_16[n] if n < len(color_panel) else '#000000'

                        trackers_leg.append([color16, cls.Trackers[tracker]])

                        n += 1
                        rect_re = _read_result_file(seq['results'][tracker])[index]
                        if len(rect_re.shape) == 1:
                            x, y, w, h = rect_re * TmpConfigs.scale
                            xx = int(round(x + w))
                            yy = int(round(y + h))
                            x = int(round(x))
                            y = int(round(y))
                            cv2.rectangle(img_big, (x, y), (xx, yy), color, 1, cv2.LINE_AA)
                        elif len(rect_re.shape) == 2:
                            # poly
                            poly_re = rect_re * TmpConfigs.scale
                            poly_re = poly_re.astype('int')
                            poly_re = poly_re.reshape((-1, 1, 2))
                            cv2.polylines(img_big, [poly_re], True, color, 1, cv2.LINE_AA)
                        else:
                            raise ValueError

            img = img_big[off_y: off_y + TmpConfigs.win_height, off_x: off_x + TmpConfigs.win_width, :]
            if TmpConfigs.show_frame_num:
                cv2.putText(img, '#%03d' % frame_num, (20, 50), cv2.QT_FONT_BLACK, 1, (255, 255, 255), 1, lineType=cv2.LINE_AA)

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            image_out[:, i*TmpConfigs.win_width: (i+1)*TmpConfigs.win_width, :] = img[:, :, :]

        x_t = np.arange(0, TmpConfigs.win_width*n_pic, 5*TmpConfigs.scale)
        # x_t_0 = np.arange(0, TmpConfigs.win_width, 2*TmpConfigs.scale)
        # x_n = (x_t_0 / TmpConfigs.scale).astype('int')
        # x_n = np.repeat(x_n, n_pic)

        y_t = np.arange(0, TmpConfigs.win_height + 10, 5*TmpConfigs.scale)
        y_n = (y_t / TmpConfigs.scale).astype('int')

        for cc, ll in trackers_leg:
            a = np.array([0, 1])
            b = a * 1
            plt.plot(a, b, color=cc, label=ll)

        plt.legend(bbox_to_anchor=(0, 0), loc='upper left', borderaxespad=0.1, ncol=9)
        # plt.legend()
        attrs = Attr(seq['attr'])
        attrs_name = []
        for ii, attr in enumerate(attrs.attrs):
            if attr == 1:
                attrs_name.append(cls._attrs[ii])
        if TmpConfigs.show_attrs:
            cv2.putText(image_out, '%s - %s' % (TmpConfigs.video_seq, ', '.join(attrs_name)),
                        (20, TmpConfigs.win_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1, lineType=cv2.LINE_AA)
        plt.imshow(image_out)
        cls._image_last = cv2.cvtColor(image_out, cv2.COLOR_RGB2BGR)
        # ax.imshow(img)
        plt.xticks(x_t, [])
        plt.yticks(y_t, y_n)

        plt.tick_params('x', top=True, bottom=False)

        plt.show()

    @classmethod
    def _refresh(cls, abstract: Abstract, seq: dict):
        start_frame, end_frame = abstract.source_info.frame_range
        if TmpConfigs.frame_index < abstract.details.length:
            pic_file = '%06d.tiff' % TmpConfigs.frame_index
            img_path = path.join(seq['img_dir'], pic_file)
        else:
            cls._L.error('超出范围！ length == %d'
                         % abstract.details.length)
            return
        # image = Image.open(img_path)
        img = cv2.imread(img_path)
        img_big = cv2.resize(img, None, fx=TmpConfigs.scale, fy=TmpConfigs.scale, interpolation=cv2.INTER_LANCZOS4)
        h, w, _ = img_big.shape
        poly = np.array(read_text(seq['poly'])[TmpConfigs.frame_index-1])
        rect = np.array(read_text(seq['rect'])[TmpConfigs.frame_index-1])

        # rect = rect.reshape((-1))

        poly *= TmpConfigs.scale
        rect *= TmpConfigs.scale

        if rect[1, 0] > TmpConfigs.win_width or rect[1, 1] > TmpConfigs.win_height:
            cls._L.error('窗体尺寸小于目标框范围！请减少scale！')

        off_x = int(round(min(max(rect[0, 0] + (rect[1, 0] - TmpConfigs.win_width) / 2, 0), w-rect[1, 0])))
        off_y = int(round(min(max(rect[0, 1] + (rect[1, 1] - TmpConfigs.win_height) / 2, 0), h-rect[1, 1])))

        poly = poly.astype('int')
        poly = poly.reshape((-1, 1, 2))
        cv2.polylines(img_big, [poly], True, (0, 255, 0), 1, cv2.LINE_AA)

        trackers_leg = []

        # fig, ax = plt.subplots()
        plt.figure('%s - %d/%d (%s)' % (TmpConfigs.video_seq, TmpConfigs.frame_index, abstract.details.length, pic_file))
        a = np.array([0, 1])
        b = a * 1
        plt.plot(a, b, color='#00ff00', label='GroundTruth')

        if TmpConfigs.frame_index > 1:
            n = 0
            for tracker in cls.Trackers:
                if cls._tracker_enabled[tracker].get() == 1:

                    color = color_panel[n] if n < len(color_panel) else [0, 0, 0]
                    color16 = color_panel_16[n] if n < len(color_panel) else '#000000'

                    trackers_leg.append([color16, cls.Trackers[tracker]])

                    # plt.scatter(x=[0], y=[0], c=trackers_leg[-1][0], label=trackers_leg[-1][1])

                    n += 1
                    rect_re = _read_result_file(seq['results'][tracker])[TmpConfigs.frame_index-1]
                    if len(rect_re.shape) == 1:
                        x, y, w, h = rect_re*TmpConfigs.scale
                        xx = int(round(x + w))
                        yy = int(round(y + h))
                        x = int(round(x))
                        y = int(round(y))
                        cv2.rectangle(img_big, (x, y), (xx, yy), color, 1, cv2.LINE_AA)
                    elif len(rect_re.shape) == 2:
                        # poly
                        poly_re = rect_re*TmpConfigs.scale
                        poly_re = poly_re.astype('int')
                        poly_re = poly_re.reshape((-1, 1, 2))
                        cv2.polylines(img_big, [poly_re], True, color, 1, cv2.LINE_AA)
                    else:
                        raise ValueError

            for cc, ll in trackers_leg:
                a = np.array([0, 1])
                b = a * 1
                plt.plot(a, b, color=cc, label=ll)

        img = img_big[off_y: off_y+TmpConfigs.win_height, off_x: off_x+TmpConfigs.win_width, :]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0.)

        x_t = np.arange(0, TmpConfigs.win_width+10, 50)
        x_n = (x_t / TmpConfigs.scale).astype('int')

        y_t = np.arange(0, TmpConfigs.win_width + 10, 50)[::-1]
        y_n = (y_t / TmpConfigs.scale).astype('int')

        plt.imshow(img)
        # ax.imshow(img)
        plt.xticks(x_t, x_n)
        plt.yticks(y_t, y_n)

        plt.show()

    @classmethod
    def on_refresh(cls):
        TmpConfigs.Load(TMP_CONFIG_FILE)
        plt.close()
        seq = cls.D[TmpConfigs.video_seq]
        abstract = Abstract.MakeNewFromJsonFile(seq['abs'])

        if isinstance(TmpConfigs.frame_index, list):
            # for i in range(len(TmpConfigs.frame_index)):
            #     TmpConfigs.frame_index[i] += 1
            cls._multi_refresh(abstract, seq)
        elif isinstance(TmpConfigs.frame_index, int):
            # TmpConfigs.frame_index += 1
            cls._refresh(abstract, seq)
        else:
            raise ValueError

    @classmethod
    def on_save_ori(cls):
        if TmpConfigs.save_ori != '' and cls._image_last is not None:
            dir_name = os.path.dirname(TmpConfigs.save_ori)
            os.makedirs(dir_name, exist_ok=True)
            cv2.imwrite(TmpConfigs.save_ori, cls._image_last)
            cls._L.info('Save original image to: %s' % TmpConfigs.save_ori)

    @classmethod
    def compare(cls):
        import tkinter
        # from tkinter import ttk
        root = tkinter.Tk()
        root.wm_geometry('320x720+1000+100')
        root.resizable(0, 0)
        cls._tracker_enabled.clear()
        tracker_btn = {}
        top_canvas = tkinter.Frame(root, bg='black')
        canvas = tkinter.Canvas(top_canvas)
        # canvas.place(x=0, y=0, height=600, width=500)
        scrollbar = tkinter.Scrollbar(top_canvas, orient="vertical", command=canvas.yview)
        # scrollbar.place(x=500, y=0, height=600)
        scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y, expand=True)
        canvas.pack(side=tkinter.RIGHT, fill='none', expand=True)
        top_canvas.pack(expand=True)

        canvas.configure(yscrollcommand=scrollbar.set)
        frame = tkinter.Frame(canvas)
        canvas.create_window((0, 0), window=frame, anchor='center')

        def roll_func(event):
            canvas.configure(scrollregion=canvas.bbox("all"), height=600)

        frame.bind("<Configure>", roll_func)
        tracker_list = list(cls.Trackers)
        tracker_list.sort()
        for tracker in tracker_list:
            var = tkinter.IntVar()
            cls._tracker_enabled[tracker] = var
            btn = tkinter.Checkbutton(frame, text=tracker, variable=var, onvalue=1, offvalue=0)
            btn.pack(anchor=tkinter.W)
            tracker_btn[tracker] = btn
        refresh_btn = tkinter.Button(root, text='refresh', command=cls.on_refresh)
        refresh_btn.pack(side=tkinter.TOP)

        # play_btn = tkinter.Button(root, text='play', command=cls.on_play)
        # play_btn.pack(side=tkinter.BOTTOM)

        def select_all():
            for t in cls.Trackers:
                cls._tracker_enabled[t].set(1)

        def diselect_all():
            for t in cls.Trackers:
                cls._tracker_enabled[t].set(0)

        select_all_btn = tkinter.Button(root, text='select all', command=select_all)
        select_all_btn.pack(side=tkinter.TOP)

        diselect_all_btn = tkinter.Button(root, text='diselect all', command=diselect_all)
        diselect_all_btn.pack(side=tkinter.TOP)

        save_ori_btn = tkinter.Button(root, text='save last image', command=cls.on_save_ori)
        save_ori_btn.pack(side=tkinter.TOP)

        root.mainloop()


ResultsAnalysis.Load(RESULTS_ANALYSIS_CONFIG_FILE)
ResultsAnalysis.Read()
ResultsAnalysis.compare()


