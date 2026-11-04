
import unittest

from src.frame import Frame
from src.capture_metrics import CaptureMetrics


class TestCaptureMetrics(unittest.TestCase):

    def test_detecta_saltos_na_sequencia(self):
        metrics = CaptureMetrics()

        indices = [0, 1, 4, 5]

        for indice in indices:
            frame = Frame(
                data=b"imagem_simulada",
                width=640,
                height=480,
                pixel_format="MJPG",
                timestamp_ns=1_000_000_000 + indice * 64_000_000,
                frame_index=indice,
                timestamp_origin="driver_soe"
            )

            metrics.atualizar(frame)

        resumo = metrics.resumo()

        self.assertEqual(resumo["frames_recebidos"], 4)
        self.assertEqual(resumo["frames_perdidos_estimados"], 2)


if __name__ == "__main__":
    unittest.main()
