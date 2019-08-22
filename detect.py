#!/usr/bin/env python3

from argparse import ArgumentParser
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random
import os
import sys
import time
from threading import Thread
from typing import Dict, List

import cv2 
import numpy as np

DLDT = False
try: 
    from armv7l.openvino.inference_engine import IEPlugin, IENetwork
    print('success')
except ImportError: 
    try: 
        from openvino.inference_engine import IEPlugin, IENetwork
    except ImportError: 
        from cv2 import dnn
        DLDT = True

def softmax(vector: list):
    '''
    Compute softmax value for each normalized value in array
    '''
    return np.exp(vector) / np.sum(np.exp(vector), axis=0)

@dataclass(frozen=True)
class Box: 
    xmin: int
    ymin: int
    xmax: int
    ymax: int

@dataclass
class Detection: 
    position: Box
    class_id: int 
    label: str
    time: float
    color: field(init=False)

    def __post_init__(self):
        self.color = (min(self.class_id * 5, 255), min(self.class_id * 12, 255), min(self.class_id * 7, 255))

@dataclass 
class Classification: 
    human: float
    no_human: float
    class_label: str

class OpenVino:

    def __init__(self, config):

        #Numbers to keep track of process ID
        self.curr = 0
        self.next = 1
        self.width, self.height = config.frame_width, config.frame_height
        
        try:
            self.plugin = IEPlugin(device=config.default_device)
            self.net = IENetwork(model=config.network_file, weights=config.weights_file)
        
        except RuntimeError:
            print("We're probably dealing with a mac here, do some cpu target stuff")
            self.plugin = IEPlugin(device=config.fallback_device)
            self.net = IENetwork(model=config.network_file, weights=config.weights_file)
            supported_layers = self.plugin.get_supported_layers(self.net)
            not_supported_layers = [l for l in self.net.layers.keys() if l not in supported_layers]
            
            if len(not_supported_layers) != 0:
                raise Exception("Some layers in the mdoel are not supported by the CPU - figure this out")
    
        #Get sizes for image pre-processing
        self.input_blob = next(iter(self.net.inputs))
        self.output_blob = next(iter(self.net.outputs))
        self.n, self.c, self.h, self.w = self.net.inputs[self.input_blob].shape
        self.threshold = config.threshold
        if config.mode == 'classify':
            self.threshold = [config.threshold, config.non_threshold]
        self.normalize = config.normalize

        self.exec_net = self.plugin.load(network=self.net)
        #Do we need this? 
        del self.net
        

class OpenVinoClassifierAsync(OpenVino):
    
    def __init__(self, InferenceConfig):
        super().__init__(InferenceConfig)
    
    def run(self, frame)->bool:
        start = time.time()
        #Image resizing - need to normalize the frame
        frame = cv2.resize(frame, (self.w, self.h))
        frame = frame.transpose((2,0,1))
        frame = frame.reshape((self.n, self.c, self.h, self.w))
        if self.normalize: 
            frame = frame.astype(np.uint8)/255.
        #Start request 
        self.exec_net.requests[self.curr].async_infer(inputs={self.input_blob: frame})
        if self.exec_net.requests[self.curr].wait(-1) == 0: 
            classification_time = time.time() - start
            predictions = Classification(
                        self.exec_net.requests[self.curr].outputs[self.output_blob][0][0], 
                        self.exec_net.requests[self.curr].outputs[self.output_blob][0][1],
                        'human')
            #print(classification_time)
            if predictions.human > self.threshold[0] and \
                predictions.no_human < self.threshold[1]: 
                return True

            
    
class OpenVinoDetectorAsync(OpenVino): 

    def __init__(self, InferenceConfig): 
        OpenVino.__init__(self, InferenceConfig)

    def run(self, frame) -> List[Detection]:
        start = time.time() 
        #Image resizing
        frame = cv2.resize(frame, (self.w, self.h))
        frame = frame.transpose((2,0,1))
        frame = frame.reshape((self.n, self.c, self.h, self.w))
        self.exec_net.requests[self.curr].async_infer(inputs={self.input_blob: frame})
        #detections = self.exec_net.infer(inputs={self.input_blob: frame})
        confirmed_detections = []
        if self.exec_net.requests[self.curr].wait(-1) == 0: 
            detection_time = time.time() - start
            #Get results and look at probability
            detections = self.exec_net.requests[self.curr].outputs[self.output_blob]
            for detection in detections[0][0]:
                if detection[2] > self.threshold: 
                    box_posn = Box(
                        detection[3] * self.width, 
                        detection[4] * self.height, 
                        detection[5] * self.width, 
                        detection[6] * self.height
                    )
                    id = random.randint(1,40)
                    confirmed_detection = Detection(box_posn, id, 'human', detection_time, None)
                    confirmed_detections.append(confirmed_detection)
        #self.curr, self.next  = self.next, self.curr
        return confirmed_detections

