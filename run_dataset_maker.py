import os

from tools.video_target_selector import TargetSelector
from configs import CONFIGS_DIR


if __name__ == '__main__':

    exec_func_name = '_create_coco_dataset'
    save_root_dir = '/data1/IPIUSVX-Det-v1-COCO'

    os.makedirs(save_root_dir, exist_ok=True)

    all_dataset_configs = os.path.join(CONFIGS_DIR, 'dataset_for_each')
    yaml_files = [os.path.join(all_dataset_configs, i) for i in os.listdir(all_dataset_configs) if i.endswith('.yaml')]
    yaml_files.sort()

    for yaml_file in yaml_files:
        print('=====> Processing: %s' % yaml_file)
        TargetSelector.StartVideo(opt_config_file=yaml_file, exec_func_name=exec_func_name, root_dir=save_root_dir)
