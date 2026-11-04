import os
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from .frame import Frame

Gst.init(None)


class SHMPublisher:
    def __init__(
        self,
        socket_path="/tmp/p4_video_shm",
        width=640,
        height=480
    ):
        self.width = width
        self.height = height

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
            f"caps=image/jpeg,width={width},height={height},"
            "framerate=0/1 "
            "! jpegdec "
            "! videoconvert "
            f"! video/x-raw,format=BGR,width={width},height={height} "
            f"! shmsink socket-path={socket_path} "
            "shm-size=8000000 "
            "wait-for-connection=false sync=false"
        )

        self.pipeline = Gst.parse_launch(pipeline_description)
        self.source = self.pipeline.get_by_name("source")

        result = self.pipeline.set_state(Gst.State.PLAYING)

        if result == Gst.StateChangeReturn.FAILURE:
            self.release()
            raise RuntimeError("Falha ao iniciar o SHM Publisher.")

    def publish(self, frame: Frame) -> None:
        if frame.pixel_format != "MJPG":
            raise ValueError("O publicador espera quadros MJPEG.")

        if (frame.width, frame.height) != (self.width, self.height):
            raise ValueError("Resolução diferente da configurada.")

        buffer = Gst.Buffer.new_allocate(
            None, len(frame.data), None
        )

        buffer.fill(0, frame.data)

        result = self.source.emit("push-buffer", buffer)

        if result != Gst.FlowReturn.OK:
            raise RuntimeError(
                f"Falha ao enviar quadro: {result}"
            )
        
        self.frames_aceitos_appsrc += 1
        self.bytes_aceitos_appsrc += len(frame.data)

    def resumo(self):
         return {
            "frames_aceitos_appsrc": self.frames_aceitos_appsrc,
            "bytes_aceitos_appsrc": self.bytes_aceitos_appsrc
        }

    def release(self) -> None:
        self.pipeline.set_state(Gst.State.NULL)