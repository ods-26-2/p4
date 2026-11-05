#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/venv/bin/python"
MODO="${1:-ajuda}"

if [[ "$MODO" == "ajuda" || "$MODO" == "--help" ]]; then
    echo "Uso:"
    echo "  ./scripts/p4_demo.sh imx519"
    echo "  ./scripts/p4_demo.sh imx477"
    echo "  ./scripts/p4_demo.sh video [caminho.mp4]"
    echo "  ./scripts/p4_demo.sh kafka [caminho.mp4]"
    exit 0
fi

if [[ ! -x "$PYTHON" ]]; then
    echo "Erro: ambiente virtual nao encontrado em $ROOT/venv"
    exit 1
fi

cd "$ROOT"

export PYTHONPATH="$ROOT:/usr/lib/python3/dist-packages${PYTHONPATH:+:$PYTHONPATH}"
export P4_MODO_DIAGNOSTICO=false
export P4_NORMALIZAR_TSC="${P4_NORMALIZAR_TSC:-false}"
export P4_ATIVAR_KAFKA=false

unset P4_FRAME_LIMIT

case "$MODO" in
    imx519|imx477)
        export P4_SOURCE=camera
        export P4_CAMERA="$MODO"
        FONTE="$MODO"
        ;;

    video|kafka)
        VIDEO="${2:-${P4_VIDEO_PATH:-$ROOT/../videos/cars_extended.mp4}}"

        if [[ ! -f "$VIDEO" ]]; then
            echo "Erro: video nao encontrado: $VIDEO"
            exit 1
        fi

        export P4_SOURCE=file
        export P4_VIDEO_PATH="$VIDEO"
        FONTE="file"

        if [[ "$MODO" == "kafka" ]]; then
            export P4_ATIVAR_KAFKA=true
            export P4_FRAME_LIMIT=60
            export P4_KAFKA_BOOTSTRAP_SERVERS="${P4_KAFKA_BOOTSTRAP_SERVERS:-172.18.4.56:9092}"
        fi
        ;;

    *)
        echo "Modo desconhecido: $MODO"
        echo "Use ./scripts/p4_demo.sh --help"
        exit 1
        ;;
esac

# Impede duas instancias deste script na mesma fonte.
exec 9>"/tmp/p4_demo_${FONTE}.lock"

if ! flock -n 9; then
    echo "Erro: a fonte $FONTE ja esta sendo utilizada por outra instancia."
    exit 1
fi

echo "=================================="
echo " P4 - Fonte de Video"
echo "=================================="
echo " Modo: $MODO"
echo " Kafka: $P4_ATIVAR_KAFKA"
echo " Para encerrar: Ctrl+C"
echo "=================================="

exec "$PYTHON" -m src.main
