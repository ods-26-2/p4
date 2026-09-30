# Squad SIS-2 - Componente P4 (Fonte de Vídeo)

Módulo de captura de vídeo V4L2/GStreamer com timestamp monotônico do kernel,
desdistorção em tempo real e exportação de metadados JSON para o projeto ODS (2026/2).

## Como executar no Raspberry Pi 4
1. Instalar dependências do sistema:
   `sudo apt update && sudo apt install -y python3-opencv python3-gst-1.0 python3-gi`
2. Executar a coleta de calibração:
   `python3 collect_calibration.py`
3. Executar o pipeline principal:
   `python3 main.py`