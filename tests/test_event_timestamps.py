import unittest

from src.metadata import FrameMetadata
from src.events import montar_evento_frame


class TestEventTimestamps(unittest.TestCase):

    def test_timestamp_normalizado(self):
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

        evento = montar_evento_frame(metadata)
        payload = evento["payload"]

        self.assertEqual(
            payload["timestamp"],
            50_000_000_000
        )

        self.assertEqual(
            payload["timestamp_monotonic_raw_ns"],
            7_791_844_688
        )

        self.assertEqual(
            payload["timestamp_monotonic_raw_clock"],
            "CLOCK_MONOTONIC_RAW"
        )

        # Verifica compatibilidade sem timestamp normalizado
        metadata.captured_at_monotonic_raw_ns = None

        evento = montar_evento_frame(metadata)

        self.assertNotIn(
            "timestamp_monotonic_raw_ns",
            evento["payload"]
        )


if __name__ == "__main__":
    unittest.main()