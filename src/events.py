
from .metadata import FrameMetadata


def montar_evento_frame(metadata: FrameMetadata) -> dict:
    return {
        "schema": "ods.p4.frame",
        "producer": "P4",
        "source_id": metadata.source_id,
        "session_id": metadata.session_id,
        "payload": {
            "frame_id": metadata.frame_index,
            "timestamp": metadata.captured_at_ns,
            "width": metadata.width,
            "height": metadata.height,
            "format": metadata.pixel_format,
            "fps": metadata.fps,
            "raw": metadata.raw
        }
    }
