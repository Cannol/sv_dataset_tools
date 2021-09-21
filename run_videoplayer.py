from tools.video_player import VideoPlayer


def keys():
    import numpy as np
    import cv2

    has_do = [False]

    def _empty(event, x, y, flags, param): pass

    def _mouse_event(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            print('Got Ctrl-Key: %d' % flags)
            has_do[0] = True
            cv2.setMouseCallback('TestKeys', _empty)

    Keys = ['Esc', 'Enter', 'Backspace']

    test = np.zeros((500, 500, 1), 'uint8')
    cv2.imshow('TestKeys', test)
    cv2.setMouseCallback('TestKeys', _mouse_event)
    print('Press Ctrl + Mouse Left Button....', end='')
    while not has_do[0]:
        cv2.waitKey(1000)
    for key in Keys:
        print('Please Press Key [%s] ....' % key, end='')
        x = cv2.waitKey(0)
        print('Got number: %d ' % x)
    print('Test over!')


def run_video(names):
    if isinstance(names, str):
        names = [names]
    VideoPlayer.PlayList(VideoPlayer.MakePlayList(names))


if __name__ == '__main__':
    # keys()
    run_video('*.*')