
import uuid
from collections.abc import Callable
from time import CLOCK_MONOTONIC_RAW, clock_gettime_ns, monotonic_ns

from .source import VideoSource
from .frame import Frame
from .metadata import FrameMetadata
from .capture_metrics import CaptureMetrics
from .tsc_converter import TSCClockConverter


class P4:
    def __init__(
        self,
        source: VideoSource,
        source_id: str,
        fps: float | None = None,
        raw: bool = False,
        tsc_converter: TSCClockConverter | None = None
    ):
        self.source = source
        self.source_id = source_id
        self.session_id = str(uuid.uuid4())
        self.fps = fps
        self.raw = raw
        self.last_capture_ns = None
        self.metrics = CaptureMetrics()

        # Opcional: utilizado somente para fontes com timestamps TSC
        self.tsc_converter = tsc_converter

    def read(self) -> tuple[Frame, FrameMetadata]:
        frame = self.source.read()

        # Registra o quadro recebido e verifica a sequência
        self.metrics.atualizar(frame)

        captured_at_monotonic_raw_ns = None
        received_at_monotonic_raw_ns = None

        if frame.timestamp_origin.startswith("driver_"):
            # Preserva o timestamp original do driver
            captured_at_ns = frame.timestamp_ns
            received_at_ns = monotonic_ns()

            # Converte somente quando o conversor foi configurado
            # explicitamente para uma fonte que utiliza TSC
            if self.tsc_converter is not None:
                captured_at_monotonic_raw_ns = (
                    self.tsc_converter.to_monotonic_raw_ns(
                        captured_at_ns
                    )
                )

                received_at_monotonic_raw_ns = clock_gettime_ns(
                    CLOCK_MONOTONIC_RAW
                )

        else:
            # Mantém o comportamento atual das outras fontes
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
            received_at_ns=received_at_ns,
            captured_at_monotonic_raw_ns=(
                captured_at_monotonic_raw_ns
            ),
            received_at_monotonic_raw_ns=(
                received_at_monotonic_raw_ns
            )
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
