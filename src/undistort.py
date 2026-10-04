import json
import cv2
import numpy as np


class Undistorter:
    def __init__(self, config_path="config/camera_calibration.json"):
        with open(config_path, "r") as file:
            config = json.load(file)

        self.camera_matrix = np.array(
            config["camera_matrix"],
            dtype=np.float64
        )

        self.distortion_coefficients = np.array(
            config["distortion_coefficients"],
            dtype=np.float64
        )

    def process(self, frame):
        frame.image = cv2.undistort(
            frame.image,
            self.camera_matrix,
            self.distortion_coefficients
        )

        return frame