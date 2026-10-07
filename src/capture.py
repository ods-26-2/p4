from .v4l2_capture import V4L2Capture


class Capture:
    def read(self):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError


class WebcamCapture(Capture):
    def __init__(self, device="/dev/video0"):
        self.camera = V4L2Capture(device)

        # Por enquanto, a câmera está configurada em aproximadamente 30 FPS.
        self.fps = 30.0

    def read(self):
        return self.camera.read()

    def release(self):
        self.camera.release()