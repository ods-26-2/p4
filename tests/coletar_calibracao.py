from src.v4l2_capture import V4L2Capture
import cv2


camera = V4L2Capture()

try:
    for i in range(10):
        frame = camera.read()

        filename = f"data/dataset_calibracao/frame_{i:03d}.jpg"

        cv2.imwrite(filename, frame.image)

        print(
            f"Imagem {i + 1}/10 salva: {filename} "
            f"| Frame ID: {frame.frame_id} "
            f"| Timestamp: {frame.timestamp_ns}"
        )

finally:
    camera.release()