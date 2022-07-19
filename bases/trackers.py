import threading
from typing import List
import multiprocessing
import queue

import cv2
from collections import namedtuple
from multiprocessing import Process

from common.yaml_helper import YamlConfigClassBase
from bases.images_reader import ImageSeqReader
from common.graphic_helper import get_outside_rect, get_image_patch_from_center_range, get_bbox_iou_xywh, merge2routes
from third_part.KCFpy.kcftracker import KCFTracker

minor_ver = cv2.__version__.split('.')[0]


TrackingTask = namedtuple('TrackingTask', ['target_id', 'indexes', 'ref_polys', 'scale', 'enlarge'])
TrackingResult = namedtuple('TrackingResult', ['target_id', 'indexes', 'result_polys'])


class TrackerRunner(YamlConfigClassBase, Process):

    MaxQueue: int = 100
    CacheSize: int = 1000
    NumTrackers: int = 10
    ShowTrackingSteps: bool = False
    ShowWaitTime: int = 1000

    _task_queue: multiprocessing.Queue = None
    _finished_queue: multiprocessing.Queue = None
    _runners: List[Process] = []
    _recv_thread = None

    def __init__(self, image_lst_files, cache_size=None):
        Process.__init__(self, daemon=True)
        self.image_lst_files = image_lst_files
        self.length = len(self.image_lst_files)
        self._cache_size = self.CacheSize if cache_size is None else cache_size # MB
        assert self.length > 0
        self._task_queue_local = self._task_queue
        self._finished_queue_local = self._finished_queue
        self._tracker = None
        self._reader = None
        self._runners.append(self)
        self._show_tracking_steps = self.ShowTrackingSteps
        self._show_wait_time = self.ShowWaitTime

    @classmethod
    def StopAllRunners(cls):
        for i in range(len(cls._runners)):
            cls._task_queue.put(None)
        for _r in cls._runners:
            # _r.terminate()
            if _r.is_alive():
                _r.join()
        cls._runners.clear()

    @classmethod
    def StartRunners(cls, image_list):
        # number = min(max(0, number), cls.MaxTrackers)
        # if len(cls._runners) == number:
        #     return
        # if len(cls._runners) > number:
        #     de = len(cls._runners) - number
        #     for i in range(de):
        #         cls._task_queue.put(None)

        # for i in range(number):
        #     t = cls(image_list)
        #     t.start()
        if len(cls._runners) == 0:
            for i in range(cls.NumTrackers):
                t = cls(image_list)
                t.start()

    @classmethod
    def ExistAliveRunners(cls):
        for _r in cls._runners:
            if _r.is_alive():
                return True
        return False

    @classmethod
    def _receive_loop(cls, func):
        print('[Tracking Thread] Start receive results.')
        while True:
            tracking_result = cls._finished_queue.get(block=True)
            if tracking_result is None:
                break
            try:
                func(tracking_result)
            except Exception as e:
                print(e)
                print(e.__traceback__)
        print('[Tracking Thread] Stopped receive results. Bye bye ^.^')

    @classmethod
    def BandReceiveHookAndStartThread(cls, hook_func):
        """
        This thread must run in the parent process of all TrackerRunner processes.
        """
        import threading
        import time

        if hook_func is None:
            if cls._recv_thread is not None:
                cls._finished_queue.put(None)
                cls._recv_thread.join()
                cls._recv_thread = None
            return

        if cls._recv_thread is not None:
            cls._finished_queue.put(None)
            cls._recv_thread.join()

        cls._recv_thread = threading.Thread(target=cls._receive_loop,
                                            args=(hook_func, ),
                                            daemon=True)
        cls._recv_thread.start()
        while not cls._recv_thread.is_alive():
            print('Waiting for receive thread start...')
            time.sleep(1)

    def one_way_detect(self, indexes, polys, enlarge, scale):
        bbox = get_outside_rect(polys[0], True)
        frame_init = self._reader[indexes[0]]
        frame_init, bbox_init, _ = get_image_patch_from_center_range(frame_init, bbox, enlarge, scale)
        self._tracker.init(bbox_init, frame_init)

        # cv2.imshow('tracker_detect', frame_init)
        # cv2.waitKey(1)

        result_polys = [bbox]
        for i, bbox_ in zip(indexes[1:], polys[1:]):
            frame, _, off_xy = get_image_patch_from_center_range(self._reader[i],
                                                                 get_outside_rect(bbox_, True), enlarge, scale)
            bbox = self._tracker.update(frame)

            # p1 = (int(bbox[0]), int(bbox[1]))
            # p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            # cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
            # cv2.imshow('tracker_detect', frame)
            # cv2.waitKey(1)

            bbox = [bbox[0] / scale + off_xy[0], bbox[1] / scale + off_xy[1], bbox[2] / scale, bbox[3] / scale]
            result_polys.append(bbox.copy())
        return result_polys

    def one_way_track(self, indexes, start_poly, enlarge, scale):
        bbox = get_outside_rect(start_poly, True)

        frame_init = self._reader[indexes[0]]

        frame_init, bbox_init, _ = get_image_patch_from_center_range(frame_init, bbox, enlarge, scale)
        self._tracker.init(bbox_init, frame_init)

        # cv2.imshow('tracker', frame_init)
        # cv2.waitKey(1)

        result_polys = [bbox]
        for i in indexes[1:]:
            frame, _, off_xy = get_image_patch_from_center_range(self._reader[i], bbox, enlarge, scale)
            bbox = self._tracker.update(frame)

            # p1 = (int(bbox[0]), int(bbox[1]))
            # p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            # cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
            # cv2.imshow('tracker', frame)
            # cv2.waitKey(500)

            bbox = [bbox[0] / scale + off_xy[0], bbox[1] / scale + off_xy[1], bbox[2] / scale, bbox[3] / scale]
            result_polys.append(bbox.copy())
        # cv2.destroyWindow('tracker')
        return result_polys

    def _show_result(self, target_name, indexes, bboxes, enlarge, scale):
        cv2.namedWindow('result_show')
        cv2.setWindowTitle('result_show', target_name)
        if len(target_name) > 10:
            target_name = '%s...%s' % (target_name[:5], target_name[-3:])
        # print(bboxes)
        for index, bbox in zip(indexes, bboxes):
            frame, rect, _ = get_image_patch_from_center_range(self._reader[index], bbox, enlarge, scale)
            p1 = (int(rect[0]), int(rect[1]))
            p2 = (int(rect[0] + rect[2]), int(rect[1] + rect[3]))
            cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
            cv2.setWindowTitle('result_show', '%s frame: %d (%d -> %d)' % (target_name, index, indexes[0], indexes[-1]))
            cv2.imshow('result_show', frame)
            cv2.waitKey(self._show_wait_time)
        cv2.destroyWindow('result_show')

    def run(self, *args) -> None:
        self._tracker = KCFTracker(True, True, True)
        self._reader = ImageSeqReader(self.image_lst_files, self._cache_size)
        while True:
            task: TrackingTask = self._task_queue_local.get(block=True)
            if task is None:
                print('[Tracking Process] Early stopped!')
                break

            scale = task.scale
            enlarge = task.enlarge
            indexes = task.indexes

            if len(task.ref_polys) == 1:
                result_polys = self.one_way_track(indexes, task.ref_polys[0], enlarge, scale)
            elif len(task.ref_polys) == 2:
                result_polys = self.one_way_track(indexes, task.ref_polys[0], enlarge, scale)
                end_bbox = get_outside_rect(task.ref_polys[-1], True)
                iou = get_bbox_iou_xywh(end_bbox, result_polys[-1])
                result_polys_inverse = self.one_way_track(indexes[::-1], task.ref_polys[-1], enlarge, scale)
                start_bbox = get_outside_rect(task.ref_polys[0], True)
                iou_inverse = get_bbox_iou_xywh(start_bbox, result_polys_inverse[-1])
                # print('iou+', iou)
                # print('iou-', iou_inverse)
                if iou + iou_inverse == 0:
                    result_polys = None
                else:
                    result_polys = merge2routes(result_polys, result_polys_inverse[::-1], iou, iou_inverse)
            elif len(task.ref_polys) == len(indexes):
                result_polys = self.one_way_detect(indexes, task.ref_polys, enlarge, scale)
            else:
                result_polys = None

            if result_polys is not None and self._show_tracking_steps:
                self._show_result(task.target_id, indexes, result_polys, enlarge, scale)

            res = TrackingResult(target_id=task.target_id,
                                 indexes=indexes,
                                 result_polys=result_polys)
            self._finished_queue_local.put(res)

    @classmethod
    def AddTask(cls, **kwargs):
        """
        return: True -- Add new task successfully
                False -- The task queue is full
        """
        if cls._task_queue.full():
            return False
        else:
            tt = TrackingTask(**kwargs)
            try:
                cls._task_queue.put_nowait(tt)
            except queue.Full:
                return False
            return True

    @classmethod
    def GetResult(cls) -> TrackingResult:
        if cls._finished_queue.empty():
            return None
        else:
            return cls._finished_queue.get_nowait()

    @classmethod
    def Load(cls, file=None):
        super().Load(file)
        cls._task_queue = multiprocessing.Queue(cls.MaxQueue)
        cls._finished_queue = multiprocessing.Queue(cls.MaxQueue)

