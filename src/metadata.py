from dataclasses import dataclass


@dataclass
class FrameMetadata:
    source_id: str
    session_id: str
    frame_index: int
    width: int
    height: int
    pixel_format: str
    fps: float | None
    raw: bool

    # Campos existentes: mantidos para compatibilidade
    captured_at_ns: int | None
    received_at_ns: int | None

    # Novos campos: timestamps na mesma base temporal
    captured_at_monotonic_raw_ns: int | None = None
    received_at_monotonic_raw_ns: int | None = None