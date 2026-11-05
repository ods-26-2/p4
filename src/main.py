
import json
import os

from pathlib import Path

from .video_file_source import VideoFileSource
from .tsc_converter import TSCClockConverter
from .v4l2_source import V4L2Source
from .p4 import P4
from .clock import ClockConverter
from .events import montar_evento_frame, montar_evento_inicio_sessao
from .config import CAMERAS


# ============================================================
# CONFIGURAÇÕES
# ============================================================

CAMERA_SELECIONADA = os.getenv("P4_CAMERA", "imx519")

# "camera": câmera CSI (IMX519 ou IMX477)
# "file": arquivo de vídeo simulando uma câmera
TIPO_FONTE = os.getenv("P4_SOURCE", "camera").lower()
CAMINHO_VIDEO = os.getenv("P4_VIDEO_PATH")

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


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    fonte = None
    publisher = None
    kafka = None
    p4 = None

    # --------------------------------------------------------
    # 1. Validação da fonte selecionada
    # --------------------------------------------------------

    if TIPO_FONTE == "camera":
        config = CAMERAS.get(CAMERA_SELECIONADA)

        if config is None:
            print(
                f"Câmera desconhecida: {CAMERA_SELECIONADA}"
            )
            return

        if not config["enabled"]:
            print(
                f"Câmera {CAMERA_SELECIONADA} desabilitada."
            )
            return

    elif TIPO_FONTE == "file":
        if not CAMINHO_VIDEO:
            print(
                "Configure P4_VIDEO_PATH para utilizar um vídeo."
            )
            return

        config = None

    else:
        print(
            f"Tipo de fonte desconhecido: {TIPO_FONTE}"
        )
        return

    try:
        # ----------------------------------------------------
        # 2. Limite de quadros
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 3. Inicialização da fonte de vídeo
        # ----------------------------------------------------

        if TIPO_FONTE == "camera":

            fonte = V4L2Source(
                device=config["device"],
                width=config["width"],
                height=config["height"],
                pixel_format=config["pixel_format"],
                sensor_mode=config.get("sensor_mode")
            )

        else:
            # Vídeo MP4 simulando uma câmera
            caminho = Path(CAMINHO_VIDEO).expanduser()

            if not caminho.is_file():
                raise FileNotFoundError(
                    f"Vídeo não encontrado: {caminho}"
                )

            fonte = VideoFileSource(str(caminho))

            config = {
                "source_id": f"file_{caminho.stem}",
                "width": fonte.width,
                "height": fonte.height,
                "fps": fonte.fps,
                "pixel_format": "BGR8",
                "raw": False,
                "socket_path": "/tmp/p4_file_shm"
            }

            print(
                f"Arquivo de vídeo: {caminho}"
            )

            print(
                f"Vídeo: {fonte.width}x{fonte.height} | "
                f"FPS: {fonte.fps} | "
                f"Formato: BGR8"
            )

        # ----------------------------------------------------
        # 4. Conversor TSC (somente câmeras CSI)
        # ----------------------------------------------------

        tsc_converter = None

        if NORMALIZAR_TSC and TIPO_FONTE == "camera":

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

        elif NORMALIZAR_TSC and TIPO_FONTE == "file":
            print(
                "Conversão TSC ignorada para arquivo de vídeo."
            )

        # ----------------------------------------------------
        # 5. Inicialização do P4
        # ----------------------------------------------------

        p4 = P4(
            source=fonte,
            source_id=config["source_id"],
            fps=config["fps"],
            raw=config["raw"],
            tsc_converter=tsc_converter
        )

        # ----------------------------------------------------
        # 6. Serviços do modo completo
        # ----------------------------------------------------

        if not MODO_DIAGNOSTICO:

            from .shm_publisher import SHMPublisher

            publisher = SHMPublisher(
                socket_path=config["socket_path"],
                width=config["width"],
                height=config["height"],
                pixel_format=config["pixel_format"]
            )

            print(
                f"SHM configurado: {config['socket_path']}"
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

        # ----------------------------------------------------
        # 7. Conversor UTC existente
        # ----------------------------------------------------

        clock = (
            ClockConverter()
            if CONVERTER_TIMESTAMP_UTC
            else None
        )

        # ----------------------------------------------------
        # 8. Evento de início de sessão
        # ----------------------------------------------------

        def informar_inicio_sessao(evento: dict):

            evento_formatado = montar_evento_inicio_sessao(
                evento
            )

            print(json.dumps(evento_formatado))

            if kafka is not None:
                kafka.publicar_inicio_sessao(
                    evento_formatado
                )

        # ----------------------------------------------------
        # 9. Processamento de cada frame
        # ----------------------------------------------------

        def receber_frame(frame, metadata):

            # MODO DIAGNÓSTICO
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

                    captura_raw = (
                        metadata.captured_at_monotonic_raw_ns
                    )

                    recebimento_raw = (
                        metadata.received_at_monotonic_raw_ns
                    )

                    # Compara somente quando existe um instante
                    # de captura física na mesma base temporal.
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

            # Publica o pacote P4R1 no SHM
            publisher.publish(frame, metadata)

            # Monta o evento no formato B2
            evento = montar_evento_frame(metadata)

            # Conversão UTC, se habilitada
            if clock is not None:

                if metadata.captured_at_ns is not None:

                    evento["captured_at_utc"] = clock.to_utc(
                        metadata.captured_at_ns
                    )

            # Envia para o Kafka, se estiver ativo
            if kafka is not None:
                kafka.publicar_frame(evento)

            # Imprime um evento a cada 30 quadros
            if frame.frame_index % 30 == 0:
                print(json.dumps(evento))

        # ----------------------------------------------------
        # 10. Identificação da execução
        # ----------------------------------------------------

        modo = (
            "DIAGNÓSTICO"
            if MODO_DIAGNOSTICO
            else "COMPLETO"
        )

        print(
            f"P4 iniciado | "
            f"Fonte: {TIPO_FONTE} | "
            f"Identificação: {config['source_id']} | "
            f"Modo: {modo}"
        )

        # ----------------------------------------------------
        # 11. Execução
        # ----------------------------------------------------

        try:
            p4.run(
                consumer=receber_frame,
                frame_limit=limite,
                on_session_started=informar_inicio_sessao
            )

        except StopIteration:
            if TIPO_FONTE == "file":
                print(
                    "Fim do arquivo de vídeo. "
                    "Reprodução encerrada normalmente."
                )
            else:
                raise

        if MODO_DIAGNOSTICO:
            print(
                "Diagnóstico finalizado com sucesso!"
            )

    except KeyboardInterrupt:
        print("\nCaptura interrompida.")

    except Exception as erro:
        print(f"Erro no P4: {erro}")

    finally:
        # ----------------------------------------------------
        # 12. Métricas e liberação dos recursos
        # ----------------------------------------------------

        if p4 is not None:
            print(
                "Métricas de captura:",
                json.dumps(p4.metrics.resumo())
            )

        try:
            if publisher is not None:

                print(
                    "Métricas de transmissão:",
                    json.dumps(publisher.resumo())
                )

                publisher.release()

        finally:
            try:
                if fonte is not None:
                    fonte.release()

            finally:
                if kafka is not None:
                    kafka.release()

                print(
                    "Recursos de captura liberados."
                )


if __name__ == "__main__":
    main()
