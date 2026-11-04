
import json
import os

from .v4l2_source import V4L2Source
from .p4 import P4
from .clock import ClockConverter
from .events import montar_evento_frame, montar_evento_inicio_sessao
from .config import CAMERAS


# CONFIGURAÇÕES

CAMERA_SELECIONADA = os.getenv("P4_CAMERA", "imx519")

# Quantidade de quadros no modo diagnóstico
LIMITE_QUADROS = 30

MODO_DIAGNOSTICO = (
    os.getenv("P4_MODO_DIAGNOSTICO", "true").lower() == "true"
)

CONVERTER_TIMESTAMP_UTC = False
ATIVAR_KAFKA = True

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
        # Inicializa a fonte de vídeo
        camera = V4L2Source(
            device=config["device"],
            width=config["width"],
            height=config["height"],
            pixel_format=config["pixel_format"],
            sensor_mode=config.get("sensor_mode")
        )

        # Inicializa o P4
        p4 = P4(
            source=camera,
            source_id=config["source_id"],
            fps=config["fps"],
            raw=config["raw"]
        )

        # Inicializa os serviços apenas no modo completo
        if not MODO_DIAGNOSTICO:
            from .shm_publisher import SHMPublisher
            from .kafka_publisher import KafkaPublisher

            publisher = SHMPublisher(
                socket_path=config["socket_path"],
                width=config["width"],
                height=config["height"]
            )

            if ATIVAR_KAFKA:
                if not KAFKA_SERVIDOR:
                    raise RuntimeError(
                        "Configure P4_KAFKA_BOOTSTRAP_SERVERS."
                    )

                kafka = KafkaPublisher(
                    bootstrap_servers=KAFKA_SERVIDOR
                )

        clock = (
            ClockConverter()
            if CONVERTER_TIMESTAMP_UTC
            else None
        )

        # Monta e publica o evento de início de sessão
        def informar_inicio_sessao(evento: dict):
            evento_formatado = montar_evento_inicio_sessao(evento)

            print(json.dumps(evento_formatado))

            if kafka is not None:
                kafka.publicar_inicio_sessao(evento_formatado)

        def receber_frame(frame, metadata):
            # Modo diagnóstico: apenas verifica a captura
            if MODO_DIAGNOSTICO:
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

                return

            # Modo completo: transmite o pacote P4R1 pelo SHM
            publisher.publish(frame, metadata)

            # Monta o evento do frame no formato B2
            evento = montar_evento_frame(metadata)

            if clock is not None:
                if metadata.captured_at_ns is not None:
                    evento["captured_at_utc"] = clock.to_utc(
                        metadata.captured_at_ns
                    )

            # Publica o evento no Kafka, se estiver ativo
            if kafka is not None:
                kafka.publicar_frame(evento)

            # Imprime um evento a cada 30 quadros
            if frame.frame_index % 30 == 0:
                print(json.dumps(evento))

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

        p4.run(
            consumer=receber_frame,
            frame_limit=(
                LIMITE_QUADROS
                if MODO_DIAGNOSTICO
                else None
            ),
            on_session_started=informar_inicio_sessao
        )

        if MODO_DIAGNOSTICO:
            print("Diagnóstico finalizado com sucesso!")

    except KeyboardInterrupt:
        print("\nCaptura interrompida.")

    except Exception as erro:
        print(f"Erro no P4: {erro}")

    finally:
        if p4 is not None:
            print(
                "Métricas de captura:",
                json.dumps(p4.metrics.resumo())
            )

        # Libera o SHM e a câmera antes de aguardar o Kafka
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
