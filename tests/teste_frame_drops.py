from src.v4l2_capture import V4L2Capture


camera = V4L2Capture()

timestamps = []
frame_ids = []
frames_capturados = 0

try:
    for _ in range(100):
        frame = camera.read()

        timestamps.append(frame.timestamp_ns)
        frame_ids.append(frame.frame_id)
        frames_capturados += 1

finally:
    camera.release()


print("Total de frames capturados:", frames_capturados)
print("Primeiro frame ID:", frame_ids[0])
print("Último frame ID:", frame_ids[-1])

intervalos = []

for i in range(1, len(timestamps)):
    intervalo = timestamps[i] - timestamps[i - 1]
    intervalos.append(intervalo)

intervalos_32ms = 0
intervalos_64ms = 0

for intervalo in intervalos:
    intervalo_ms = intervalo / 1_000_000

    if 25 <= intervalo_ms <= 45:
        intervalos_32ms += 1

    elif 55 <= intervalo_ms <= 75:
        intervalos_64ms += 1

print("Quantidade de intervalos:", len(intervalos))
print("Intervalos próximos de 32 ms:", intervalos_32ms)
print("Intervalos próximos de 64 ms:", intervalos_64ms)

tempo_total = timestamps[-1] - timestamps[0]

fps_observado = (frames_capturados - 1) / (
    tempo_total / 1_000_000_000
)

print("Tempo total:", tempo_total / 1_000_000_000, "segundos")
print("FPS observado:", fps_observado)