import unittest
from unittest.mock import patch

from src.tsc_converter import TSCClockConverter


class TestTSCClockConverter(unittest.TestCase):

    @patch("src.tsc_converter.ctypes.CDLL")
    def test_conversao_timestamp(self, mock_cdll):
        mock_funcao = (
            mock_cdll.return_value.p4_tsc_raw_offset_ns
        )

        mock_funcao.return_value = 42_208_155_312

        converter = TSCClockConverter(
            "/tmp/libp4_tsc_clock.so"
        )

        timestamp_original = 50_000_000_000

        resultado = converter.to_monotonic_raw_ns(
            timestamp_original
        )

        self.assertEqual(resultado, 7_791_844_688)
        self.assertEqual(
            converter.offset_ns,
            42_208_155_312
        )

    @patch("src.tsc_converter.ctypes.CDLL")
    def test_falha_medicao_offset(self, mock_cdll):
        mock_funcao = (
            mock_cdll.return_value.p4_tsc_raw_offset_ns
        )

        mock_funcao.return_value = -1

        with self.assertRaises(RuntimeError):
            TSCClockConverter(
                "/tmp/libp4_tsc_clock.so"
            )


if __name__ == "__main__":
    unittest.main()