import unittest

from src.metadata import FrameMetadata
from src.shm_protocol import criar_cabecalho, ler_cabecalho


class TestSHMTimestamps(unittest.TestCase):

    def test_timestamp_normalizado_no_cabecalho(self):
        metadata = FrameMetadata(
            source_id="imx477",
            session_id="sessao-teste",
            frame_index=10,
            width=1920,
            height=1080,
            pixel_format="RG10",
            fps=60.0,
            raw=True,
            captured_at_ns=50_000_000_000,
            received_at_ns=8_000_000_000,
            captured_at_monotonic_raw_ns=7_791_844_688,
            received_at_monotonic_raw_ns=7_800_000_000
        )

        dados_raw = b"\x01\x02\x03\x04"

        pacote = (
            criar_cabecalho(metadata, len(dados_raw))
            + dados_raw
        )

        campos, inicio_raw = ler_cabecalho(pacote)

        # Timestamp original preservado
        self.assertEqual(
            campos["timestamp"],
            50_000_000_000
        )

        # Timestamp normalizado disponível
        self.assertEqual(
            campos["timestamp_monotonic_raw_ns"],
            7_791_844_688
        )

        self.assertEqual(
            campos["timestamp_monotonic_raw_clock"],
            "CLOCK_MONOTONIC_RAW"
        )

        # Bytes RAW preservados
        self.assertEqual(
            pacote[inicio_raw:],
            dados_raw
        )


if __name__ == "__main__":
    unittest.main()