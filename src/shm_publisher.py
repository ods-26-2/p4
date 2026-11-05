
import os
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from .frame import Frame
from .metadata import FrameMetadata
from .shm_protocol import criar_cabecalho

Gst.init(None)


class SHMPublisher:
    def __init__(
        self,
        socket_path="/tmp/p4_video_shm",
        width=640,
        height=480,
        pixel_format="RG10"
    ):
        self.width = width
        self.height = height
        self.pixel_format = pixel_format

        formatos_suportados = {
            "RG10": 16,
            "BGR8": 24
        }

        if pixel_format not in formatos_suportados:
            raise ValueError(
                f"Formato de pixel não suportado: {pixel_format}. "
            )
        storage_bits = formatos_suportados[pixel_format]

        self.frames_aceitos_appsrc = 0
        self.bytes_aceitos_appsrc = 0

        self.socket_path = socket_path

        if os.path.lexists(socket_path):
            raise RuntimeError(
                f"O socket SHM já existe: {socket_path}. "
                "Verifique se há outro P4 ativo ou um socket antigo."
            )

        pipeline_description = (
            "appsrc name=source is-live=true "
            "format=time do-timestamp=true block=true "
            "caps=application/x-ods-frame,version=1,"
            f"width={width},height={height},"
            f"storage-bits={storage_bits},framerate=0/1 "
            f"! shmsink socket-path={socket_path} "
            "shm-size=33554432 "
            "wait-for-connection=false sync=false"
        )

        self.pipeline = Gst.parse_launch(pipeline_description)
        self.source = self.pipeline.get_by_name("source")

        result = self.pipeline.set_state(Gst.State.PLAYING)

        if result == Gst.StateChangeReturn.FAILURE:
            self.release()
            raise RuntimeError("Falha ao iniciar o SHM Publisher.")

    def publish(self, frame: Frame, metadata: FrameMetadata) -> None:
        if frame.frame_index != metadata.frame_index:
            raise ValueError(
                "O índice do frame não corresponde aos metadados."
            )

        if frame.pixel_format != self.pixel_format:
            raise ValueError(
                f"O publicador espera quadros {self.pixel_format} e recebeu {frame.pixel_format}."
            )

        if (frame.width, frame.height) != (self.width, self.height):
            raise ValueError(
                "Resolução diferente da configurada."
            )

        # Cria o cabeçalho com a identificação do frame.
        cabecalho = criar_cabecalho(metadata, len(frame.data))

        # Adiciona os bytes RAW originais após o cabeçalho.
        pacote = cabecalho + frame.data

        # Cria um buffer GStreamer com o pacote completo.
        buffer = Gst.Buffer.new_allocate(
            None, len(pacote), None
        )

        buffer.fill(0, pacote)

        # Envia o pacote ao appsrc.
        result = self.source.emit("push-buffer", buffer)

        if result != Gst.FlowReturn.OK:
            raise RuntimeError(
                f"Falha ao enviar quadro: {result}"
            )

        self.frames_aceitos_appsrc += 1
        self.bytes_aceitos_appsrc += len(pacote)

    def resumo(self):
        return {
            "frames_aceitos_appsrc": self.frames_aceitos_appsrc,
            "bytes_aceitos_appsrc": self.bytes_aceitos_appsrc
        }

    def release(self) -> None:
        self.pipeline.set_state(Gst.State.NULL)
