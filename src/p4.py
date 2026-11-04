
import uuid
from collections.abc import Callable
from time import monotonic_ns

from .source import VideoSource
from .frame import Frame
from .metadata import FrameMetadata
from .capture_metrics import CaptureMetrics

class P4:
    def __init__(
        self,
        source: VideoSource,
        source_id: str,
        fps: float | None = None,
        raw: bool = False
    ):
        self.source = source
        self.source_id = source_id
        self.session_id = str(uuid.uuid4())
        self.fps = fps
        self.raw = raw
        self.last_capture_ns = None
        self.metrics = CaptureMetrics()

    def read(self) -> tuple[Frame, FrameMetadata]:
        frame = self.source.read()

        # Registra o quadro recebido e verifica a sequência
        self.metrics.atualizar(frame)

        if frame.timestamp_origin.startswith("driver_"):
            captured_at_ns = frame.timestamp_ns
            received_at_ns = monotonic_ns()
        else:
            captured_at_ns = None
            received_at_ns = frame.timestamp_ns

        measured_fps = None

        if captured_at_ns is not None:
            if self.last_capture_ns is not None:
                intervalo_ns = captured_at_ns - self.last_capture_ns

                if intervalo_ns > 0:
                    measured_fps = round(
                        1_000_000_000 / intervalo_ns,
                        2
                    )

            self.last_capture_ns = captured_at_ns

        metadata = FrameMetadata(
            source_id=self.source_id,
            session_id=self.session_id,
            frame_index=frame.frame_index,
            width=frame.width,
            height=frame.height,
            pixel_format=frame.pixel_format,
            fps=self.fps if self.fps is not None else measured_fps,
            raw=self.raw,
            captured_at_ns=captured_at_ns,
            received_at_ns=received_at_ns
        )

        return frame, metadata



    def run(
        self,
        consumer: Callable[[Frame, FrameMetadata], None],
        frame_limit: int | None = None,
        on_session_started: Callable[[dict], None] | None = None
    ) -> None:
    
        count = 0
    
        while frame_limit is None or count < frame_limit:
            frame, metadata = self.read()
    
            # Anuncia a sessão após capturar o primeiro quadro
            if count == 0 and on_session_started is not None:
                event = {
                    "event": "ods.session.started",
                    "source_id": self.source_id,
                    "session_id": self.session_id
                }
    
                on_session_started(event)
    
            consumer(frame, metadata)
    
            count += 1

    def release(self) -> None:
        self.source.release()
