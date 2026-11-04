
import json
import os

from .v4l2_source import V4L2Source
from .p4 import P4
from .clock import ClockConverter
from .events import montar_evento_frame
from .config import CAMERAS

# CONFIGURAÇÕES

CAMERA_SELECIONADA = "emeet"

# True: apenas captura e verifica os quadros
# False: ativa a execução completa do P4
MODO_DIAGNOSTICO = True

# Quantidade de quadros no modo diagnóstico
LIMITE_QUADROS = 30

CONVERTER_TIMESTAMP_UTC = False
ATIVAR_KAFKA = True

KAFKA_SERVIDOR = os.getenv(
    "P4_KAFKA_BOOTSTRAP_SERVERS"
)


def main():
    camera = None
    publisher = None
    kafka = None

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
            pixel_format=config["pixel_format"]
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

        def informar_inicio_sessao(evento: dict):
            print(json.dumps(evento))

            if kafka is not None:
                kafka.publicar_inicio_sessao(evento)

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

            # Modo completo: transmite o vídeo
            publisher.publish(frame)

            # Monta os metadados
            evento = montar_evento_frame(metadata)

            if clock is not None:
                if metadata.captured_at_ns is not None:
                    evento["captured_at_utc"] = clock.to_utc(
                        metadata.captured_at_ns
                    )

            # Publica todos os eventos no Kafka
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
        if kafka is not None:
            kafka.release()

        if publisher is not None:
            publisher.release()

        if camera is not None:
            camera.release()

        print("Recursos liberados.")


if __name__ == "__main__":
    main()
