import os
import psutil

from src.v4l2_capture import V4L2Capture


process = psutil.Process(os.getpid())

memoria_inicial = process.memory_info().rss

camera = V4L2Capture()

try:
    for i in range(1000):
        frame = camera.read()

        if (i + 1) % 100 == 0:
            memoria_atual = process.memory_info().rss

            memoria_inicial_mb = memoria_inicial / (1024 * 1024)
            memoria_atual_mb = memoria_atual / (1024 * 1024)

            print(
                f"Frame {i + 1}: "
                f"memória = {memoria_atual_mb:.2f} MB "
                f"| variação = "
                f"{memoria_atual_mb - memoria_inicial_mb:+.2f} MB"
            )

finally:
    camera.release()