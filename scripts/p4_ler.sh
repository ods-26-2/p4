#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODO="${1:-video}"

case "$MODO" in
    imx519)
        SOCKET="/tmp/p4_imx519_shm"
        ;;
    imx477)
        SOCKET="/tmp/p4_imx477_shm"
        ;;
    video)
        SOCKET="/tmp/p4_file_shm"
        ;;
    *)
        echo "Uso: ./scripts/p4_ler.sh {imx519|imx477|video}"
        exit 1
        ;;
esac

cd "$ROOT"

PYTHONPATH="$ROOT:/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}" \
"$ROOT/venv/bin/python" - "$SOCKET" <<'PY'
import sys
import hashlib
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from src.shm_protocol import ler_cabecalho

socket = sys.argv[1]

Gst.init(None)

pipeline = Gst.parse_launch(
    f"shmsrc socket-path={socket} "
    "is-live=true do-timestamp=true "
    "! application/x-ods-frame,version=1 "
    "! appsink name=sink sync=false max-buffers=1 drop=true"
)

try:
    if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
        raise RuntimeError("Falha ao iniciar leitor SHM")

    sink = pipeline.get_by_name("sink")
    sample = sink.emit("try-pull-sample", 5 * Gst.SECOND)

    if sample is None:
        raise RuntimeError("Nenhum frame recebido em 5 segundos")

    buffer = sample.get_buffer()
    ok, mapped = buffer.map(Gst.MapFlags.READ)

    if not ok:
        raise RuntimeError("Falha ao ler buffer")

    try:
        pacote = bytes(mapped.data)
    finally:
        buffer.unmap(mapped)

    campos, inicio = ler_cabecalho(pacote)
    pixels = pacote[inicio:]

    print("\n========== FRAME RECEBIDO ==========")
    print("Fonte:", campos["source_id"])
    print("Frame:", campos["frame_id"])
    print("Sessão:", campos["session_id"])
    print("Resolução:", campos["width"], "x", campos["height"])
    print("Formato:", campos["format"])
    print("Bytes:", len(pixels))
    print("SHA-256:", hashlib.sha256(pixels).hexdigest())

    if campos["format"] == "BGR8":
        import cv2
        import numpy as np

        altura = campos["height"]
        largura = campos["width"]

        imagem = np.frombuffer(
            pixels, dtype=np.uint8
        ).reshape(altura, largura, 3)

        destino = "/tmp/p4_frame_recebido.png"

        if not cv2.imwrite(destino, imagem):
            raise RuntimeError("Falha ao salvar imagem")

        print("Imagem salva:", destino)

    elif campos["format"] == "RG10":
        import cv2
        import numpy as np

        altura = campos["height"]
        largura = campos["width"]

        raw16 = np.frombuffer(
            pixels, dtype="<u2"
        ).reshape(altura, largura)

        raw8 = (raw16 >> 2).astype(np.uint8)
        imagem = cv2.cvtColor(raw8, cv2.COLOR_BayerRG2BGR)

        destino = f"/tmp/p4_{campos['source_id']}_recebido.png"

        if not cv2.imwrite(destino, imagem):
            raise RuntimeError("Falha ao salvar imagem RAW convertida")

        print("Imagem convertida e salva:", destino)

    else:
        print("Formato sem conversão de imagem configurada")

    print("====================================")
    print("RECEBIMENTO VALIDADO!")

finally:
    pipeline.set_state(Gst.State.NULL)
PY
