
import json
import struct

from .metadata import FrameMetadata


def criar_cabecalho(metadata: FrameMetadata, tamanho_dados: int) -> bytes:
    campos = {
        "source_id": metadata.source_id,
        "session_id": metadata.session_id,
        "frame_id": metadata.frame_index,
        "timestamp": metadata.captured_at_ns,
        "width": metadata.width,
        "height": metadata.height,
        "format": metadata.pixel_format,
        "raw": metadata.raw,
        "data_size": tamanho_dados
    }

    # Obtém o timestamp normalizado, quando disponível.
    timestamp_raw = getattr(
        metadata,
        "captured_at_monotonic_raw_ns",
        None
    )

    # Preserva a compatibilidade com metadados antigos.
    if timestamp_raw is not None:
        campos["timestamp_monotonic_raw_ns"] = timestamp_raw
        campos["timestamp_monotonic_raw_clock"] = (
            "CLOCK_MONOTONIC_RAW"
        )

    # Instante de recebimento/reprodução na base MONOTONIC_RAW
    recebimento_raw = getattr(
        metadata,
        "received_at_monotonic_raw_ns",
        None
    )

    if recebimento_raw is not None:
        campos["received_at_monotonic_raw_ns"] = recebimento_raw
        campos["received_at_monotonic_raw_clock"] = (
            "CLOCK_MONOTONIC_RAW"
        )

    conteudo = json.dumps(campos).encode("utf-8")

    return b"P4R1" + struct.pack("!I", len(conteudo)) + conteudo


def ler_cabecalho(pacote: bytes) -> tuple[dict, int]:
    if len(pacote) < 8 or pacote[:4] != b"P4R1":
        raise ValueError("Identificador inválido ou cabeçalho incompleto.")

    tamanho_json = struct.unpack("!I", pacote[4:8])[0]
    inicio_raw = 8 + tamanho_json

    if len(pacote) < inicio_raw:
        raise ValueError("Cabeçalho JSON incompleto.")

    campos = json.loads(pacote[8:inicio_raw].decode("utf-8"))

    tamanho_declarado = campos["data_size"]
    tamanho_recebido = len(pacote) - inicio_raw

    if type(tamanho_declarado) is not int or tamanho_declarado < 0:
        raise ValueError("Tamanho RAW declarado inválido.")

    if tamanho_recebido != tamanho_declarado:
        raise ValueError(
            "O tamanho dos dados RAW não corresponde ao declarado."
        )

    return campos, inicio_raw
