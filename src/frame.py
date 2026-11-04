from dataclasses import dataclass


@dataclass
class Frame:
    data: bytes
    width: int
    height: int
    pixel_format: str
    timestamp_ns: int
    frame_index: int
    timestamp_origin: str = "received"