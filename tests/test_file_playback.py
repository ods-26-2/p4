
import unittest

from src.frame import Frame
from src.p4 import P4
from src.events import montar_evento_frame
from src.shm_protocol import criar_cabecalho, ler_cabecalho


class FonteMP4Simulada:
    def read(self):
        return Frame(
            data=b"\x00\x01\x02\x03\x04\x05",
            width=2,
            height=1,
            pixel_format="BGR8",
            timestamp_ns=123456789,
            frame_index=0,
            timestamp_origin="file_playback_raw"
        )

    def release(self):
        pass


class TestFilePlayback(unittest.TestCase):

    def test_timestamps_mp4_evento_e_shm(self):
        fonte = FonteMP4Simulada()

        p4 = P4(
            source=fonte,
            source_id="file_teste",
            fps=60.0,
            raw=False
        )

        try:
            frame, metadata = p4.read()

            # Arquivo MP4 não possui timestamp de captura física.
            self.assertIsNone(metadata.captured_at_ns)

            # O instante de reprodução deve ser preservado.
            self.assertEqual(
                metadata.received_at_monotonic_raw_ns,
                frame.timestamp_ns
            )

            # Valida o evento Kafka.
            evento = montar_evento_frame(metadata)
            payload = evento["payload"]

            self.assertIsNone(payload["timestamp"])

            self.assertEqual(
                payload["received_at_monotonic_raw_ns"],
                123456789
            )

            self.assertFalse(payload["raw"])

            # Valida o cabeçalho SHM.
            pacote = (
                criar_cabecalho(metadata, len(frame.data))
                + frame.data
            )

            cabecalho, inicio = ler_cabecalho(pacote)

            self.assertIsNone(cabecalho["timestamp"])

            self.assertEqual(
                cabecalho["received_at_monotonic_raw_ns"],
                123456789
            )

            self.assertEqual(cabecalho["format"], "BGR8")
            self.assertFalse(cabecalho["raw"])
            self.assertEqual(pacote[inicio:], frame.data)

        finally:
            p4.release()


if __name__ == "__main__":
    unittest.main()
