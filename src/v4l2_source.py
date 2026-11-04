
from time import monotonic_ns

from linuxpy.video.device import Device, VideoCapture

from .frame import Frame
from .source import VideoSource


class V4L2Source(VideoSource):
    def __init__(
        self,
        device="/dev/video0",
        width=640,
        height=480,
        pixel_format="MJPG"
    ):
        self.device = Device(device)
        self.capture = None

        try:
            self.device.open()

            self.capture = VideoCapture(self.device)

            # Solicita o formato desejado
            self.capture.set_format(
                width,
                height,
                pixel_format
            )

            # Verifica o formato realmente aceito pelo driver
            formato = self.capture.get_format()
            formato_real = formato.pixel_format.human_str()

            if (
                formato.width != width
                or formato.height != height
                or formato_real != pixel_format
            ):
                raise RuntimeError(
                    "Formato solicitado não foi aceito. "
                    f"Recebido: {formato.width}x{formato.height} "
                    f"{formato_real}"
                )

            self.capture.open()
            self.frames = iter(self.capture)

        except Exception:
            self.release()
            raise

    def read(self) -> Frame:
        camera_frame = next(self.frames)

        flags = int(camera_frame.flags)

        tipo_timestamp = flags & 0xE000
        origem_timestamp = flags & 0x70000

        if tipo_timestamp == 0x2000:
            # Timestamp monotônico fornecido pelo driver
            timestamp = camera_frame.buff.timestamp

            timestamp_ns = (
                int(timestamp.secs) * 1_000_000_000
                + int(timestamp.usecs) * 1_000
            )

            if origem_timestamp == 0x10000:
                timestamp_origin = "driver_soe"

            elif origem_timestamp == 0x00000:
                timestamp_origin = "driver_eof"

            else:
                timestamp_origin = "driver_monotonic"

        else:
            # Origem do relógio não confirmada:
            # utiliza o momento de recebimento
            timestamp_ns = monotonic_ns()
            timestamp_origin = "received"

        return Frame(
            data=bytes(camera_frame),
            width=camera_frame.width,
            height=camera_frame.height,
            pixel_format=camera_frame.pixel_format.human_str(),
            timestamp_ns=timestamp_ns,
            frame_index=camera_frame.frame_nb,
            timestamp_origin=timestamp_origin
        )

    def release(self) -> None:
        try:
            if self.capture is not None:
                self.capture.close()
        finally:
            self.device.close()
