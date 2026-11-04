
from .frame import Frame


class CaptureMetrics:
    def __init__(self):
        self.frames_recebidos = 0
        self.frames_perdidos_estimados = 0
        self.ultimo_frame_id = None

        self.primeiro_timestamp_ns = None
        self.ultimo_timestamp_ns = None
        self.frames_com_timestamp = 0

    def atualizar(self, frame: Frame):
        self.frames_recebidos += 1

        # Verifica saltos na sequência de quadros
        if self.ultimo_frame_id is not None:
            diferenca = frame.frame_index - self.ultimo_frame_id

            if diferenca > 1:
                self.frames_perdidos_estimados += diferenca - 1

        self.ultimo_frame_id = frame.frame_index

        # Utiliza timestamps monotônicos fornecidos pelo driver
        if (
            frame.timestamp_origin.startswith("driver_")
            and frame.timestamp_ns > 0
        ):
            if self.primeiro_timestamp_ns is None:
                self.primeiro_timestamp_ns = frame.timestamp_ns
                self.ultimo_timestamp_ns = frame.timestamp_ns
                self.frames_com_timestamp = 1

            elif frame.timestamp_ns > self.ultimo_timestamp_ns:
                self.ultimo_timestamp_ns = frame.timestamp_ns
                self.frames_com_timestamp += 1

    def resumo(self):
        fps_medio = None

        if self.frames_com_timestamp >= 2:
            duracao_ns = (
                self.ultimo_timestamp_ns
                - self.primeiro_timestamp_ns
            )

            duracao_s = duracao_ns / 1_000_000_000

            if duracao_s > 0:
                fps_medio = round(
                    (self.frames_com_timestamp - 1) / duracao_s,
                    2
                )

        return {
            "frames_recebidos": self.frames_recebidos,
            "frames_perdidos_estimados": self.frames_perdidos_estimados,
            "fps_medio": fps_medio
        }
