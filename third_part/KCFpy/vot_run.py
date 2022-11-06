import numpy as np 
import cv2
import sys
sys.path.append('/root/data/remote_video/Tracking/Trackers/KCFpy')

from time import time

import kcftracker

import vot2020 as vot
from vot2020 import Rectangle, Polygon, Point


def get_axis_aligned_bbox(region):
    """ convert region to (cx, cy, w, h) that represent by axis aligned box
    """
    nv = region.size
    if nv == 8:
        cx = np.mean(region[0::2])
        cy = np.mean(region[1::2])
        x1 = min(region[0::2])
        x2 = max(region[0::2])
        y1 = min(region[1::2])
        y2 = max(region[1::2])
        A1 = np.linalg.norm(region[0:2] - region[2:4]) * \
            np.linalg.norm(region[2:4] - region[4:6])
        A2 = (x2 - x1) * (y2 - y1)
        s = np.sqrt(A1 / A2)
        w = s * (x2 - x1) + 1
        h = s * (y2 - y1) + 1
    else:
        x = region[0]
        y = region[1]
        w = region[2]
        h = region[3]
        cx = x+w/2
        cy = y+h/2
    return cx, cy, w, h

def main():
    tracker = kcftracker.KCFTracker(True, True, False)  # hog, fixed_window, multiscale

    handle = vot.VOT("rectangle")
    region = handle.region()
    # print(region)

    try:
        region = np.array([region[0][0][0], region[0][0][1], region[0][1][0], region[0][1][1],
                           region[0][2][0], region[0][2][1], region[0][3][0], region[0][3][1]])
    except:
        region = np.array(region)
    # print(region)
    cx, cy, w, h = get_axis_aligned_bbox(region)
    w = max(w, 2)
    h = max(h, 2)

    image_file = handle.frame()
    if not image_file:
        sys.exit(0)

    im = cv2.imread(image_file)  # HxWxC
    # init
    target_pos, target_sz = np.array([cx, cy]), np.array([w, h])
    gt_bbox_ = [cx-(w-1)/2, cy-(h-1)/2, w, h]

    tracker.init(gt_bbox_, im)


    while True:
        img_file = handle.frame()
        if not img_file:
            break
        im = cv2.imread(img_file)

        pred_bbox = tracker.update(im)


        result = Rectangle(*pred_bbox)
        score = 1
        # if cfg.MASK.MASK:
        #     pred_bbox = outputs['polygon']
        #     result = Polygon(Point(x[0], x[1]) for x in pred_bbox)

        handle.report(result, score)
