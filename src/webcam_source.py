
import cv2
import time

from .frame import Frame
from .source import VideoSource


class WebcamSource(VideoSource):
    def __init__(self, device="/dev/video0"):
        self.camera = cv2.VideoCapture(device, cv2.CAP_V4L2)

        if not self.camera.isOpened():
            raise RuntimeError("Não foi possível abrir a câmera.")

        self.camera.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*"MJPG")
        )

        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.frame_index = 0

    def read(self) -> Frame:
        success, image = self.camera.read()
        received_at_ns = time.monotonic_ns()

        if not success:
            raise RuntimeError("Falha ao capturar o quadro.")

        height, width = image.shape[:2]

        frame = Frame(
            data=image.tobytes(),
            width=width,
            height=height,
            pixel_format="BGR",
            timestamp_ns=received_at_ns,
            frame_index=self.frame_index
        )

        self.frame_index += 1

        return frame

    def release(self) -> None:
        self.camera.release()
