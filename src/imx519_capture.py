from picamera2 import Picamera2

from .frame import Frame


class IMX519Capture:
    def __init__(self):
        self.camera = Picamera2()

        config = self.camera.create_preview_configuration(
            main={"size": (1280, 720)}
        )

        self.camera.configure(config)
        self.camera.start()

        self.frame_id = 0
        self.fps = 30.0

    def read(self):
        image = self.camera.capture_array()
        metadata = self.camera.capture_metadata()

        frame = Frame(
            image=image,
            timestamp_ns=metadata["SensorTimestamp"],
            frame_id=self.frame_id
        )

        self.frame_id += 1

        return frame

    def release(self):
        self.camera.stop()