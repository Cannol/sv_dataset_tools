from bases.targets import Target
import os
import numpy as np
import cv2
import random

from configs import VIDEO_IDS_TXT

video_ids = {}
with open(VIDEO_IDS_TXT) as f:
    lines = f.readlines()
for line in lines:
    a, b = line.strip().split(' ')
    video_ids[a] = b

path = r'D:\Sanatar\Desktop\标注结果'
Use_Map = False
maps_dir = r'E:\ORSV_coll\pics'
out_file = r'D:\Sanatar\Desktop\results'
os.makedirs(out_file, exist_ok=True)
names = os.listdir(path)
names.sort()
Target.SetLength(1)


def get_color_randomly():
    return [int(round(255 * random.random())), int(round(255 * random.random())), int(round(255 * random.random()))]


contents = []
for name in names:
    meta_dir = os.path.join(path, name, 'targets')
    vid = name.split('_')[0]
    print('==== ', name, meta_dir, ' ====')
    meta_files = [os.path.join(meta_dir, i) for i in os.listdir(meta_dir) if i.endswith('.meta')]
    if Use_Map:
        big_map = cv2.imread(os.path.join(maps_dir, '%s.tiff' % video_ids[vid]))
    else:
        big_map = np.zeros((5000, 12000, 3), 'uint8')
    for meta_file in meta_files:
        try:
            target = Target.MakeNewFromJsonFile(meta_file)
        except Exception as e:
            print('ERROR --> %s' % meta_file)
            continue
        cps = target.get_route()
        color = get_color_randomly()
        cps = cps.astype('int')
        cps = cps.reshape((-1, 1, 2))
        cv2.polylines(big_map, [cps], False, color, 1, lineType=cv2.LINE_AA)
    # cv2.imshow('show', big_map)
    # cv2.waitKey(0)
    if Use_Map:
        cv2.imwrite(os.path.join(out_file, '%s-map.tiff' % vid), big_map)
    else:
        cv2.imwrite(os.path.join(out_file, '%s.tiff' % vid), big_map)
