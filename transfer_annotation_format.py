import os
import numpy as np

from bases.targets import Target
from bases.file_ops import read_state_file
from bases.file_ops import read_text
from bases.abs_file import Abstract

Target.SetLength(327)
# Target.SetGlobalOffsize(0, 0, 12000, 5000)

global_off_x = 4549
global_off_y = 1942
Target.SetGlobalOffsize(0, 0, 12000, 5000)

source_dir = r'F:\dataset\002car_refix01\refix01'
dst_dir = r'F:\dataset\output'

Target.SetDefaultSavingPath(dst_dir)

all_targets = {}

for group in os.listdir(source_dir):
    path = os.path.join(source_dir, group, 'annotations')
    filenames = [i.split('.')[0] for i in os.listdir(path) if i.endswith('.abs')]
    for filename in filenames:
        all_targets[filename] = os.path.join(path, filename)

num_set1 = set()
num_set2 = set()
# def find_end(rects):
#     end = 0
#     for r in rects:
#         if r[0] == -1

for target_name in all_targets:
    basename = all_targets[target_name]
    abs_file = Abstract.MakeNewFromJsonFile(basename+'.abs')
    state = read_state_file(basename+'.state')
    rect = np.array(read_text(basename + '.rect'))
    start_x, start_y, _, _ = abs_file.source_info.crop_range
    rect[:, 0, 0] += start_x + global_off_x
    rect[:, 0, 1] += start_y + global_off_y

    num_set1.add(abs_file.source_info.frame_range[0])
    num_set2.add(abs_file.source_info.frame_range[1])

    t = Target()
    start_index = abs_file.source_info.frame_range[0] - 1
    # end_index = abs_file.source_info.frame_range[1]

    end_index = start_index+rect.shape[0]

    t.start_index = start_index
    t.end_index = end_index - 1

    t.name = target_name
    try:
        t.rect_poly_points[start_index: end_index, 0] = rect[:, 0]
        t.rect_poly_points[start_index: end_index, 1, 0] = rect[:, 0, 0] + rect[:, 1, 0]
        t.rect_poly_points[start_index: end_index, 1, 1] = rect[:, 0, 1]
        t.rect_poly_points[start_index: end_index, 2] = rect[:, 0] + rect[:, 1]
        t.rect_poly_points[start_index: end_index, 3, 0] = rect[:, 0, 0]
        t.rect_poly_points[start_index: end_index, 3, 1] = rect[:, 0, 1] + rect[:, 1, 1]
        t.class_name = 'vehicle'
        t.state_flags[start_index: end_index] = state[:]
        for i in range(start_index, end_index):
            t.key_frame_flags[i] = [i-1, i+1, 1]
        t.key_frame_flags[end_index-1, 1] = -1
    except Exception as e:
        print(e)
        print(rect.shape)

    t.save_file()

print(num_set1)
print(num_set2)

    # t = Target()



