
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
    captured_at_ns: int | None
    received_at_ns: int | None
