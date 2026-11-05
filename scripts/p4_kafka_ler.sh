#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/venv/bin/python"

"$PYTHON" - <<'PY'
import json
import time
import uuid
from confluent_kafka import Consumer, TopicPartition

consumer = Consumer({
    "bootstrap.servers": "172.18.4.56:9092",
    "group.id": f"p4-demo-{uuid.uuid4()}",
    "enable.auto.commit": False,
})

def ler_ultimos(topico, quantidade):
    particao = TopicPartition(topico, 0)
    inicio, fim = consumer.get_watermark_offsets(
        particao, timeout=5
    )

    if fim <= inicio:
        return []

    primeiro = max(inicio, fim - quantidade)
    consumer.assign([TopicPartition(topico, 0, primeiro)])

    eventos = []
    prazo = time.monotonic() + 10

    while len(eventos) < fim - primeiro:
        if time.monotonic() >= prazo:
            break

        msg = consumer.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            raise RuntimeError(msg.error())
        if msg.offset() >= fim:
            break

        eventos.append(json.loads(msg.value()))

    consumer.unassign()
    return eventos

try:
    sessoes = ler_ultimos("ods.session.started", 1)

    if not sessoes:
        raise RuntimeError("Nenhuma sessão encontrada")

    sessao = sessoes[-1]
    session_id = sessao["session_id"]

    eventos = ler_ultimos("ods.p4.frame", 60)
    frames = [
        evento["payload"]["frame_id"]
        for evento in eventos
        if evento.get("session_id") == session_id
    ]

    print("\n========== KAFKA - P4 ==========")
    print("Fonte:", sessao["source_id"])
    print("Sessão:", session_id)
    print("Eventos de início encontrados: 1")
    print("Frames da sessão recuperados:", len(frames))

    if frames:
        print("Primeiro frame:", min(frames))
        print("Último frame:", max(frames))

    if set(frames) == set(range(60)):
        print("PUBLICAÇÃO E CONSUMO VALIDADOS!")
    else:
        print("ATENÇÃO: os últimos 60 eventos não correspondem")
        print("integralmente à última sessão de 60 frames.")

    print("================================")

finally:
    consumer.close()
PY
