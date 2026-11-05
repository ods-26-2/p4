
import json
import os

from pathlib import Path

from .tsc_converter import TSCClockConverter
from .v4l2_source import V4L2Source
from .p4 import P4
from .clock import ClockConverter
from .events import montar_evento_frame, montar_evento_inicio_sessao
from .config import CAMERAS


# CONFIGURAÇÕES

CAMERA_SELECIONADA = os.getenv("P4_CAMERA", "imx519")

# Quantidade de quadros no modo diagnóstico
LIMITE_QUADROS = 30

# Limite opcional para o modo completo
LIMITE_QUADROS_COMPLETO = os.getenv("P4_FRAME_LIMIT")

MODO_DIAGNOSTICO = (
    os.getenv("P4_MODO_DIAGNOSTICO", "true").lower() == "true"
)

CONVERTER_TIMESTAMP_UTC = False

ATIVAR_KAFKA = (
    os.getenv("P4_ATIVAR_KAFKA", "true").lower() == "true"
)

NORMALIZAR_TSC = (
    os.getenv("P4_NORMALIZAR_TSC", "false").lower() == "true"
)

KAFKA_SERVIDOR = os.getenv(
    "P4_KAFKA_BOOTSTRAP_SERVERS"
)


def main():
    camera = None
    publisher = None
    kafka = None
    p4 = None

    config = CAMERAS[CAMERA_SELECIONADA]

    if not config["enabled"]:
        print(f"Câmera {CAMERA_SELECIONADA} desabilitada.")
        return

    try:
        # Define o limite de quadros
        if MODO_DIAGNOSTICO:
            limite = LIMITE_QUADROS

        elif LIMITE_QUADROS_COMPLETO is None:
            limite = None

        else:
            limite = int(LIMITE_QUADROS_COMPLETO)

            if limite <= 0:
                raise ValueError(
                    "P4_FRAME_LIMIT deve ser maior que zero."
                )

        # Inicializa a fonte de vídeo
        camera = V4L2Source(
            device=config["device"],
            width=config["width"],
            height=config["height"],
            pixel_format=config["pixel_format"],
            sensor_mode=config.get("sensor_mode")
        )

        # Inicializa o conversor TSC quando solicitado
        tsc_converter = None

        if NORMALIZAR_TSC:
            if CAMERA_SELECIONADA not in ("imx477", "imx519"):
                raise ValueError(
                    "Conversão TSC habilitada para uma fonte "
                    "que ainda não foi validada."
                )

            biblioteca = (
                Path(__file__).resolve().parent.parent
                / "build"
                / "libp4_tsc_clock.so"
            )

            tsc_converter = TSCClockConverter(
                str(biblioteca)
            )

            print(
                f"Conversor TSC ativado | "
                f"Offset: "
                f"{tsc_converter.offset_ns / 1_000_000:.3f} ms"
            )

        # Inicializa o P4
        p4 = P4(
            source=camera,
            source_id=config["source_id"],
            fps=config["fps"],
            raw=config["raw"],
            tsc_converter=tsc_converter
        )

        # Inicializa os serviços apenas no modo completo
        if not MODO_DIAGNOSTICO:
            from .shm_publisher import SHMPublisher

            publisher = SHMPublisher(
                socket_path=config["socket_path"],
                width=config["width"],
                height=config["height"]
            )

            if ATIVAR_KAFKA:
                from .kafka_publisher import KafkaPublisher

                if not KAFKA_SERVIDOR:
                    raise RuntimeError(
                        "Configure P4_KAFKA_BOOTSTRAP_SERVERS."
                    )

                kafka = KafkaPublisher(
                    bootstrap_servers=KAFKA_SERVIDOR
                )

        # Conversor UTC existente
        clock = (
            ClockConverter()
            if CONVERTER_TIMESTAMP_UTC
            else None
        )

        # Monta e publica o evento de início de sessão
        def informar_inicio_sessao(evento: dict):
            evento_formatado = montar_evento_inicio_sessao(
                evento
            )

            print(json.dumps(evento_formatado))

            if kafka is not None:
                kafka.publicar_inicio_sessao(
                    evento_formatado
                )

        # Processa cada frame recebido
        def receber_frame(frame, metadata):

            # MODO DIAGNÓSTICO
            if MODO_DIAGNOSTICO:

                # Exibe informações a cada 10 frames
                if frame.frame_index % 10 == 0:
                    print(
                        f"Frame {frame.frame_index} | "
                        f"{frame.width}x{frame.height} | "
                        f"Formato: {frame.pixel_format} | "
                        f"Tamanho: {len(frame.data)} bytes | "
                        f"Timestamp: {frame.timestamp_ns} ns | "
                        f"Origem: {frame.timestamp_origin} | "
                        f"FPS: {metadata.fps}"
                    )

                    # Timestamps normalizados para MONOTONIC_RAW
                    captura_raw = (
                        metadata.captured_at_monotonic_raw_ns
                    )

                    recebimento_raw = (
                        metadata.received_at_monotonic_raw_ns
                    )

                    # Compara apenas timestamps na mesma base
                    if (
                        captura_raw is not None
                        and recebimento_raw is not None
                    ):
                        diferenca_ms = (
                            recebimento_raw - captura_raw
                        ) / 1_000_000

                        print(
                            "Tempo estimado captura → leitura: "
                            f"{diferenca_ms:.3f} ms"
                        )

                return

            # MODO COMPLETO

            # Transmite o pacote P4R1 pelo SHM
            publisher.publish(frame, metadata)

            # Monta o evento do frame no formato B2
            evento = montar_evento_frame(metadata)

            # Conversão UTC existente, se habilitada
            if clock is not None:
                if metadata.captured_at_ns is not None:
                    evento["captured_at_utc"] = clock.to_utc(
                        metadata.captured_at_ns
                    )

            # Publica no Kafka, se estiver ativo
            if kafka is not None:
                kafka.publicar_frame(evento)

            # Imprime um evento a cada 30 quadros
            if frame.frame_index % 30 == 0:
                print(json.dumps(evento))

        # Identifica o modo de execução
        modo = (
            "DIAGNÓSTICO"
            if MODO_DIAGNOSTICO
            else "COMPLETO"
        )

        print(
            f"P4 iniciado | "
            f"Câmera: {CAMERA_SELECIONADA} | "
            f"Modo: {modo}"
        )

        # Inicia a captura
        p4.run(
            consumer=receber_frame,
            frame_limit=limite,
            on_session_started=informar_inicio_sessao
        )

        if MODO_DIAGNOSTICO:
            print("Diagnóstico finalizado com sucesso!")

    except KeyboardInterrupt:
        print("\nCaptura interrompida.")

    except Exception as erro:
        print(f"Erro no P4: {erro}")

    finally:
        # Métricas de captura
        if p4 is not None:
            print(
                "Métricas de captura:",
                json.dumps(p4.metrics.resumo())
            )

        # Libera SHM e câmera antes do Kafka
        try:
            if publisher is not None:
                print(
                    "Métricas de transmissão:",
                    json.dumps(publisher.resumo())
                )

                publisher.release()

        finally:
            try:
                if camera is not None:
                    camera.release()

            finally:
                if kafka is not None:
                    kafka.release()

                print("Recursos de captura liberados.")


if __name__ == "__main__":
    main()
