import os

'''
此脚本用来将原有OTB数据集的格式转换为通用格式
 - 将图片序列存放在sequences文件夹中
 - 将所有的标签（gt_rect, gt_poly, attr, state_flags）存放在annotations中
'''

root = '/data1/data_here'
video_list = ['01', '02', '03', '04', '05', '06']

annos_dirname = 'annotations'
attr_postfix = '.attr'
state_postfix = '.state'
rect_postfix = '.rect'
poly_postfix = '.poly'

attr_dirname = 'attribute'
seq_dirname = 'sequences'
state_filename = 'frame_flags.txt'
gt_rect_filename = 'groundtruth_rect.txt'
gt_poly_filename = 'groundtruth.txt'
img_dirname = 'img'


def _remove_file(file_name):
    os.system('rm %s' % file_name)


def _remove_dir(dir_name):
    os.system('rm -r %s' % dir_name)


def _move_files_to_dir(file_list, dir_name):
    files = ' '.join(file_list)
    os.system('mv %s %s' % (files, dir_name))


def _move(file, new):
    os.system('mv %s %s' % (file, new))


def _cp(file, new):
    os.system('cp %s %s' % (file, new))


for video in video_list:
    v_dir = os.path.join(root, video)
    all_seq_dir = os.path.join(v_dir, seq_dirname)
    all_seqs = os.listdir(all_seq_dir)
    attrs_dir = os.path.join(v_dir, attr_dirname)

    annos_dir = os.path.join(v_dir, annos_dirname)

    if not os.path.exists(annos_dir):
        os.mkdir(annos_dir)

    for seq_name in all_seqs:
        seq_dir = os.path.join(all_seq_dir, seq_name)
        print('Processing... %s' % seq_dir)

        gt_rect_file_ori = os.path.join(seq_dir, gt_rect_filename)
        gt_rect_file_new = os.path.join(annos_dir, '%s%s' % (seq_name, rect_postfix))

        gt_poly_file_ori = os.path.join(seq_dir, gt_poly_filename)
        gt_poly_file_new = os.path.join(annos_dir, '%s%s' % (seq_name, poly_postfix))

        state_file_ori = os.path.join(seq_dir, state_filename)
        state_file_new = os.path.join(annos_dir, '%s%s' % (seq_name, state_postfix))

        _move(gt_rect_file_ori, gt_rect_file_new)
        _move(gt_poly_file_ori, gt_poly_file_new)
        _move(state_file_ori, state_file_new)

        tmp_dir = os.path.join(all_seq_dir, 'tmp')
        img_dir = os.path.join(seq_dir, img_dirname)
        _move(img_dir, tmp_dir)
        _remove_dir(seq_dir)
        _move(tmp_dir, seq_dir)

        attr_file_ori = os.path.join(attrs_dir, '%s.txt' % seq_name)
        attr_file_new = os.path.join(annos_dir, '%s%s' % (seq_name, attr_postfix))
        _move(attr_file_ori, attr_file_new)


