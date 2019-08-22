#!/usr/bin/env python3

from datetime import datetime, timezone
from enum import Enum
import json
from queue import Queue
import os
from threading import Thread

"""
Boto s3 libraries for session creation
"""
import botocore.session
from botocore.config import Config
import boto3
from botocore.exceptions import ClientError
import subprocess

"""
Request Library for session creation
"""
import requests
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter
from requests import Session, exceptions

'''
Ping to check for internet connection
'''
def isConnected():
    p = subprocess.Popen(['ping', '8.8.8.8', '-n', '-c', '1', '-W', '1'])
    p.wait()
    return not (p.poll())

def sendReq(url: str, data: json, timeout: int):
    '''
    Utility function for dealing with requests
    '''
    if isConnected():
        try:
            s = Session()
            s.mount('https://', HTTPAdapter(max_retries=Retry(total=0)))
            r = s.post(url, json=data, timeout=timeout)
            return r
        except:
            print('[ALERT] POST request failed')
            pass
    
    return None

"""
Boto S3 instance - manages data and utility functions
"""
class AWSSessionUpload(Thread):

    def __init__(self, file_path, config):
        Thread.__init__(self)
        self.file_path = file_path
        self.config = config.AWS
        self.device = config.Device

    def run(self):
        session_config = Config(
            connect_timeout= self.config.C_TIME, 
            read_timeout= self.config.R_TIME, 
            retries={'max_attempts':self.config.MAX_RETRIES} #We're gonna declare 0 attempts for now
            )
        session = boto3.session.Session()
        #boto3.set_stream_logger('')
        self.s3 = session.resource('s3', 
            aws_access_key_id = self.config.key_id,
            aws_secret_access_key = self.config.access_key,
            region_name = self.device.region,
            config=session_config
            )
    
        #if isConnected():
        try:
            device_folder = self.device.location + '-' + self.device.name
            file_timestamp = self.file_path.split('/')[-1]
            key = os.path.join(device_folder, self.config.DATA_FOLDER, file_timestamp)
            self.s3.Bucket(self.config.BUCKET_NAME).upload_file(self.file_path, key)
            #print("[LOGS] Uploaded image {0} to {1}".format(self.file_path, key))
            return 200 
    
        except ClientError as e:
            print('[ALERT] Boto upload FAILED: ',e)
            return 400
    
def upload_frame(frame_file: str, Config):
    return AWSSessionUpload(frame_file, Config).start()

'''
Function for going down presigned url path

def preSignedURL(fileLocation, c_time:int=3, r_time:int=5):
    global s3

    if isUp():
        try: 
'''            