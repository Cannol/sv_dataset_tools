import os

DATA_ROOT = '/data2/CROP_TRACKING_DATASETS'
DES_FILE = 'notice'
with open(os.path.join(DATA_ROOT, DES_FILE)) as f:
    lines = f.readlines()

SUB_VIDEOS = [[line[3:].strip(), os.path.join(DATA_ROOT, line[:2].strip())] for line in lines]
