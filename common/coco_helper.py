from typing import Dict
import os
import shutil
import numpy as np
import tqdm
import datetime
from bases.targets import Target
from common.json_helper import JsonTransBase


class BaseInfo(JsonTransBase):
    def __init__(self):
        self.description = ''
        self.url = None
        self.version = 1.0
        self.year = 2022
        self.contributor = 'IPIU Lab @Xidian University'
        self.date_created = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.video_length = 0
        self.video_name = ""
        self.crop_range = []
        self.color_channels = 0


class Licenses(JsonTransBase):
    def __init__(self):
        self.url = ""
        self.id = 0
        self.name = ""


class Images(JsonTransBase):
    def __init__(self):
        self.license = 0
        self.file_name = ""
        self.height = 0
        self.width = 0
        self.date_captured = ""
        self.id = 1


class Annotations(JsonTransBase):
    def __init__(self):
        self.area = 1.0
        self.iscrowd = 0
        self.image_id = 0
        self.bbox = []
        self.category_id = 0
        self.id = 0
        self.keyframe = 0


class Categories(JsonTransBase):
    def __init__(self):
        self.supercategory = ''
        self.id = 0
        self.name = ''

    @classmethod
    def MakeIPIUDefault(cls):
        cls_super = ['vehicle', 'vehicle', 'ship', 'airplane', 'train']
        cls_names = ['vehicle', 'large-vehicle', 'ship', 'airplane', 'train']

        default_list = []
        _id_dict = {}
        for i, (cs, cn) in enumerate(zip(cls_super, cls_names)):
            obj = cls()
            obj.id = i + 1
            obj.name = cn
            obj.supercategory = cs
            default_list.append(obj)
            _id_dict[cn] = i + 1

        return default_list, _id_dict


class Targets(JsonTransBase):
    def __init__(self):
        self.id = 0
        self.name = ''
        self.category_id = 0

class COCOJsonFile(JsonTransBase):
    """
    The format is designed for Satellite Video dataset with COCO format,
    which is something different from the official COCO format.
    """

    def __init__(self):
        self.info = {}
        self.licenses = []
        self.images = []
        self.annotations = []
        self.categories = []
        self.type = ''

class IPIUCOCOJsonFile(JsonTransBase):
    """
    The format is designed for Satellite Video dataset with COCO format,
    which is something different from the official COCO format.
    """

    _dict = {
        'licenses': Licenses,
        "images": Images,
        "annotations": Annotations,
        "categories": Categories,
        "targets": Targets
    }

    def __init__(self):
        self.info = BaseInfo()
        self.licenses = []
        self.images = []
        self.annotations = []
        self.categories = []
        self.targets = []

    def from_dict(self, obj_dict: dict):
        self.info = BaseInfo.FromJsonDict(obj_dict.pop('info'))

        for key in obj_dict:
            value = obj_dict[key]
            assert isinstance(value, list), type(value)
            assert key in self._dict.keys(), key
            cls: JsonTransBase = self._dict[key]
            lst: list = getattr(self, key)
            for item in value:
                lst.append(cls.FromJsonDict(item))


