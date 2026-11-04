
import unittest
from types import SimpleNamespace

from src.metadata import FrameMetadata
from src.shm_protocol import criar_cabecalho, ler_cabecalho


class TestSHMProtocol(unittest.TestCase):

    def test_pacote_valido(self):
        metadata = FrameMetadata(
            source_id="imx519",
            session_id="sessao-teste",
            frame_index=125,
            width=1920,
            height=1080,
            pixel_format="RG10",
            fps=60.0,
            raw=True,
            captured_at_ns=123456789,
            received_at_ns=None
        )

        dados_raw = b"\x01\x02\x03\x04"
        pacote = criar_cabecalho(metadata, len(dados_raw)) + dados_raw

        campos, inicio_raw = ler_cabecalho(pacote)

        self.assertEqual(campos["source_id"], metadata.source_id)
        self.assertEqual(campos["session_id"], metadata.session_id)
        self.assertEqual(campos["frame_id"], metadata.frame_index)
        self.assertEqual(campos["data_size"], len(dados_raw))
        self.assertEqual(pacote[inicio_raw:], dados_raw)

    def test_pacote_incompleto(self):
        metadata = SimpleNamespace(
            source_id="imx519",
            session_id="sessao-teste",
            frame_index=125,
            captured_at_ns=123456789,
            width=1920,
            height=1080,
            pixel_format="RG10",
            raw=True
        )

        pacote = criar_cabecalho(metadata, 4) + b"\x01\x02"

        with self.assertRaises(ValueError):
            ler_cabecalho(pacote)


if __name__ == "__main__":
    unittest.main()
