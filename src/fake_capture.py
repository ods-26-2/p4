import numpy as np

from .frame import Frame


class FakeCapture:
    def __init__(self):
        self.fps = 30.0
        self.frame_id = 0

    def read(self):
        image = np.zeros((480, 640, 3), dtype=np.uint8)

        frame = Frame(
            image=image,
            timestamp_ns=0,
            frame_id=self.frame_id
        )

        self.frame_id += 1

        return frame

    def release(self):
        pass