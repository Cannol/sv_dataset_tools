from typing import Dict
import os
import sys
import shutil
import xml.dom.minidom
import numpy as np
import tqdm
import datetime
import cv2
from bases.targets import Target


def make_voc_dataset(root_path, dataset_name, video_name, crop_range, owner_name, image_shape, targets: Dict[str, Target], frame_list:list):
    length = len(frame_list)
    crop_range_text = '_'.join(list(map(str, crop_range)))
    date = datetime.date.today()
    save_date = '%04d%02d%02d' % (date.year, date.month, date.day)
    out_path = os.path.join(root_path, '%s_%s_%s' % (video_name, crop_range_text, save_date))
    folder = os.path.basename(out_path)

    os.makedirs(out_path, exist_ok=True)

    anno_path = os.path.join(out_path, 'Annotations')
    tiff_path = os.path.join(out_path, 'TIFFImages')
    demo_path = os.path.join(out_path, 'DemoImages')
    os.makedirs(anno_path, exist_ok=True)
    os.makedirs(tiff_path, exist_ok=True)
    os.makedirs(demo_path, exist_ok=True)

    for i, frame_file in tqdm.tqdm(enumerate(frame_list)):

        img_name = '%06d.tiff' % (i+1)
        xml_name = '%06d.xml' % (i+1)

        # copying image files
        out_tiff_file = os.path.join(tiff_path, img_name)
        shutil.copy(frame_file, out_tiff_file)

        # making xml files
        objects_for_each_frame = []
        cls_all = set()

        # get all visible targets
        for target_name in targets:
            target = targets[target_name]
            flag, poly = target.get_rect_poly(i)
            if flag and target.state_flags[i] == 0:
                obj_dict = {}
                x, y = poly[:, 0], poly[:, 1]
                obj_dict['cls_name'] = target.class_name
                obj_dict['bndbox'] = [np.min(x), np.min(y), np.max(x), np.max(y)]
                obj_dict['id'] = target.name
                obj_dict['keyframe'] = target.key_frame_flags[i, 2]
                objects_for_each_frame.append(obj_dict)
                cls_all.add(target.class_name)

        if len(objects_for_each_frame) == 0:
            continue

        # create demo image
        img = cv2.imread(frame_file)
        for obj in objects_for_each_frame:
            x, y, xx, yy = obj['bndbox']

            cv2.rectangle(img, (int(round(x)), int(round(y))), (int(round(xx)), int(round(yy))), [0, 0, 255], 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(demo_path, img_name), img)

        # create xml file object and root node
        doc = xml.dom.minidom.Document()
        root_node = doc.createElement("annotation")
        doc.appendChild(root_node)

        # create folder node
        folder_node = doc.createElement("folder")
        folder_value = doc.createTextNode(folder)
        folder_node.appendChild(folder_value)
        root_node.appendChild(folder_node)

        # create filename node
        filename_node = doc.createElement("filename")
        filename_value = doc.createTextNode(img_name)
        filename_node.appendChild(filename_value)
        root_node.appendChild(filename_node)

        # create owner node
        owner_node = doc.createElement("owner")
        owner_node.appendChild(doc.createTextNode(owner_name))
        root_node.appendChild(owner_node)

        # create source node
        source_node = doc.createElement("source")
        dataset_node = doc.createElement("dataset_name")
        dataset_node.appendChild(doc.createTextNode(dataset_name))
        source_node.appendChild(dataset_node)
        video_frame_node = doc.createElement("frame_now")
        video_frame_node.appendChild(doc.createTextNode(str(i+1)))
        source_node.appendChild(video_frame_node)
        video_frame_total_node = doc.createElement("frame_total")
        video_frame_total_node.appendChild(doc.createTextNode(str(length)))
        root_node.appendChild(source_node)

        # create classes node
        classes_node = doc.createElement("categories")
        cls_all_list = list(cls_all)
        cls_all_list.sort()
        class_count_node = doc.createElement("count")
        class_count_node.appendChild(doc.createTextNode(str(len(cls_all_list))))
        class_names_node = doc.createElement("name_list")
        class_names_node.appendChild(doc.createTextNode(','.join(cls_all_list)))
        classes_node.appendChild(class_count_node)
        classes_node.appendChild(class_names_node)
        root_node.appendChild(classes_node)

        # create size node
        size_node = doc.createElement("size")
        image_width, image_height, depth = image_shape
        for item, value in zip(["width", "height", "depth"], [image_width, image_height, depth]):
            elem = doc.createElement(item)
            elem.appendChild(doc.createTextNode(str(value)))
            size_node.appendChild(elem)
        root_node.appendChild(size_node)

        # create segmented node
        seg_node = doc.createElement("segmented")
        seg_node.appendChild(doc.createTextNode(str(0)))
        root_node.appendChild(seg_node)

        # create object node
        for _object in objects_for_each_frame:
            obj_node = doc.createElement("object")
            name_node = doc.createElement("name")
            name_node.appendChild(doc.createTextNode(_object['cls_name']))
            obj_node.appendChild(name_node)

            id_node = doc.createElement("id")
            id_node.appendChild(doc.createTextNode(_object['id']))
            obj_node.appendChild(id_node)

            keyframe_node = doc.createElement("keyframe")
            keyframe_node.appendChild(doc.createTextNode(str(_object['keyframe'])))
            obj_node.appendChild(keyframe_node)

            diff_node = doc.createElement("difficult")
            diff_node.appendChild(doc.createTextNode(str(0)))
            obj_node.appendChild(diff_node)

            bndbox_node = doc.createElement("bndbox")
            for item, value in zip(["xmin", "ymin", "xmax", "ymax"], _object['bndbox']):
                elem = doc.createElement(item)
                elem.appendChild(doc.createTextNode(str(value)))
                bndbox_node.appendChild(elem)
            obj_node.appendChild(bndbox_node)
            root_node.appendChild(obj_node)

        with open(os.path.join(anno_path, xml_name), "w", encoding="utf-8") as f:
            # writexml()第一个参数是目标文件对象，第二个参数是根节点的缩进格式，第三个参数是其他子节点的缩进格式，
            # 第四个参数制定了换行格式，第五个参数制定了xml内容的编码。
            doc.writexml(f, indent='', addindent='\t', newl='\n', encoding="utf-8")
    return out_path







