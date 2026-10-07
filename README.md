# SIS-2 — P4: Fonte de Vídeo

Componente responsável pela captura, processamento e fornecimento de frames de vídeo para o projeto de ODS.

O P4 tem como objetivo levar o quadro da câmera até o software de forma confiável, mantendo informações de identificação e temporização do frame e permitindo a aplicação de correção de distorção da lente.

## Fluxo

Câmera → Captura → Frame → Timestamp → Desdistorção → Frame + Metadados

## Sprint 1

Nesta etapa, o desenvolvimento está focado na implementação e validação da lógica de software antes da integração com a plataforma final.

### Requisitos do P4

* Wrapper de captura de vídeo;
* Extração do timestamp diretamente do kernel através da interface V4L2;
* Representação dos frames com imagem, timestamp e identificador;
* Leitura da configuração de calibração em JSON;
* Desdistorção das imagens utilizando OpenCV;
* Coleta de imagens para calibração;
* Testes de memória;
* Testes relacionados a frame drops.

## Estado atual

### Implementado e validado

* Captura de frames de webcam USB (para testes) através de V4L2;
* Uso de buffers MMAP do V4L2;
* Decodificação de frames MJPEG;
* Extração de timestamp fornecido pelo kernel;
* Identificação sequencial dos frames;
* Estrutura `Frame` contendo imagem, timestamp e frame ID;
* Leitura da matriz da câmera e coeficientes de distorção através de JSON;
* Aplicação de `cv2.undistort()` em tempo real;
* Coleta básica de imagens para posterior montagem de um dataset de calibração;
* Teste de 1000 frames sem crescimento contínuo de memória observado;
* Teste de sequência de frames e intervalos de timestamp.

### Resultados dos testes atuais

* Captura validada em webcam USB EMEET SmartCam C60E 4K;
* Timestamp do kernel validado através de V4L2;
* Frame IDs sequenciais de `0` a `99` no teste de 100 frames;
* FPS observado de aproximadamente 15 FPS no ambiente WSL durante o teste de frame drops;
* Nenhum salto de `frame ID` observado nesse teste;
* Uso de memória sem crescimento contínuo observado durante 1000 frames;
* 10 imagens capturadas no teste de coleta para calibração.

> **Observação:** os parâmetros presentes em `config/camera_calibration.json` são valores de teste e ainda não representam a calibração real da câmera.

### Em desenvolvimento

* Dataset real para calibração da câmera;
* Substituição dos parâmetros de calibração de teste pelos parâmetros reais;
* Tratamento mais completo de frame drops;
* Envio dos frames e metadados para os demais componentes do ODS;
* Integração com Raspberry Pi e câmera IMX519;
* Integração final com Jetson;
* Pipeline otimizado utilizando GStreamer/ISP quando necessário.

## Estrutura

```text
P4/
├── config/
│   └── camera_calibration.json
├── src/
│   ├── capture.py
│   ├── frame.py
│   ├── main.py
│   ├── metadata.py
│   ├── undistort.py
│   └── v4l2_capture.py
├── tests/
│   ├── coletar_calibracao.py
│   ├── teste_frame_drops.py
│   ├── teste_memoria.py
│   ├── teste_undistort.py
│   └── teste_v4l2_timestamp.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Ambiente atual de desenvolvimento

Os testes atuais foram realizados em:

* Windows + WSL2;
* Ubuntu;
* Python 3;
* Webcam USB EMEET SmartCam C60E 4K;
* Interface V4L2;
* OpenCV;
* NumPy;
* psutil.

A câmera é disponibilizada ao WSL através do `usbipd`.

## Instalação

Crie e ative um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Para utilizar a câmera através do WSL, ela deve estar conectada ao ambiente Linux e disponível como um dispositivo `/dev/video*`.

Verifique os dispositivos disponíveis:

```bash
v4l2-ctl --list-devices
```

## Executando a captura

Com a câmera disponível em `/dev/video0`:

```bash
python -m src.main
```

O programa captura um frame, aplica o processamento de desdistorção configurado e exibe as informações do frame e dos metadados no terminal.

## Testes

Os testes são executados a partir da raiz do projeto.

### Teste de desdistorção

```bash
PYTHONPATH=. python tests/teste_undistort.py
```

Verifica a leitura da configuração JSON e a aplicação do processamento de desdistorção.

### Teste de timestamp e frame ID

```bash
PYTHONPATH=. python tests/teste_v4l2_timestamp.py
```

Valida a obtenção das informações de temporização através da interface V4L2.

### Teste de frame drops

```bash
PYTHONPATH=. python tests/teste_frame_drops.py
```

Analisa a sequência dos frame IDs e os intervalos entre timestamps.

### Teste de memória

```bash
PYTHONPATH=. python tests/teste_memoria.py
```

Executa uma captura prolongada e acompanha o uso de memória do processo.

### Coleta de imagens para calibração

```bash
PYTHONPATH=. python tests/coletar_calibracao.py
```

Realiza uma coleta básica de imagens da câmera, que poderá ser utilizada posteriormente na montagem de um dataset adequado para calibração.

## Calibração

O arquivo:

```text
config/camera_calibration.json
```

contém atualmente valores de teste utilizados para validar a estrutura do módulo de desdistorção.

Esses valores **não representam a calibração real da câmera**.

Após a coleta de um dataset adequado, os parâmetros reais da câmera deverão substituir os valores de teste.

## Hardware futuro

A implementação está sendo desenvolvida de forma modular para permitir a utilização de diferentes fontes de vídeo.

Durante o desenvolvimento, a captura é validada com webcam USB no PC.

Posteriormente, o componente será adaptado e validado com:

* Raspberry Pi 4 + Arducam IMX519;
* Jetson + câmeras utilizadas pela plataforma final.

A lógica comum de processamento deverá permanecer independente da fonte de captura sempre que possível.

## Objetivo final

O P4 deverá fornecer aos demais componentes do projeto:

* frame de vídeo;
* timestamp confiável;
* identificador do frame;
* resolução;
* FPS;
* informações de processamento;
* demais metadados necessários à integração do sistema.
