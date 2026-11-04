
import hashlib
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)


def main():
    pipeline_description = (
        "shmsrc socket-path=/tmp/p4_raw_teste_shm "
        "is-live=true do-timestamp=true "
        "! application/x-ods-raw,format=RG10,"
        "width=1920,height=1080,storage-bits=16,framerate=0/1 "
        "! appsink name=sink sync=false "
        "max-buffers=1 drop=true"
    )

    pipeline = Gst.parse_launch(pipeline_description)
    sink = pipeline.get_by_name("sink")

    try:
        resultado = pipeline.set_state(Gst.State.PLAYING)

        if resultado == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError("Falha ao iniciar leitor SHM.")

        sample = sink.emit("try-pull-sample", 5 * Gst.SECOND)

        if sample is None:
            raise RuntimeError("Nenhum quadro recebido.")

        buffer = sample.get_buffer()
        sucesso, mapped = buffer.map(Gst.MapFlags.READ)

        if not sucesso:
            raise RuntimeError("Falha ao acessar os bytes.")

        try:
            dados = bytes(mapped.data)
        finally:
            buffer.unmap(mapped)

        print("Bytes recebidos:", len(dados))
        print("SHA-256:", hashlib.sha256(dados).hexdigest())

    finally:
        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
