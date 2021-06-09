from common import YamlConfigClassBase, LoggerMeta
from configs import DATASET_CONFIG_FILE
import os
from logging import Logger


class DatasetBase(YamlConfigClassBase, metaclass=LoggerMeta):
    _L: Logger = None

    DataRoot: str = ''
    VideoList: list = []

    AnnosDirName: str = ''
    SeqDirName: str = ''
    AttrPostfix: str = ''
    StatePostfix: str = ''
    RectPostfix: str = ''
    PolyPostfix: str = ''

    AttrsCH: list = []
    AttrsEN: list = []

    D = {}

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

            seqs = os.listdir(seqs_dir)

            for seq in seqs:
                d = dict()
                d['seq_name'] = '%s.%s' % (video, seq)
                d['img_dir'] = os.path.join(seqs_dir, seq)
                d['attr'] = os.path.join(annos, '%s%s' % (seq, cls.AttrPostfix))
                d['state'] = os.path.join(annos, '%s%s' % (seq, cls.StatePostfix))
                d['rect'] = os.path.join(annos, '%s%s' % (seq, cls.RectPostfix))
                d['poly'] = os.path.join(annos, '%s%s' % (seq, cls.PolyPostfix))

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
        x = []
        for d in cls.D:
            x.append(cls.D[d][x_key])
        return x


DatasetBase.Load(DATASET_CONFIG_FILE)
DatasetBase.Read()
