import cv2
import numpy as np


class TargetSelectWindow:
    def __init__(self, win_width, win_height ):
        self.font = None
        self.frame = None
        self.index = -1
        self.width = 300
        self.height = 300

    def set_font(self, font):
        self.font = font

    def to_frame(self, frame_index):
        self.index = frame_index
        if self.index < 0:
            self.frame = np.zeros((self.height, self.width, 3), 'uint8')

        self.frame = cv2.imread(self.image_list[self.index])
        self.refresh()

    def refresh(self):
        pass

