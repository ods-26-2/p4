from src.v4l2_capture import V4L2Capture
from src.undistort import Undistorter


camera = V4L2Capture()
undistorter = Undistorter()

try:
    frame = camera.read()

    print("Frame original:")
    print("  ID:", frame.frame_id)
    print("  Timestamp:", frame.timestamp_ns)
    print("  Tamanho:", frame.image.shape)

    frame_corrigido = undistorter.process(frame)

    print()
    print("Frame após Undistorter:")
    print("  ID:", frame_corrigido.frame_id)
    print("  Timestamp:", frame_corrigido.timestamp_ns)
    print("  Tamanho:", frame_corrigido.image.shape)

finally:
    camera.release()