import os
import cv2
import numpy as np
from bases.targets import Target
from bases.file_ops import read_state_file
from bases.file_ops import read_text
from bases.abs_file import Abstract

# Target.SetLength(327)
# Target.SetGlobalOffsize(0, 0, 12000, 5000)

Target.SetGlobalOffsize(0, 0, 12000, 5000)


def transfer_files(target_name, basename, global_off_x, global_off_y, out_base_dir, length):
    abs_file = Abstract.MakeNewFromJsonFile(basename + '.abs')
    state = read_state_file(basename + '.state')
    rect = np.array(read_text(basename + '.rect'))
    start_x, start_y, _, _ = abs_file.source_info.crop_range
    rect[:, 0, 0] += start_x + global_off_x
    rect[:, 0, 1] += start_y + global_off_y

    # num_set1.add(abs_file.source_info.frame_range[0])
    # num_set2.add(abs_file.source_info.frame_range[1])

    Target.SetLength(length)

    t = Target()
    start_index = abs_file.source_info.frame_range[0] - 1
    # end_index = abs_file.source_info.frame_range[1]

    end_index = start_index + rect.shape[0]

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
            t.key_frame_flags[i] = [i - 1, i + 1, 1]
        t.key_frame_flags[end_index - 1, 1] = -1
    except Exception as e:
        print(e)
        print(rect.shape)

    t.save_file(out_base_dir, base_path=True)


path = r'F:\dataset\refix_label01\refix_label01'
out_base = r'F:\dataset\output_all'
vid_dict = {
    '001': ('005', 0, 0),
    '002': ('005', 4549, 1942),
    '003': ('006', 3915, 1715),
    '004': ('007', 4471, 144),
    '005': ('008', 833, 2768),
    '006': ('008', 3026, 2124),
    '007': ('008', 5564, 1216),
    '008': ('010', 874, 53),
    '009': ('011', 1996, 1736),
    '010': ('011', 4020, 994),
    '011': ('011', 6392, 2303),
    '012': ('012', 8212, 924),
    '013': ('012', 9120, 2484)
}
vid_length = {
    '005': 327,
    '006': 327,
    '007': 326,
    '008': 326,
    '010': 326,
    '011': 326,
    '012': 326
}

file_list = []
for root, dirs, files in os.walk(path):
    target_names_set = set()
    for file in files:
        filename = file.split('.')[0]
        target_names_set.add(filename)
    target_names = list(target_names_set)
    target_names.sort()

    for name in target_names:
        vid = name.split('_')[0]
        file_list.append((name, os.path.join(root, name), vid))

for name, file_path, vid in file_list:
    vid_real, off_x, off_y = vid_dict[vid]
    out_dir = os.path.join(out_base, vid_real)
    os.makedirs(out_dir, exist_ok=True)
    transfer_files(target_name=name,
                   basename=file_path,
                   global_off_x=off_x,
                   global_off_y=off_y,
                   out_base_dir=out_dir,
                   length=vid_length[vid_real])







