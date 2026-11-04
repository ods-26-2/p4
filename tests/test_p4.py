
import unittest

from src.p4 import P4
from src.frame import Frame


class CameraComFalha:
    def read(self):
        raise RuntimeError("Câmera não entregou quadro")

    def release(self):
        pass

class CameraFuncionando:
    def __init__(self):
        self.indice = 0

    def read(self):
        frame = Frame(
            data=b"imagem_simulada",
            width=640,
            height=480,
            pixel_format="MJPG",
            timestamp_ns=1_000_000_000 + self.indice * 64_000_000,
            frame_index=self.indice,
            timestamp_origin="driver_soe"
        )

        self.indice += 1
        return frame

    def release(self):
        pass


class TestP4(unittest.TestCase):

    def test_nao_inicia_sessao_sem_frame(self):
        eventos = []

        p4 = P4(
            source=CameraComFalha(),
            source_id="camera_teste"
        )

        with self.assertRaises(RuntimeError):
            p4.run(
                consumer=lambda frame, metadata: None,
                on_session_started=eventos.append
            )

        self.assertEqual(len(eventos), 0)

    def test_inicia_sessao_uma_vez_antes_do_frame(self):
        ordem = []

        p4 = P4(
            source=CameraFuncionando(),
            source_id="camera_teste"
        )

        p4.run(
            consumer=lambda frame, metadata: ordem.append(
                ("frame", frame.frame_index)
            ),
            frame_limit=2,
            on_session_started=lambda evento: ordem.append(
                ("sessao", evento["session_id"])
            )
        )

        self.assertEqual(
            ordem,
            [
                ("sessao", p4.session_id),
                ("frame", 0),
                ("frame", 1)
            ]
        )



    def test_timestamps_e_fps(self):
        metadados = []
    
        p4 = P4(
            source=CameraFuncionando(),
            source_id="camera_teste"
        )
    
        p4.run(
            consumer=lambda frame, metadata: metadados.append(metadata),
            frame_limit=3
        )
    
        # Verifica os timestamps capturados
        self.assertEqual(
            metadados[0].captured_at_ns,
            1_000_000_000
        )
    
        self.assertEqual(
            metadados[1].captured_at_ns,
            1_064_000_000
        )
    
        # Primeiro quadro ainda não possui FPS calculado
        self.assertIsNone(metadados[0].fps)
    
        # Segundo quadro permite calcular o FPS
        self.assertAlmostEqual(
            metadados[1].fps,
            15.625,
            places=1
        )
    
        # Verifica as métricas de captura
        resumo = p4.metrics.resumo()
    
        self.assertEqual(resumo["frames_recebidos"], 3)
    
        self.assertAlmostEqual(
            resumo["fps_medio"],
            15.625,
            places=1
        )



if __name__ == "__main__":
    unittest.main()
