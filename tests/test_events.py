
import unittest

from src.metadata import FrameMetadata
from src.events import montar_evento_frame, montar_evento_inicio_sessao


class TestEvents(unittest.TestCase):

    def test_evento_frame(self):
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

        evento = montar_evento_frame(metadata)

        campos_obrigatorios = [
            "message_id",
            "message_type",
            "schema",
            "schema_version",
            "producer",
            "occurred_at",
            "payload"
        ]

        for campo in campos_obrigatorios:
            self.assertIn(campo, evento)

        self.assertEqual(evento["schema"], "ods.p4.frame")
        self.assertEqual(evento["schema_version"], "1.0")
        self.assertEqual(evento["source_id"], "imx519")
        self.assertEqual(evento["session_id"], "sessao-teste")
        self.assertEqual(evento["payload"]["frame_id"], 125)
        self.assertEqual(evento["payload"]["timestamp"], 123456789)

    def test_evento_inicio_sessao(self):
        evento_original = {
            "event": "ods.session.started",
            "source_id": "imx519",
            "session_id": "sessao-teste"
        }

        evento = montar_evento_inicio_sessao(evento_original)

        campos_obrigatorios = [
            "message_id",
            "message_type",
            "schema",
            "schema_version",
            "producer",
            "occurred_at",
            "payload"
        ]

        for campo in campos_obrigatorios:
            self.assertIn(campo, evento)

        self.assertEqual(evento["schema"], "ods.session.started")
        self.assertEqual(evento["schema_version"], "1.0")
        self.assertEqual(evento["source_id"], "imx519")
        self.assertEqual(evento["session_id"], "sessao-teste")
        self.assertEqual(
            evento["payload"]["session_id"],
            "sessao-teste"
        )


if __name__ == "__main__":
    unittest.main()
