import os
from bases.sv_dataset import DatasetBase
from bases.abs_file import Abstract

for seq_name in DatasetBase.D:
    seq = DatasetBase.D[seq_name]
    abs_file = seq['abs']
    img_path = seq['img_dir']
    abs_obj = Abstract.MakeNewFromJsonFile(abs_file)
    start, end = abs_obj.source_info.frame_range
    images = os.listdir(img_path)
    images.sort()
    start_file = images[0][:6]
    end_file = images[-1][:6]
    if start_file != '000001':
        print(seq_name)
        for i, image in enumerate(images):
            src = os.path.join(img_path, image)
            des = os.path.join(img_path, '%06d.tiff' % (i+1))
            cmd = 'mv %s %s' % (src, des)
            # print(cmd)
            os.system(cmd)


