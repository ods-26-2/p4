
import cv2
from pathlib import Path


class VideoRecorder:
    def __init__(self, width, height, fps, output_path="videos/video_capturado.mp4"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        self.writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            fps,
            (width, height)
        )

        if not self.writer.isOpened():
            raise RuntimeError("Não foi possível criar o arquivo de vídeo.")

    def write(self, frame):
        self.writer.write(frame.image)

    def release(self):
        self.writer.release()
