from bases.sv_dataset import DatasetBase
from bases.file_ops import read_state_file, read_text, Attr
import numpy as np
import matplotlib.pyplot as plt

"""
用来自动生成序列的attribute：
 - STO, LTO, SM, CO, BCL
  - '[STO] Short-Term Occlusion'     - '短时遮挡：出现过遮挡帧数不超过50帧的短时遮挡现象至少1次'                         
  - '[LTO] Long-Term Occlusion'      - '长时遮挡：出现过遮挡帧数超过50帧的长时遮挡现象至少1次'                          
  - '[SM] Slow Motion'               - '慢速运动：目标运动速度低于每帧X个像素'     # X有待确定                       
  - '[CO] Continuous Occlusion'      - '连续遮挡：出现过2次或2次以上长短时遮挡'                                  
  - '[BCL] Background Cluster'       - '背景相似：目标与背景融为一体，且无明显遮挡物'                                
"""


class LabelDataAttr(DatasetBase):
    def __init__(self):
        super().__init__()
        pass

    @classmethod
    def SetAll(cls, rect, state, attr):
        STO, LTO, CO = cls.get_OCC_flag(state)
        SM = cls.get_SM_flag_rect(rect)
        BCL = cls.get_BCL_flag(state)

        attr[0] = STO
        attr[1] = LTO
        attr[7] = CO
        attr[5] = SM
        attr[8] = BCL

    @classmethod
    def Auto_label(cls):
        states = cls.GetAllX('state')
        attrs = cls.GetAllX('attr')
        rects = cls.GetAllX('rect')

        names = list(states)
        names.sort()
        for i, name in enumerate(names):
            state_filename = states[name]
            attr_filename = attrs[name]
            rect_file = rects[name]

            s = read_state_file(state_filename)
            attr = Attr(attr_filename)
            # attr.read_attrs()
            print(attr.attrs)

            this_attr = attr.attrs.copy()

            STO, LTO, CO = cls.get_OCC_flag(s)

            SM = cls.get_SM_flag(rect_file)

            BCL = cls.get_BCL_flag(s)

            # - '[STO] Short-Term Occlusion'
            # - '[LTO] Long-Term Occlusion'
            # - '[DS] Dense Similarity'
            # - '[IV] Illumination Variation'
            # - '[BCH] Background Change'
            # - '[SM] Slow Motion'
            # - '[ND] Natural Disturbance'
            # - '[CO] Continuous Occlusion'
            # - '[BCL] Background Cluster'
            # - '[IPR] In-Plane Rotation'
            this_attr[0] = STO
            this_attr[1] = LTO
            this_attr[7] = CO
            this_attr[5] = SM
            this_attr[8] = BCL

            attr.save_attrs(this_attr)

    # STO, LTO, CO
    @classmethod
    def get_OCC_flag(cls, state):
        occ_num = 0
        occ_min_len = 999999
        occ_max_len = 0

        occ_state = state == 2
        occ_flag = occ_state[:-1] != occ_state[1:]
        occ_ind = np.argwhere(occ_flag)
        if len(occ_ind) < 1:
            return False, False, False

        occ_start = 0
        for ind in occ_ind:
            if not occ_start:
                occ_start = ind + 1
                continue
            else:
                end = ind
                occ_num += 1
                occ_len = end - occ_start + 1
                occ_min_len = min(occ_len, occ_min_len)
                occ_max_len = max(occ_len, occ_max_len)
                occ_start = 0

        if occ_start:
            occ_num += 1
            occ_len = len(state) - occ_start
            occ_min_len = min(occ_len, occ_min_len)
            occ_max_len = max(occ_len, occ_max_len)

        sto = True if 0 < occ_min_len < 50 else False
        lto = True if occ_max_len >= 50 else False
        co = True if occ_num >= 2 else False
        return sto, lto, co

    @classmethod
    def get_SM_flag(cls, rect_file, threshold=1):
        rect = np.array(read_text(rect_file))
        return cls.get_SM_flag_rect(rect, threshold)

    @classmethod
    def get_SM_flag_rect(cls, rect, threshold=1):
        center_np = cls.toCenter(rect)
        sp = center_np[1:, 0, :] - center_np[:-1, 0, :]
        speed = np.sqrt(np.square(sp[:, 0]) + np.square(sp[:, 1]))
        avg_speed = np.zeros((len(speed) - 5 + 1))
        for j in range(len(speed) - 5 + 1):
            avg_speed[j] = np.average(speed[j:j + 5]) * 10
        if np.sum(avg_speed < threshold):
            return True
        else:
            return False

    @classmethod
    def get_BCL_flag(cls, state):
        return True if np.sum(state == 1) >= 10 else False


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
            if high[-1] > 40:
                print(name)

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
#
#
# # p: LabelDataAttr = AnalysisData.AnalysisAttr('MV')
#
# LabelDataAttr.Auto_label()
# # pp: LabelDataAttr = LabelDataAttr()
# # pp.Auto_label()
# # a.analysis_count()
