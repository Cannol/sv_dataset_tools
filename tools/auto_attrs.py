from bases.sv_dataset import DatasetBase
from bases.file_ops import read_state_file
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
    def _analysis_BCL(cls):
        states = cls.GetAllX('state')
        state_matrix = []
        # 主要统计state中1的个数分布
        for state_filename in states:
            s = read_state_file(state_filename)
            c = np.sum(s == 1)
            if c > 0:
                state_matrix.append(c)
        print(state_matrix)
        plt.hist(state_matrix, bins=10)
        plt.show()
        return cls(1, state_matrix, 'hist')


a: AnalysisData = AnalysisData.AnalysisAttr('BCL')
# a.analysis_count()
