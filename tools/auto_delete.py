from bases.sv_dataset import DatasetBase
from bases.file_ops import Sequence, Attr
from tools.make_abs import AbsCreator
from tools.auto_label_attrs import LabelDataAttr


class AutoDelete(DatasetBase):

    @classmethod
    def Delete(cls, seq_name, index, orientation='after'):
        d = cls.D[seq_name]

        seq = Sequence(img_path=d['img_dir'],
                       poly_path=d['poly'],
                       rect_path=d['rect'],
                       state_path=d['state'])

        if orientation == 'after':
            seq.delete_after(index)
        elif orientation == 'before':
            seq.delete_before(index)
        else:
            cls._L.error('Unknown orientation, which must be in <after> or <before>!')
            return

        attr = Attr(d['attr'])

        LabelDataAttr.SetAll(rect=seq.rect_data,
                             state=seq.flags,
                             attr=attr.attrs)

        AbsCreator.Build(seq_name)



AutoDelete.Delete()
