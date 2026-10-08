import gi
import numpy as np

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from .frame import Frame
from .camera_config import CAMERAS

MODOS_SUPORTADOS = CAMERAS["emeet"]["modes"]


Gst.init(None)


class GStreamerCapture:
    def __init__(
        self,
        device="/dev/video0",
        width=1280,
        height=720,
        fps=30
    ):
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_id = 0

        modo = (width, height)

        if modo not in MODOS_SUPORTADOS:
            raise ValueError(
                f"Resolução não suportada: {width}x{height}."
            )

        if fps not in MODOS_SUPORTADOS[modo]:
            fps_disponiveis = MODOS_SUPORTADOS[modo]

            raise ValueError(
                f"FPS {fps} não suportado para {width}x{height}. "
                f"FPS disponíveis: {fps_disponiveis}."
            )

        if width <= 0 or height <= 0:
            raise ValueError("Resolução inválida.")

        if not 1 <= fps <= 60:
            raise ValueError("O FPS deve estar entre 1 e 60.")

        pipeline_description = (
            f"v4l2src device={device} "
            f"! image/jpeg,width={width},height={height},"
            f"framerate={fps}/1 "
            "! jpegdec "
            "! videoconvert "
            "! video/x-raw,format=BGR "
            "! appsink name=sink max-buffers=1 drop=true"
        )

        self.pipeline = Gst.parse_launch(pipeline_description)
        self.sink = self.pipeline.get_by_name("sink")
        self.sink.set_property("sync", False)

        result = self.pipeline.set_state(Gst.State.PLAYING)

        if result == Gst.StateChangeReturn.FAILURE:
            self.pipeline.set_state(Gst.State.NULL)
            raise RuntimeError("Não foi possível iniciar o GStreamer.")

    def read(self):
        sample = self.sink.emit(
            "try-pull-sample",
            5 * Gst.SECOND
        )

        if sample is None:
            raise RuntimeError("Nenhum frame recebido em 5 segundos.")

        buffer = sample.get_buffer()
        caps = sample.get_caps()
        structure = caps.get_structure(0)

        width = structure.get_value("width")
        height = structure.get_value("height")

        success, mapped = buffer.map(Gst.MapFlags.READ)

        if not success:
            raise RuntimeError("Não foi possível acessar o frame.")

        try:
            image = np.frombuffer(
                mapped.data,
                dtype=np.uint8
            ).reshape(height, width, 3).copy()
        finally:
            buffer.unmap(mapped)

        timestamp_ns = buffer.pts

        if timestamp_ns == Gst.CLOCK_TIME_NONE:
            raise RuntimeError("O frame não possui PTS válido.")

        frame = Frame(
            image=image,
            timestamp_ns=int(timestamp_ns),
            frame_id=self.frame_id
        )

        self.frame_id += 1

        return frame

    def release(self):
        self.pipeline.set_state(Gst.State.NULL)