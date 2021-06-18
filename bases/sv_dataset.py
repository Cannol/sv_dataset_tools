from common import YamlConfigClassBase, LoggerMeta
from configs import DATASET_CONFIG_FILE
import os
import numpy as np
from logging import Logger


class DatasetBase(YamlConfigClassBase, metaclass=LoggerMeta):
    _L: Logger = None

    DataRoot: str = ''
    VideoList: list = []
    VideoName: list = []

    AnnosDirName: str = ''
    SeqDirName: str = ''
    AttrPostfix: str = ''
    StatePostfix: str = ''
    RectPostfix: str = ''
    PolyPostfix: str = ''
    AbsPostfix: str = ''

    AttrsCH: list = []
    AttrsEN: list = []

    D = {}
    # V_DIRS = {}

    _DName = ['seq_name', 'img_dir', 'attr', 'state', 'rect', 'poly']

    def debug(self):
        print(self.DataRoot)
        print(self.VideoList)
        print(self.AnnosDirName)
        print(self.SeqDirName)
        print(self.AttrPostfix)
        print(self.StatePostfix)
        print(self.RectPostfix)
        print(self.PolyPostfix)

    @classmethod
    def Read(cls):
        for video in cls.VideoList:
            seqs_dir = os.path.join(cls.DataRoot, video, cls.SeqDirName)
            annos = os.path.join(cls.DataRoot, video, cls.AnnosDirName)
            # cls.V_DIRS[video] = {'seqs_dir': seqs_dir, 'annos': annos}

            seqs = [s for s in os.listdir(seqs_dir) if not s.startswith('.')]

            for seq in seqs:
                d = dict()
                d['seq_name'] = '%s.%s' % (video, seq)
                d['img_dir'] = os.path.join(seqs_dir, seq)
                d['attr'] = os.path.join(annos, '%s%s' % (seq, cls.AttrPostfix))
                d['state'] = os.path.join(annos, '%s%s' % (seq, cls.StatePostfix))
                d['rect'] = os.path.join(annos, '%s%s' % (seq, cls.RectPostfix))
                d['poly'] = os.path.join(annos, '%s%s' % (seq, cls.PolyPostfix))
                d['abs'] = os.path.join(annos, '%s%s' % (seq, cls.AbsPostfix))

                cls.D[d['seq_name']] = d

        cls._L.info('Read %d records in %d videos from dataset [%s]' % (len(cls.D), len(cls.VideoList), cls.DataRoot))

    @classmethod
    def WriteIntoObj(cls, dict_name):
        v = cls.D.get(dict_name)
        if v is None:
            return None
        obj = cls()
        for name in cls._DName:
            if hasattr(obj, name):
                setattr(obj, name, v[name])
            else:
                cls._L.debug('Object [{}] does not have Key [{}], skipped!'.format(obj, name))
        return obj

    @classmethod
    def GetAllX(cls, x_key):
        x = {}
        for d in cls.D:
            x[d] = (cls.D[d][x_key])
        return x

    @classmethod
    def toCenter(cls, rects):
        rects_np = np.array(rects, dtype='float')
        rects_np[:, 0, 0] += (rects_np[:, 1, 0]/2)
        rects_np[:, 0, 1] += (rects_np[:, 1, 1]/2)
        return rects_np

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


DatasetBase.Load(DATASET_CONFIG_FILE)
DatasetBase.Read()
