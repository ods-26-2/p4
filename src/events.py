
import uuid
from datetime import datetime, timezone

from .metadata import FrameMetadata


def montar_evento_frame(metadata: FrameMetadata) -> dict:
    return {
        "message_id": str(uuid.uuid4()),
        "message_type": "event",
        "schema": "ods.p4.frame",
        "schema_version": "1.0",
        "producer": "P4",
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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


def montar_evento_inicio_sessao(evento: dict) -> dict:
    return {
        "message_id": str(uuid.uuid4()),
        "message_type": "event",
        "schema": "ods.session.started",
        "schema_version": "1.0",
        "producer": "P4",
        "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_id": evento["source_id"],
        "session_id": evento["session_id"],
        "payload": {
            "source_id": evento["source_id"],
            "session_id": evento["session_id"]
        }
    }
