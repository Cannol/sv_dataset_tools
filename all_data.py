import os
import cv2
from bases.targets import Target
from bases.trackers import TrackerRunner
from bases.trackers import TrackingTask, TrackingResult
import time

from configs import VIDEO_IDS_TXT, TRACKER_CONFIG_FILE

if __name__ == '__main__':

    video_ids = {}
    with open(VIDEO_IDS_TXT) as f:
        lines = f.readlines()
    for line in lines:
        a, b = line.strip().split(' ')
        video_ids[a] = b

    path = r'D:\Sanatar\Desktop\标注结果\018_宋纬\targets'
    target_file = '1efcdadbcc471753f5417e84df96b2c2.meta'
    vid = '018'
    vid_from = r'E:\ORSV_coll\total'
    img_path = r'D:\imgs'

    if len(os.listdir(img_path)) == 0:
        seq_id = 1
        cap = cv2.VideoCapture(os.path.join(vid_from, video_ids[vid] + '.avi'))
        while cap.isOpened():
            print(seq_id)
            res, image = cap.read()
            if image is None:
                break
            else:
                cv2.imwrite(os.path.join(img_path, '%06d.tiff' % seq_id), image)
                seq_id += 1
        cap.release()

    img_paths = [os.path.join(img_path, i) for i in os.listdir(img_path) if i.endswith('.tiff')]
    img_paths.sort()
    Target.SetLength(1)

    TrackerRunner.Load(TRACKER_CONFIG_FILE)
    runner = TrackerRunner(img_paths)
    runner.start()
    runner1 = TrackerRunner(img_paths)
    runner1.start()

    target_files = [os.path.join(path, i) for i in os.listdir(path) if i.endswith('.meta')]
    n = 0
    for target_file in target_files[2:3]:
        t = Target.MakeNewFromJsonFile(target_file)

        index = t.start_index

        polys = t.rect_poly_points[index: index+21]

        TrackerRunner.AddTask(target_id=t.name,
                              indexes=list(range(index, index+21)),
                              ref_polys=[polys[0], polys[-1]],
                              enlarge=5,
                              scale=10)
        n += 1

    res = []
    while len(res) < n:
        time.sleep(1)
        r: TrackingResult = TrackerRunner.GetResult()
        if r is not None:
            res.append(r)
            print(r)
    runner.terminate()
    runner1.terminate()
    runner.join()
    runner1.join()








