
import json
import unittest
from unittest.mock import patch

from src.kafka_publisher import KafkaPublisher


class TestKafkaPublisher(unittest.TestCase):

    @patch("src.kafka_publisher.Producer")
    def test_publicar_frame(self, MockProducer):
        evento = {
            "source_id": "imx519",
            "session_id": "sessao-teste",
            "payload": {
                "frame_id": 125
            }
        }

        publisher = KafkaPublisher(
            bootstrap_servers="servidor-simulado:9092"
        )

        resultado = publisher.publicar_frame(evento)

        argumentos = (
            MockProducer.return_value.produce.call_args.kwargs
        )

        self.assertTrue(resultado)
        self.assertEqual(argumentos["topic"], "ods.p4.frame")
        self.assertEqual(
            argumentos["key"],
            "imx519:sessao-teste"
        )
        self.assertEqual(
            json.loads(argumentos["value"]),
            evento
        )

        self.assertEqual(publisher.enfileiradas, 1)

    @patch("src.kafka_publisher.Producer")
    def test_confirmacao_entrega(self, MockProducer):
        publisher = KafkaPublisher(
            bootstrap_servers="servidor-simulado:9092"
        )

        evento = {
            "source_id": "imx519",
            "session_id": "sessao-teste",
            "payload": {
                "frame_id": 125
            }
        }

        publisher.publicar_frame(evento)

        argumentos = (
            MockProducer.return_value.produce.call_args.kwargs
        )

        # Recupera a função que receberia a confirmação do Kafka.
        callback = argumentos["on_delivery"]

        # Simula uma entrega confirmada pelo broker.
        callback(None, None)

        self.assertEqual(publisher.enfileiradas, 1)
        self.assertEqual(publisher.confirmadas, 1)
        self.assertEqual(publisher.falhas_entrega, 0)


    @patch("src.kafka_publisher.Producer")
    def test_falha_entrega(self, MockProducer):
        publisher = KafkaPublisher(
            bootstrap_servers="servidor-simulado:9092"
        )

        evento = {
            "source_id": "imx519",
            "session_id": "sessao-teste",
            "payload": {
                "frame_id": 125
            }
        }

        publisher.publicar_frame(evento)

        argumentos = (
            MockProducer.return_value.produce.call_args.kwargs
        )

        callback = argumentos["on_delivery"]

        # Simula uma falha ao entregar a mensagem.
        callback(Exception("Falha simulada"), None)

        self.assertEqual(publisher.enfileiradas, 1)
        self.assertEqual(publisher.confirmadas, 0)
        self.assertEqual(publisher.falhas_entrega, 1)


    @patch("src.kafka_publisher.Producer")
    def test_falha_envio(self, MockProducer):
        publisher = KafkaPublisher(
            bootstrap_servers="servidor-simulado:9092"
        )

        # Simula uma fila Kafka cheia.
        MockProducer.return_value.produce.side_effect = BufferError(
            "Fila cheia"
        )

        evento = {
            "source_id": "imx519",
            "session_id": "sessao-teste",
            "payload": {
                "frame_id": 125
            }
        }

        resultado = publisher.publicar_frame(evento)

        self.assertFalse(resultado)
        self.assertEqual(publisher.enfileiradas, 0)
        self.assertEqual(publisher.confirmadas, 0)
        self.assertEqual(publisher.falhas_envio, 1)



if __name__ == "__main__":
    unittest.main()
