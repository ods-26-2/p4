
import gi
import cv2
import numpy as np

gi.require_version("Gst", "1.0")
gi.require_version("GstVideo", "1.0")

from gi.repository import Gst, GstVideo

Gst.init(None)


def main():
    pipeline_description = (
        "shmsrc socket-path=/tmp/p4_video_shm "
        "is-live=true do-timestamp=true "
        "! video/x-raw,format=BGR,width=640,height=480 "
        "! appsink name=sink sync=false "
        "max-buffers=1 drop=true"
    )

    pipeline = Gst.parse_launch(pipeline_description)
    sink = pipeline.get_by_name("sink")

    result = pipeline.set_state(Gst.State.PLAYING)

    if result == Gst.StateChangeReturn.FAILURE:
        raise RuntimeError("Falha ao conectar ao P4.")

    try:
        for i in range(30):
            sample = sink.emit(
                "try-pull-sample",
                5 * Gst.SECOND
            )

            if sample is None:
                raise RuntimeError(
                    "Nenhum quadro recebido do P4."
                )

            buffer = sample.get_buffer()

            info = GstVideo.VideoInfo.new_from_caps(sample.get_caps())
            if info is None:
                raise RuntimeError("Formato inválido.")

            success, mapped = buffer.map(Gst.MapFlags.READ)

            if not success:
                raise RuntimeError("Falha ao ler quadro.")

            try:
                image = np.ndarray(
                    shape=(info.height, info.width, 3),
                    dtype=np.uint8,
                    buffer=mapped.data,
                    strides=(info.stride[0], 3, 1)
                ).copy()
            finally:
                buffer.unmap(mapped)

            if i == 0:
                if not cv2.imwrite("i1_frame.jpg", image):
                    raise RuntimeError("Falha ao salvar imagem.")

            if i % 10 == 0:
                print(
                    f"I1 recebeu quadro {i}: "
                    f"{info.width}x{info.height}"
                )

        print("Recepção de vídeo funcionando!")

    finally:
        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
