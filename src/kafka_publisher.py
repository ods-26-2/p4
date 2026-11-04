
import json

from confluent_kafka import Producer, KafkaException


class KafkaPublisher:
    def __init__(self, bootstrap_servers: str):
        self.enfileiradas = 0
        self.confirmadas = 0
        self.falhas_entrega = 0
        self.falhas_envio = 0

        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,

            # Limita o tempo aguardando a entrega
            "message.timeout.ms": 10000,

            # Evita crescimento ilimitado da fila
            "queue.buffering.max.messages": 500,

            # Habilita proteção contra duplicações
            # causadas por tentativas de envio do produtor
            "enable.idempotence": True
        })

    def confirmar_entrega(self, erro, mensagem):
        if erro is None:
            self.confirmadas += 1
        else:
            self.falhas_entrega += 1

            if self.falhas_entrega == 1 or self.falhas_entrega % 30 == 0:
                print(f"Kafka: falha na entrega: {erro}")

    def publicar(self, topico: str, evento: dict) -> bool:
        # Processa confirmações pendentes sem bloquear
        self.producer.poll(0)

        mensagem = json.dumps(evento).encode("utf-8")

        # Mantém a identificação da fonte e da sessão
        chave = (
            f"{evento['source_id']}:"
            f"{evento['session_id']}"
        )

        try:
            self.producer.produce(
                topic=topico,
                key=chave,
                value=mensagem,
                on_delivery=self.confirmar_entrega
            )

        except (BufferError, KafkaException) as erro:
            self.falhas_envio += 1

            if self.falhas_envio == 1 or self.falhas_envio % 30 == 0:
                print(f"Kafka: falha ao enfileirar: {erro}")

            return False

        self.enfileiradas += 1
        return True

    def publicar_inicio_sessao(self, evento: dict) -> bool:
        return self.publicar("ods.session.started", evento)

    def publicar_frame(self, evento: dict) -> bool:
        return self.publicar("ods.p4.frame", evento)

    def release(self):
        try:
            pendentes = self.producer.flush(2)

        except KeyboardInterrupt:
            print("\nKafka: encerramento interrompido.")
            pendentes = len(self.producer)

        print(
            "Kafka | "
            f"Enfileiradas: {self.enfileiradas} | "
            f"Confirmadas: {self.confirmadas} | "
            f"Falhas de entrega: {self.falhas_entrega} | "
            f"Falhas de envio: {self.falhas_envio} | "
            f"Pendentes: {pendentes}"
        )