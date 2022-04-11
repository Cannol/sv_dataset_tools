import cv2

video = cv2.VideoCapture('/data1/ORSV/part3/火箭原始视频/JL103B_MSS_20180907120918_200004770_101_001_L1B_MSS.avi')

win_name = 'show'
cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(win_name, 1600, 1200)

writer = cv2.VideoWriter()

n = 0
while True:
    ret, frame = video.read()
    if frame is None:
        break
    # print(frame.shape)
    n += 1
    print(n)

    if n > 420 and n < 730:
        img = frame[400:2500, :6000,:]
        cv2.setWindowTitle(win_name, 'frame: %d' % n)
        cv2.imshow(win_name, img)
        cv2.waitKey(30)
    elif n >= 730:
        break