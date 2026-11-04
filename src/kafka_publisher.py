
import json

from confluent_kafka import Producer


class KafkaPublisher:
    def __init__(self, bootstrap_servers: str):
        # Conecta o cliente ao broker Kafka
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers
        })

    def confirmar_entrega(self, erro, mensagem):
        # Chamado quando o Kafka confirma ou rejeita
        # a entrega de uma mensagem
        if erro is not None:
            print(f"Erro ao publicar no Kafka: {erro}")

    def publicar(self, topico: str, evento: dict):
        # Converte o dicionário Python para JSON
        mensagem = json.dumps(evento).encode("utf-8")

        # Coloca a mensagem na fila de envio
        self.producer.produce(
            topic=topico,
            key=evento["session_id"],
            value=mensagem,
            on_delivery=self.confirmar_entrega
        )

        # Processa confirmações e possíveis erros
        self.producer.poll(0)

    def publicar_inicio_sessao(self, evento: dict):
        self.publicar("ods.session.started", evento)

    def publicar_frame(self, evento: dict):
        self.publicar("ods.p4.frame", evento)

    def release(self):
        # Aguarda até 5 segundos pelas mensagens pendentes
        pendentes = self.producer.flush(5)

        if pendentes > 0:
            print(
                f"Aviso: {pendentes} mensagem(ns) "
                "não confirmada(s) pelo Kafka."
            )
