import os
import json
import numpy as np
from bases.sv_dataset import DatasetBase
from bases.file_ops import read_text, read_state_file
from bases.abs_file import Abstract
from configs import ABSCREATOR_CONFIG_FILE


"""
.abs
  - source_info
      - video_id
      - seq_id
      - frame_range
      - crop_range
      
  - details
      - init_rect
      - init_poly
      - frame_num
      - class: [car, large vehicle, ship, airplane]
      - level:[
               simple: occ+inv == 0
               normal: occ+inv < 0.3
               hard: occ+inv >= 0.3
              ]
"""


def read_addon_file(json_file):
    with open(json_file) as f:
        d = json.load(f)
    return d['frame_range'], d['area_range'], d['class']


class AbsCreator(DatasetBase):
    HardThreshold: float = 0.3
    AddOnInfo: str = ''

    @classmethod
    def BuildAll(cls):
        for seq_name in cls.D:
            cls._L.info('creating... %s' % seq_name)
            cls.Build(seq_name)

    @classmethod
    def _JudgeLevel(cls, state):
        total = len(state)
        nor = np.sum(state == 0)
        rate = 1 - nor/total
        if rate >= cls.HardThreshold:
            return 'hard'
        elif rate == 0:
            return 'simple'
        else:
            return 'normal'

    @classmethod
    def Build(cls, seq_name):
        data = cls.D[seq_name]
        video_id, seq_id = seq_name.split('.')

        rect = read_text(data['rect'])
        poly = read_text(data['poly'])

        state = read_state_file(data['state'])

        length = len(state)

        abs = Abstract()

        frame_range, crop_range, class_name = read_addon_file(os.path.join(cls.AddOnInfo, video_id, '%s.abs' % seq_id))

        abs.source_info.video_id = video_id
        abs.source_info.seq_id = seq_id
        abs.source_info.frame_range = frame_range
        abs.source_info.crop_range = crop_range
        abs.details.init_rect = rect[0]
        abs.details.init_poly = poly[0]
        abs.details.length = length
        abs.details.class_name = class_name
        abs.details.level = cls._JudgeLevel(state)

        abs.Json = data['abs']

        return abs


AbsCreator.Load(ABSCREATOR_CONFIG_FILE)

if __name__ == '__main__':
    AbsCreator.BuildAll()


