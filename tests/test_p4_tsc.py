import unittest
from unittest.mock import Mock, patch
from time import CLOCK_MONOTONIC_RAW

from src.p4 import P4
from src.frame import Frame


class TestP4TSC(unittest.TestCase):

    @patch("src.p4.clock_gettime_ns")
    @patch("src.p4.monotonic_ns")
    def test_timestamps_convertidos(
        self,
        mock_monotonic,
        mock_clock_raw
    ):
        # Simula o timestamp original de uma câmera CSI
        timestamp_driver = 50_000_000_000
        offset = 42_208_155_312

        frame = Frame(
            data=b"\x00\x00",
            width=1920,
            height=1080,
            pixel_format="RG10",
            timestamp_ns=timestamp_driver,
            frame_index=0,
            timestamp_origin="driver_eof"
        )

        source = Mock()
        source.read.return_value = frame

        converter = Mock()
        converter.to_monotonic_raw_ns.side_effect = (
            lambda timestamp: timestamp - offset
        )

        mock_monotonic.return_value = 8_000_000_000
        mock_clock_raw.return_value = 7_800_000_000

        p4 = P4(
            source=source,
            source_id="imx477",
            fps=60,
            raw=True,
            tsc_converter=converter
        )

        _, metadata = p4.read()

        # Timestamp original preservado
        self.assertEqual(
            metadata.captured_at_ns,
            timestamp_driver
        )

        self.assertEqual(
            metadata.received_at_ns,
            8_000_000_000
        )

        # Timestamp convertido
        self.assertEqual(
            metadata.captured_at_monotonic_raw_ns,
            7_791_844_688
        )

        self.assertEqual(
            metadata.received_at_monotonic_raw_ns,
            7_800_000_000
        )

        converter.to_monotonic_raw_ns.assert_called_once_with(
            timestamp_driver
        )

        mock_clock_raw.assert_called_once_with(
            CLOCK_MONOTONIC_RAW
        )


if __name__ == "__main__":
    unittest.main()