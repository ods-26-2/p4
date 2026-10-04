from dataclasses import dataclass

@dataclass
class FrameMetadata:
    camera_id: str
    width: int
    height: int
    fps: float
    is_undistorted: bool