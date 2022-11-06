import cv2
import os

source_videos_dir = r'E:\ORSV_coll\total'
out_path = r'E:\ORSV_coll\pics'
os.makedirs(out_path, exist_ok=True)

video_files = [os.path.join(source_videos_dir, i) for i in os.listdir(source_videos_dir) if i.endswith('.avi')]
last_image = None
for video_file in video_files:
    cap = cv2.VideoCapture(video_file)
    while True:
        res, image = cap.read()

        if image is None:
            break
        last_image = image
        break
    cv2.imwrite(os.path.join(out_path, '%s.tiff' % os.path.basename(video_file)[:-4]), last_image)
    cap.release()
