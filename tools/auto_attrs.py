from bases.sv_dataset import DatasetBase
from bases.file_ops import read_state_file, read_text
import numpy as np
import matplotlib.pyplot as plt

"""
用来自动生成序列的attribute：
 - CO, BCL, STO, LTO, SM, IPR
"""


class AnalysisData(DatasetBase):
    def __init__(self, data_type, data, graph):
        super().__init__()
        self.type = data_type
        self.data = data
        self.graph = graph

    @classmethod
    def AnalysisAttr(cls, attr_name):
        func = getattr(cls, '_analysis_%s' % attr_name)
        return func()

    @classmethod
    def _analysis_MV(cls):
        rects = cls.GetAllX('rect')
        names = list(rects)
        names.sort()

        low = []
        high = []

        for i, name in enumerate(names):
            rect_file = rects[name]
            rect = np.array(read_text(rect_file))
            center_np = cls.toCenter(rect)
            sp = center_np[1:, 0, :] - center_np[:-1, 0, :]
            speed = np.sqrt(np.square(sp[:, 0]) + np.square(sp[:, 1]))
            avg_speed = np.zeros((len(speed)-5+1))
            for j in range(len(speed)-5+1):
                avg_speed[j] = np.average(speed[j:j+5]) * 10
            t = np.min(avg_speed)
            low.append(t)
            high.append(np.max(avg_speed) - t)
            if i == 0:
                print(low, high)
            if high[-1] > 40:
                print(name)
                low[-1] = 0
                high[-1] = 0

        width = 1
        fig, ax = plt.subplots(figsize=(20, 8), dpi=200)
        x = np.arange(len(names)) + 1

        ax.bar(x, high, bottom=low, width=width, align='edge')

        plt.show()












    @classmethod
    def _analysis_OS(cls):
        rects = cls.GetAllX('rect')

        rects_np = np.zeros(len(rects), dtype='float')

        for i, name in enumerate(rects):
            rect_file = rects[name]
            rect = np.array(read_text(rect_file))

            rects_np[i] = np.average(np.sqrt(np.square(rect[:, 1, 0]) + np.square(rect[:, 1, 1])))

        plt.hist(rects_np, bins=100, facecolor="blue", edgecolor="black", alpha=0.7)

        plt.hist(rects_np, rwidth=0.9, kind='kde')

        plt.grid(ls=":", lw=1, color="gray", alpha=0.2)

        plt.show()

    @classmethod
    def _analysis_STATE(cls):
        states = cls.GetAllX('state')
        state_inv = []
        state_occ = []
        # 主要统计state中1的个数分布

        video_np = np.zeros((len(cls.VideoList), len(states)), dtype='float')
        video_count = np.zeros(len(cls.VideoList)+1, dtype='int')
        video_count[0] = 1
        color_map = ['mistyrose', 'seashell', 'lemonchiffon', 'honeydew', 'lightcyan', 'azure']
        video_desc = []
        video_len = np.zeros(len(states), dtype='int')

        names = list(states)
        names.sort()
        for i, name in enumerate(names):
            state_filename = states[name]
            s = read_state_file(state_filename)
            a = np.sum(s == 0)
            v, _ = name.split('.')
            video_np[int(v)-1, i] = a / len(s)
            video_count[int(v)] += 1
            a = np.sum(s == 1)
            state_inv.append(a/len(s))
            a = np.sum(s == 2)
            state_occ.append(a/len(s))
            video_len[i] = len(s)
        for i in range(1, len(video_count)):
            video_desc.append('%s-%s(%d)' % (cls.VideoList[i-1], cls.VideoName[i-1], video_count[i]))
            video_count[i] += video_count[i-1]
        for i in range(len(video_count)-1):
            video_count[i] = (video_count[i] + video_count[i+1]) // 2

        nor = []
        for a, b in zip(state_inv, state_occ):
            nor.append(a+b)
        width = 1
        fig, ax = plt.subplots(figsize=(20, 8), dpi=200)
        x = np.arange(len(states))+1
        avg_inv = np.sum(state_inv)/np.sum(np.array(state_inv) > 0) * 100
        ax.bar(x, state_inv, width=width, label='INV (AVG=%.2f%%)' % avg_inv, align='edge')
        avg_occ = np.sum(state_occ)/np.sum(np.array(state_occ) > 0) * 100
        ax.bar(x, state_occ, bottom=state_inv, width=width, label='OCC (AVG=%.2f%%)' % avg_occ, align='edge')
        ax.legend(fontsize=13)
        ax.set_ylabel('Percentage of Frame State Flags', fontsize=13)
        plt.tick_params(labelsize=12)
        for i in range(len(cls.VideoList)):
            ax.bar(x, video_np[i, :], bottom=nor, width=width, color=color_map[i], label='NOR', align='edge')
        plt.ylim((0.0, 0.7))
        plt.xticks(video_count[:-1], labels=video_desc)

        ax_right = ax.twinx()
        ax_right.bar(x, np.ones_like(video_len)+1, bottom=video_len-2, width=width, color='red', align='edge')
        ax_right.set_ylabel('Number of Frames in Each Video', fontsize=13)
        plt.ylim((0, 800))

        plt.savefig('../output/datadis1.pdf')
        plt.show()


p: AnalysisData = AnalysisData.AnalysisAttr('MV')
# a.analysis_count()
