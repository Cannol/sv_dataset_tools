from bases.sv_dataset import DatasetBase
from bases.file_ops import Sequence, Attr
# from tools.make_abs import AbsCreator
from tools.auto_label_attrs import LabelDataAttr


class AutoDelete(DatasetBase):

    @classmethod
    def DeleteLast(cls, seq_name, num):
        d = cls.D[seq_name]
        seq = Sequence(img_path=d['img_dir'],
                       poly_path=d['poly'],
                       rect_path=d['rect'],
                       state_path=d['state'])
        seq.delete_last(num)

        seq.state_save()
        seq.label_save()

        attr = Attr(d['attr'])

        attr_new = attr.attrs.copy()

        LabelDataAttr.SetAll(rect=seq.rect_data,
                             state=seq.flags,
                             attr=attr_new)

        attr.save_attrs(attr_new)

    @classmethod
    def Delete(cls, seq_name, frame_num, orientation='after'):
        index = frame_num - 1
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

        seq.state_save()
        seq.label_save()

        attr = Attr(d['attr'])

        attr_new = attr.attrs.copy()

        LabelDataAttr.SetAll(rect=seq.rect_data,
                             state=seq.flags,
                             attr=attr_new)

        attr.save_attrs(attr_new)


AutoDelete.Delete('03.000028', 663, 'after')
#
# all_list = AutoDelete.ParseNameList('03.*')
# all_list.pop(0)
# for name in all_list:
#     AutoDelete.DeleteLast(name, 3)