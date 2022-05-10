import cv2
import numpy as np


def get_diff_image(image_list, out_list):

    assert len(image_list) == len(out_list), 'image_list and out_list must have the same length! (%d v.s. %d)' \
                                             % (len(image_list), len(out_list))

    a = cv2.imread(image_list[0])
    a = a.astype('float')
    a -= np.mean(a, axis=(0, 1))
    for image_file, diff_file in zip(image_list[1:], out_list[1:]):
        b = cv2.imread(image_file)
        b = b.astype('float')
        b -= np.mean(b, axis=(0, 1))
        c = np.mean(np.abs(a - b), axis=2)
        nums, values = np.histogram(c, 256)
        mm = []
        for i, num in enumerate(nums[int(len(nums)/2):]):
            if num < 10:
                mm.append(values[i+int(len(nums)/2)])

        # _min = min(mm)
        _max = max(mm)
        # c -= _min
        # c[c < 0] = 0
        c[c > _max] = _max - 0.1
        output_c = np.round(((c-np.min(c)) / (_max - np.min(c))) * 255).astype('int8')
        # cv2.imwrite(diff_file, output_c)
        cv2.imshow('re', output_c)
        cv2.waitKey(100)
        a = b


import os
path = '/home/cannol/codes/sv_dataset_tools/tmp/01a658de4fc2b58208b2af5c9c156323'
l = [os.path.join(path, i) for i in os.listdir(path) if i.endswith('tiff')]
l_out = [os.path.join(path, 'diff-%s' % i) for i in os.listdir(path) if i.endswith('tiff')]
l.sort()
l_out.sort()

get_diff_image(l, l_out)
