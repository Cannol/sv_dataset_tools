import cv2
import numpy as np
# from numba import jit


def get_outside_rect(poly_points, wh=False):
    rx, ry = np.max(poly_points, axis=0)
    lx, ly = np.min(poly_points, axis=0)

    if wh:
        return [lx, ly, rx-lx, ry-ly]

    return [lx, ly, rx, ry]


def get_image_patch_from_center_range(image, bbox, enlarged_range, scale):
    center_x = int(bbox[0] + 0.5 * bbox[2])
    center_y = int(bbox[1] + 0.5 * bbox[3])
    width = int(bbox[2] * enlarged_range)
    height = int(bbox[3] * enlarged_range)
    lx = int(max(center_x - width / 2, 0))
    ly = int(max(center_y - height / 2, 0))
    img = image[ly: ly+height, lx: lx+width, :]

    new_x = int(round((bbox[0] - lx) * scale))
    new_y = int(round((bbox[1] - ly) * scale))
    new_w = int(round(bbox[2] * scale))
    new_h = int(round(bbox[3] * scale))

    img_out = cv2.resize(img, (width*scale, height*scale), cv2.INTER_LANCZOS4)
    return img_out, [new_x, new_y, new_w, new_h], [lx, ly]


def get_bbox_iou_xywh(bbox1, bbox2):
    xmin1 = bbox1[0]
    ymin1 = bbox1[1]
    xmax1 = bbox1[0] + bbox1[2]
    ymax1 = bbox1[1] + bbox1[3]

    xmin2 = bbox2[0]
    ymin2 = bbox2[1]
    xmax2 = bbox2[0] + bbox2[2]
    ymax2 = bbox2[1] + bbox2[3]

    inter_x = max(xmin1, xmin2)
    inter_y = max(ymin1, ymin2)
    inter_xx = min(xmax1, xmax2)
    inter_yy = min(ymax1, ymax2)

    area_union = bbox1[2] * bbox1[3] + bbox2[2] * bbox2[3]

    inter_area = max(0, inter_xx-inter_x) * max(0, inter_yy-inter_y)
    if inter_area == area_union:
        return inter_area / 1e-6
    return inter_area / (area_union - inter_area)


def get_bbox_distance_xywh(bbox1, bbox2):
    return (bbox1[0] + bbox2[0] + 0.5 * (bbox1[2] - bbox2[2]))**2 \
           + (bbox1[1] + bbox2[1] + 0.5 * (bbox1[3] - bbox2[3]))**2


def merge2routes(bbox_route1, bbox_route2, theta1, theta2):
    assert len(bbox_route1) == len(bbox_route2)

    if theta1 == 0:
        return bbox_route2
    elif theta2 == 0:
        return bbox_route1

    # print(theta1, theta2)

    length = len(bbox_route1)
    weights = np.linspace(0, 1, length)

    if theta1 == theta2:
        pass
    elif theta1 > theta2:
        weights = -np.power(weights, theta1/theta2) + 1
    elif theta1 < theta2:
        weights = -np.power(1-weights, theta2/theta1)

    weights = np.reshape(weights, (-1, 1))
    bbox_route1 = np.array(bbox_route1)
    bbox_route2 = np.array(bbox_route2)
    merged_boxes = bbox_route2 * weights + (1-weights) * bbox_route1
    return merged_boxes.tolist()

