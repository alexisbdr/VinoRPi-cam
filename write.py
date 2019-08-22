#!/usr/bin/env python3

import cv2
import os
import pickle
import redis
import time
import threading
import uuid


class WriteTask(object):
    def __init__(self, image_path, frame):
        self.id = str(uuid.uuid4())
        self.image_path = image_path
        self.frame_data = frame 
    
    def write(self):
        '''
        Task function for the multiprocessing queue
        '''
        #Path to save directory (this will be the same for all)
        #basepath = os.path.join(os.path.expanduser('~'), 'tmp')
        #imagepath = self.image_path.split('/')[-1]
        #writepath = os.path.join(basepath, imagepath)
        #JPEG Image compression flags
        jpeg_quality = [cv2.IMWRITE_JPEG_QUALITY, 100]
        cv2.imwrite(self.image_path, self.frame_data, jpeg_quality)
        #print("[LOGS] {} image saved".format(self.image_path))

class WriteQueue(object): 
    def __init__(self):
        self.redis_conn = redis.Redis()
        self.name = 'io'
        self.thread_running = False
        self.queue_lock = threading.Lock()
        self.write_lock = threading.Lock()

    def start(self):
        if self.thread_running: 
            raise Exception('IO thread is running')
        self.thread_running = True
        print("[LOGS] STARTING WRITE QUEUE")
        self.thread = threading.Thread(target=self.dequeue, args=())
        self.thread.start()
        return self

    def enqueue(self, image_path, frame):
        with self.write_lock:
            task = WriteTask(image_path, frame)
        #print("[LOGS] Received Task {}".format(task.id))
        serialized_task = pickle.dumps(task, protocol=pickle.HIGHEST_PROTOCOL)
        self.redis_conn.lpush(self.name, serialized_task)
        return task.id

    def dequeue(self):
        while self.thread_running:
            #print("[LOGS] Dequeuing Task ")
            #if self.get_length != 0:
            _, serialized_task = self.redis_conn.brpop(self.name)
            task = pickle.loads(serialized_task)
            threading.Thread(task.write(), args=()).start()

    def get_length(self):
        return self.redis_conn.llen(self.name)
    
    def stop(self):
        self.thread_running = False
        self.thread.join()
    
    def __exit__(self):
        #Close redis connection
        del redis_conn