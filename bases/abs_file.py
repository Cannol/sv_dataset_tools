from common.json_helper import JsonTransBase


class Details(JsonTransBase):
    def __init__(self):
        self.init_rect = []
        self.init_poly = []
        self.length = 0
        self.class_name = ''
        self.level = ''    # simple, normal, hard


class SourceInfo(JsonTransBase):
    def __init__(self):
        self.video_id = ''
        self.seq_id = ''
        self.frame_range = []
        self.crop_range = []


class Abstract(JsonTransBase):
    def __init__(self):
        self.source_info = SourceInfo()
        self.details = Details()