def make_coco_dataset(root_path, dataset_name, video_name: str, crop_range, owner_name, image_shape,
                      targets: Dict[str, Target], frame_list: list, version=1.0):
    length = len(frame_list)
    crop_range_text = '_'.join(list(map(str, crop_range)))
    date = datetime.date.today()
    save_date = '%04d%02d%02d' % (date.year, date.month, date.day)
    out_path = os.path.join(root_path, '%s_%s_%s' % (video_name, crop_range_text, save_date))

    date_captured = video_name.split('_')[2]
    date_captured = '%s-%s-%s %s:%s:%s' % (date_captured[:4], date_captured[4:6], date_captured[6:8],
                                           date_captured[8:10], date_captured[10:12], date_captured[12:14])

    os.makedirs(out_path, exist_ok=True)

    tiff_path = os.path.join(out_path, 'TIFFImages')
    # demo_path = os.path.join(out_path, 'DemoImages')
    os.makedirs(tiff_path, exist_ok=True)
    # os.makedirs(demo_path, exist_ok=True)

    file = IPIUCOCOJsonFile()
    file.info.description = dataset_name
    file.info.url = None
    file.info.version = version
    file.info.year = date.year
    file.info.contributor = owner_name
    file.info.video_length = length
    file.info.video_name = video_name
    file.info.crop_range = crop_range
    file.info.color_channels = image_shape[2]

    lic = Licenses()
    lic.id = 1
    lic.url = ""
    lic.name = "Experimental Dataset, No Public, No Commercial Use"
    file.licenses.append(lic)

    # make default categories
    file.categories, cls_id_dict = Categories.MakeIPIUDefault()

    target_list = list(targets)

    target_id_dict = {}
    for i, target_name in enumerate(target_list):
        t = Targets()
        t.id = i + 1
        t.name = targets[target_name].name
        t.category_id = cls_id_dict[targets[target_name].class_name]
        file.targets.append(t)
        target_id_dict[target_name] = i + 1

    for i, frame_file in tqdm.tqdm(enumerate(frame_list)):

        img_name = '%06d.tiff' % (i+1)

        img = Images()
        img.license = lic.id
        img.file_name = img_name
        img.width, img.height, _ = image_shape
        img.date_captured = date_captured
        img.id = i + 1
        file.images.append(img)

        # copying image files
        out_tiff_file = os.path.join(tiff_path, img_name)
        shutil.copy(frame_file, out_tiff_file)

        # get all visible targets
        for target_name in target_list:
            target = targets[target_name]
            flag, poly = target.get_rect_poly(i)
            if flag and target.state_flags[i] == 0:
                anno = Annotations()
                anno.id = target_id_dict[target_name] * 1000 + img.id
                anno.image_id = img.id
                anno.category_id = cls_id_dict[target.class_name]
                anno.iscrowd = 0

                x, y = poly[:, 0], poly[:, 1]
                x1, y1, x2, y2 = np.min(x), np.min(y), np.max(x), np.max(y)
                anno.bbox = [x1, y1, x2-x1, y2-y1]
                anno.keyframe = int(target.key_frame_flags[i, 2])
                anno.area = anno.bbox[2] * anno.bbox[3]
                file.annotations.append(anno)


        # # create demo image
        # img = cv2.imread(frame_file)
        # for obj in objects_for_each_frame:
        #     x, y, xx, yy = obj['bndbox']
        #
        #     cv2.rectangle(img, (int(round(x)), int(round(y))), (int(round(xx)), int(round(yy))), [0, 0, 255], 1, cv2.LINE_AA)
        # cv2.imwrite(os.path.join(demo_path, img_name), img)

    save_json = os.path.join(out_path, 'detection_all.json')
    file.Json = os.path.join(save_json)

    print('>> Annotation file saved: %s' % save_json)

    cls_names = {'vehicle': 0, 'large-vehicle': 0, 'ship': 0, 'airplane': 0, 'train': 0}
    for t in targets:
        target = targets[t]
        cls_names[target.class_name] += 1

    with open(os.path.join(root_path, 'count.txt'), 'a+') as f:
        f.write('%s,%d,%d,%d,%d,%d,%d\n' % (video_name, len(file.annotations),
                                            cls_names['vehicle'],
                                            cls_names['large-vehicle'],
                                            cls_names['ship'],
                                            cls_names['airplane'],
                                            cls_names['train']))

    return out_path



if __name__ == '__main__':
    # ipiu = IPIUCOCOJsonFile.MakeNewFromJsonFile('/data1/VISO_dataset/coco/car/annotations/instances_val2017.json')
    ipiu = COCOJsonFile.MakeNewFromJsonFile('/data1/VISO_dataset/coco/car/annotations/instances_test2017.json')
    print()
    ipiu.categories = [
        {"supercategory": '',
        "id": 1,
        "name": 'car'}
    ]
    ipiu.Json = '/data1/VISO_dataset/coco/car/annotations/instances_test2017_.json'
#     file = IPIUCOCOJsonFile()
#     for i in range(10):
#         file.images.append(Images())
#     d = file.Json
#     xx = IPIUCOCOJsonFile.MakeNewFromJson(d)
#     print()



