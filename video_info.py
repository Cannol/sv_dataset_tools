import os
import cv2


video = '/data1/ORSV/part0/20170424-侧摆角（17.0168）-美国-旧金山.mp4'

cap = cv2.VideoCapture(video)

# Check if camera opened successfully
if (cap.isOpened() == False):
    print("Error opening video file")

num = 0
w = 0
# Read until video is completed
while (cap.isOpened()):
    # Capture frame-by-frame
    ret, frame = cap.read()
    if ret == True:
        if num == 0:
            w = frame.shape
        num += 1
    else:
        break
print(num)
print(w)
        # # Display the resulting frame
        # cv2.imshow('Frame', frame)
        #
        # # Press Q on keyboard to  exit
        # if cv2.waitKey(25) & 0xFF == ord('q'):
        #     break