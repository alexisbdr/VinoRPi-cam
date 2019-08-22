from dataclasses import dataclass, field
import configparser
import os


######### DOWNLOAD FROM S3 ALL CONFIG FILES
##### IMPORTANT UTILITY FUNCTION
"""
Main config class for device
"""
@dataclass 
class DeviceConfig:
    name: str = field(init=False)
    location: str = field(init=False)

    BASEPATH: str = "~"
    WORK_FOLDER: str = "blackops"
    CONFIG_FOLDER: str = "config"
    CONFIG_FILE: str = "device_config.txt"

    def __post_init__(self):
        basepath = os.path.expanduser(self.BASEPATH)
        filepath = os.path.join(self.WORK_FOLDER, self.CONFIG_FOLDER, self.CONFIG_FILE)
        path = os.path.join(basepath, filepath)

        try:
            with open(path) as f: 
                device_info_list = f.read().split('\n') 
        except IOError: 
            raise Exception("{} file is missing".format(self.CONFIG_FILE))
        
        self.name = device_info_list[0]
        self.location = device_info_list[1]
        self.region = device_info_list[2]

@dataclass
class AWSConfig: 
    key_id: str = field(init=False)
    access_key: str = field(init=False)

    BASEPATH: str = "~"
    WORK_FOLDER: str = "blackops"
    CONFIG_FOLDER: str = "config"
    AWS_KEY_PATH: str = "aws_key.csv"

    #This stuff should be loaded from file - no?
    BUCKET_NAME: str = "edge-cam"
    DATA_FOLDER: str = "data"
    LOG_FOLDER: str = "logs"

    C_TIME: int = 3 #Connetion timeout
    R_TIME: int = 5 #Response timeout
    MAX_RETRIES: int = 0 #Why have this as a param if multi retry fails?

    def __post_init__(self):
        basepath = os.path.expanduser(self.BASEPATH)
        filepath = os.path.join(self.WORK_FOLDER, self.CONFIG_FOLDER, self.AWS_KEY_PATH)
        path = os.path.join(basepath, filepath)

        try: 
            with open(path) as f: 
                aws_key_pem = f.read().split('\n')[1].split(',')
        except IOError: 
            raise Exception("{} file is missing".format(self.AWS_KEY_PATH))

        self.key_id = aws_key_pem[0]
        self.access_key = aws_key_pem[1]

@dataclass
class InferenceConfig: 
    model_name: str = field(init=False)
    frame_width: int = field(init=False)
    frame_height: int = field(init=False)

    BASEPATH: str = "~"
    WORK_FOLDER: str = "blackops"
    CONFIG_FOLDER: str = "config" 
    CONFIG_FILE: str = "inference_config.txt"
    MODEL_CONFIG_FILE: str = "config.ini"

    def __post_init__(self):
        basepath = os.path.expanduser(self.BASEPATH)
        workpath = os.path.join(self.WORK_FOLDER, self.CONFIG_FOLDER)
        filepath = os.path.join(workpath, self.CONFIG_FILE)
        path = os.path.join(basepath, filepath)

        """
        try: 
            with open(path) as f: 
                inference_info_list = f.read().split('\n')
        except IOError: 
           raise Exception("{} file is missing".format(self.CONFIG_FILE))

       
        #frame_dimensions = inference_info_list[1].split(',')
        #self.frame_width = frame_dimensions[0]
        #self.frame_height = frame_dimensions[1]
        """
        config = configparser.ConfigParser()
        filepath = os.path.join(workpath, self.MODEL_CONFIG_FILE)
        path = os.path.join(basepath, filepath)
        
        try:
            with open(path, 'r') as f: 
                config.read_file(f)
        except IOError: 
            raise Exception("{} file is missing".format(self.MODEL_CONFIG_FILE))
        
        self.model_name = config['settings']['model_name']
        if 'DETECTION' in self.model_name: 
            self.mode = 'detect'
        else: 
            self.mode = 'classify'

        self.default_device = config['settings']['default_device']
        self.fallback_device = config['settings']['fallback_device']

        self.frame_width = config['settings']['width']
        self.frame_height = config['settings']['height']

        if self.model_name not in config:
            raise Exception("{} configuration is missing".format(self.model_name))

        model_config = config[self.model_name]
        self.network_file = model_config['path_xml']
        self.weights_file = model_config['path_bin']

        self.threshold = float(model_config['human_threshold'])
        if 'non_human_threshold' in model_config: 
            self.non_threshold = float(model_config['non_human_threshold'])
        self.normalize = bool(model_config['normalize'])
        if 'width' in model_config and 'height' in model_config: 
            self.frame_width = model_config['width']
            self.frame_height = model_config['height']

@dataclass
class Config:
    print("[LOGS] ---LOADING CONFIGURATION FILES---")
    Device: DeviceConfig = field(default_factory=DeviceConfig)
    AWS: AWSConfig = field(default_factory=AWSConfig)
    Inference: InferenceConfig = field(default_factory=InferenceConfig)



