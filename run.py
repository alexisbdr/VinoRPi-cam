#!/usr/bin/env python3

from argparse import ArgumentParser
from copy import deepcopy
from datetime import datetime, timezone
import os
import time

import cv2
import numpy as np

from boto import upload_frame
from cam import add_camera_args, Camera
from config import Config
from detect import OpenVinoDetectorAsync, OpenVinoClassifierAsync
from write import WriteQueue


#Note to self. We really don't need the argument parsers anymore...
def parse_args():
    """Parse input arguments."""
    desc = ('The Everguard pre-inference server')
    parser = ArgumentParser(description=desc)
    parser = add_camera_args(parser)
    #parser = add_build_args(parser)
    parser.add_argument('--detect', dest='detect',
                        help='option to visualize inference output',
                        action='store_true')
    parser.add_argument('--s3', dest='upload',
                        help='upload to s3, specify [bucket] and [dest]',
                        action='store_true')
    args = parser.parse_args()
    return args

def main(): 
    '''
    Main loop that initializes camera and other 
    '''
    
    args = parse_args()

    config = Config()

    #Start Camera async class    
    cam = Camera(args)
    cam.start()

    #Start io writing queue
    write_queue = WriteQueue()
    write_queue.start()
    if config.Inference.mode == 'detect':
        print('Running detection')
        detector = OpenVinoDetectorAsync(config.Inference)
    else:
        detector = OpenVinoClassifierAsync(config.Inference)

    while True: 
        _,frame = cam.read()
        start_time = time.time()
        infer_frame = deepcopy(frame)
        detections = detector.run(infer_frame)
        timestamp = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d-%H-%M-%S-%f')
        path = 'tmp/' + timestamp + '.jpg'
        if detections:
            '''
            Need to fix the bounding box locations
            for detection in detections:
                xmin = detection.position.xmin
                ymin = detection.position.ymin  
                xmax = detection.position.xmax 
                ymax = detection.position.ymax 
                cv2.rectangle(frame, (int(xmin), int(ymin)), (int(xmax), int(ymax)), detection.color, 2)
            '''
            cv2.putText(frame,'HUMAN',(10,400), cv2.FONT_HERSHEY_SIMPLEX, 4,(25,25,255),2,cv2.LINE_AA)
            cv2.imshow('frame', frame)
            cv2.imwrite(path, frame)
            #This has to RTT 
            upload_frame(path, config)
        else: 
            #add to upload queue
            write_queue.enqueue(path, frame)
        end_time = time.time()
        print("[LOGS] ---PIPELINE TIME--- **{}**".format(end_time-start_time))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break 
    cam.stop()
    write_queue.stop()
    cv2.destroyAllWindows() 
    

if __name__ == "__main__":
    main()

