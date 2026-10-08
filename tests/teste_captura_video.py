from src.capture import WebcamCapture


camera = WebcamCapture()

frames = []

for _ in range(100):
    frame = camera.read()
    frames.append(frame)

camera.release()


frame_ids = [frame.frame_id for frame in frames]
timestamps = [frame.timestamp_ns for frame in frames]

intervalos = [
    timestamps[i] - timestamps[i - 1]
    for i in range(1, len(timestamps))
]

saltos = [
    frame_ids[i] - frame_ids[i - 1]
    for i in range(1, len(frame_ids))
    if frame_ids[i] - frame_ids[i - 1] != 1
]

tempo_total_ns = timestamps[-1] - timestamps[0]
fps_observado = (len(frames) - 1) / (tempo_total_ns / 1_000_000_000)


print("=== TESTE DE CAPTURA DE VÍDEO ===")
print("Frames capturados:", len(frames))
print("Primeiro frame ID:", frame_ids[0])
print("Último frame ID:", frame_ids[-1])

print()
print("=== TIMESTAMP ===")
print("Intervalo mínimo:", min(intervalos), "ns")
print("Intervalo máximo:", max(intervalos), "ns")
print("Intervalo médio:", sum(intervalos) / len(intervalos), "ns")

print()
print("=== FRAME DROP ===")
print("Saltos de sequência:", len(saltos))

print()
print("=== FPS ===")
print("Tempo total:", tempo_total_ns / 1_000_000_000, "s")
print("FPS observado:", fps_observado)