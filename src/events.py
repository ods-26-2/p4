
import uuid
from datetime import datetime, timezone

from .metadata import FrameMetadata


def montar_evento_frame(metadata: FrameMetadata) -> dict:
    payload = {
        "frame_id": metadata.frame_index,
        "timestamp": metadata.captured_at_ns,
        "width": metadata.width,
        "height": metadata.height,
        "format": metadata.pixel_format,
        "fps": metadata.fps,
        "raw": metadata.raw
    }

    # Adiciona o timestamp normalizado quando disponível.
    timestamp_raw = getattr(
        metadata,
        "captured_at_monotonic_raw_ns",
        None
    )

    if timestamp_raw is not None:
        payload["timestamp_monotonic_raw_ns"] = timestamp_raw
        payload["timestamp_monotonic_raw_clock"] = (
            "CLOCK_MONOTONIC_RAW"
        )

    return {
        "message_id": str(uuid.uuid4()),
        "message_type": "event",
        "schema": "ods.p4.frame",
        "schema_version": "1.0",
        "producer": "P4",
        "occurred_at": datetime.now(
            timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "source_id": metadata.source_id,
        "session_id": metadata.session_id,
        "payload": payload
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
