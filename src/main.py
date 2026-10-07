#EScolha de qual captura estamos fazendo (mockado por enquanto)
from .capture import WebcamCapture
from .fake_capture import FakeCapture
from .imx519_capture import IMX519Capture

from .undistort import Undistorter
from .metadata import FrameMetadata
import cv2

#
#camera = WebcamCapture()
#camera = FakeCapture()
camera = IMX519Capture()
#
undistorter = Undistorter()

frame = camera.read()
frame = undistorter.process(frame)

metadata = FrameMetadata(
    camera_id="camera_01",
    width=frame.image.shape[1],
    height=frame.image.shape[0],
    fps=camera.fps,
    is_undistorted=True
)

cv2.imwrite("frame_teste.jpg", frame.image)

print("Frame capturado!")
print("Tamanho:", frame.image.shape)
print("Frame ID:", frame.frame_id)
print("Timestamp:", frame.timestamp_ns)

print("Camera:", metadata.camera_id)
print("Resolução:", metadata.width, "x", metadata.height)
print("FPS:", metadata.fps)
print("Desdistorcido:", metadata.is_undistorted)

camera.release()