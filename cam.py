'''
An asynchronous camera capture class
'''

import threading
import argparse
import cv2

#Note to self. We really don't need the argument parsers anymore...
def add_camera_args(parser):
    """Add parser augument for camera options."""
    parser.add_argument('--file', dest='use_file',
                        help='use a video file as input (remember to '
                        'also set --filename)',
                        action='store_true')
    parser.add_argument('--image', dest='use_image',
                        help='use an image file as input (remember to '
                        'also set --filename)',
                        action='store_true')
    parser.add_argument('--filename', dest='filename',
                        help='video file name, e.g. test.mp4',
                        default=None, type=str)
    parser.add_argument('--src', dest='src',
                        help='set source of USB webcam',
                        default=0, type=int)
    parser.add_argument('--width', dest='img_width',
                        help='image width [640]',
                        default=640, type=int)
    parser.add_argument('--height', dest='img_height',
                        help='image height [480]',
                        default=480, type=int)
    return parser

class Camera:
    def __init__(self, args):
        self.id = 0
        self.src = args.src
        try: 
            self.cap = cv2.VideoCapture(self.src)
        except: 
            raise Exception("Failed to bring up device {}".format(self.src))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.img_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.img_height)
        self.grabbed, self.frame = self.cap.read()
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.thread_running = False

        self.width = self.cap.get(3)
        self.height = self.cap.get(4)

    def set(self, var1, var2):
        self.cap.set(var1, var2)

    def start(self):
        if self.thread_running:
            raise Exception('Camera Thread is already running')
        self.thread_running = True
        print("[LOGS] STARTING CAMERA THREAD")
        self.thread = threading.Thread(target=self.grab_img, args=())
        self.thread.start()
        return self

    def grab_img(self):
        while self.thread_running:
            grabbed, frame = self.cap.read()
            with self.read_lock:
                self.grabbed = grabbed
                self.frame = frame

    def read(self):
        with self.read_lock:
            frame = self.frame.copy()
            grabbed = self.grabbed
        return grabbed, frame

    def stop(self):
        self.thread_running = False
        self.thread.join()

    def __exit__(self, exec_type, exc_value, traceback):
        self.cap.release()