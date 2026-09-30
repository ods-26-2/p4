import json
import numpy as np
import cv2

class RealtimeUndistorter:
    def __init__(self, json_path: str):
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        self.width = data["image_width"]
        self.height = data["image_height"]
        
        self.K = np.array(data["camera_matrix"], dtype=np.float32)
        self.D = np.array(data["distortion_coefficients"], dtype=np.float32)
        
        self.new_K, self.roi = cv2.getOptimalNewCameraMatrix(
            self.K, self.D, (self.width, self.height), alpha=0
        )
        
        self.map_x, self.map_y = cv2.initUndistortRectifyMap(
            self.K, self.D, None, self.new_K, (self.width, self.height), cv2.CV_32FC1
        )

    def process(self, frame: np.ndarray) -> np.ndarray:
        return cv2.remap(
            frame, 
            self.map_x, 
            self.map_y, 
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT
        )