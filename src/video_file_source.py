
import time

import cv2

from .frame import Frame
from .source import VideoSource


class VideoFileSource(VideoSource):
    def __init__(self, video_path: str):
        self.video_path = video_path

        self.capture = cv2.VideoCapture(video_path)

        if not self.capture.isOpened():
            raise RuntimeError(
                f"Não foi possível abrir o vídeo: {video_path}"
            )

        self.width = int(
            self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        )

        self.height = int(
            self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

        self.fps = float(
            self.capture.get(cv2.CAP_PROP_FPS)
        )

        if self.fps <= 0:
            self.capture.release()
            raise RuntimeError(
                "Não foi possível identificar o FPS do vídeo."
            )

        self.frame_index = 0
        self.start_ns = None

    def read(self) -> Frame:
        # Marca o início da reprodução simulada
        if self.start_ns is None:
            self.start_ns = time.monotonic_ns()

        # Calcula quando o próximo frame deve ser entregue
        intervalo_ns = 1_000_000_000 / self.fps

        instante_alvo_ns = (
            self.start_ns
            + int(self.frame_index * intervalo_ns)
        )

        # Aguarda para simular a taxa de quadros original
        tempo_restante_ns = (
            instante_alvo_ns - time.monotonic_ns()
        )

        if tempo_restante_ns > 0:
            time.sleep(
                tempo_restante_ns / 1_000_000_000
            )

        # Decodifica um frame do arquivo MP4
        sucesso, imagem = self.capture.read()

        if not sucesso:
            raise StopIteration(
                "Fim do arquivo de vídeo."
            )

        timestamp_ns = time.clock_gettime_ns(
            time.CLOCK_MONOTONIC_RAW
        )

        height, width = imagem.shape[:2]

        frame = Frame(
            data=imagem.tobytes(),
            width=width,
            height=height,
            pixel_format="BGR8",
            timestamp_ns=timestamp_ns,
            frame_index=self.frame_index,
            timestamp_origin="file_playback_raw"
        )

        self.frame_index += 1

        return frame

    def release(self) -> None:
        self.capture.release()
