# SIS-2 — P4: Fonte de Vídeo

Componente responsável pela captura de vídeo, representação dos frames, geração de metadados temporais e gravação de vídeo para o ecossistema ODS.

O objetivo do P4 é receber imagens de uma câmera e disponibilizá-las ao restante do sistema de forma organizada, com identificadores, informações de temporização e formato consistente. Futuramente, o componente deverá oferecer suporte à correção da distorção da lente e à integração com as câmeras da plataforma embarcada.

## 1. Objetivos e responsabilidades

- Detectar e selecionar câmeras compatíveis com a implementação disponível.
- Capturar frames continuamente.
- Representar cada frame com imagem, identificador sequencial e timestamp.
- Disponibilizar metadados associados à captura.
- Gravar o fluxo capturado em arquivo de vídeo.
- Preparar a arquitetura para a integração com os demais componentes ODS.
- Evoluir para o uso das câmeras e da plataforma embarcada definidas pelo projeto.

## 2. Fluxo atual

O fluxo principal implementado para a webcam USB é:

**Câmera USB → GStreamer/V4L2 → Frame → Timestamp e metadados → Gravação em MP4**

O GStreamer gerencia o pipeline de captura e decodificação. Os frames são representados pela classe `Frame`, enquanto os metadados são organizados pela classe `FrameMetadata`.

O programa principal realiza a captura contínua, registra as informações de cada frame no terminal em formato JSON e encaminha as imagens ao gravador de vídeo.

## 3. Estado atual — Sprint 1

### 3.1. Funcionalidades validadas

Os seguintes comportamentos tiveram sucesso confirmado no ambiente de desenvolvimento atual, utilizando a webcam USB EMEET SmartCam C60E 4K conectada ao WSL2:

- Detecção e seleção da webcam USB.
- Exibição dos modos de resolução e FPS configurados para a câmera.
- Captura contínua utilizando GStreamer.
- Captura configurada para 1280 × 720 a 30 FPS.
- Decodificação de imagens MJPEG e conversão para o formato BGR utilizado pelo OpenCV.
- Representação dos frames com imagem, timestamp e identificador sequencial.
- Emissão de metadados em JSON no terminal durante a captura.
- Geração de arquivo de vídeo MP4.
- Reprodução correta do vídeo gerado.
- Encerramento da captura e liberação dos recursos ao pressionar `Ctrl+C`.

Essas validações correspondem ao ambiente e à configuração testados. Não representam garantia de funcionamento em outros sistemas operacionais, câmeras ou plataformas embarcadas.

### 3.2. Funcionalidades pendentes de validação

- Medição sistemática de perda de frames na implementação principal baseada em GStreamer.
- Avaliação de consumo de memória durante capturas prolongadas.
- Calibração real da câmera e obtenção dos parâmetros de distorção.
- Aplicação e validação da correção de distorção com parâmetros reais.
- Definição da interface de saída dos frames e metadados para os demais componentes ODS.
- Validação da câmera Arducam IMX519 no Raspberry Pi 4.
- Integração e validação das câmeras na plataforma Jetson.
- Verificação das exigências temporais e do significado do timestamp em relação ao instante de exposição do sensor.
- Validação sistemática dos modos de resolução e FPS além da configuração já testada.

## 4. Ambiente de desenvolvimento

### 4.1. Ambiente atualmente utilizado

- Sistema operacional hospedeiro: Windows.
- Ambiente de execução: WSL2 com Ubuntu.
- Linguagem: Python 3.
- Câmera de teste: EMEET SmartCam C60E 4K, conectada por USB.
- Captura principal: GStreamer com fonte V4L2.
- Processamento de imagens: OpenCV e NumPy.
- Gravação de vídeo: OpenCV `VideoWriter`.

A webcam é disponibilizada ao WSL2 por meio do `usbipd` no Windows.

### 4.2. Hardware previsto para integração

- Raspberry Pi 4 com 8 GB de RAM.
- Arducam IMX519 com foco automático por VCM.
- Plataforma Jetson definida pelo projeto para a execução final.

A integração com esses dispositivos permanece pendente de validação. A implementação existente para IMX519 não significa que o pipeline esteja pronto ou testado nesses equipamentos.

## 5. Dependências

É importante distinguir os pacotes Python das bibliotecas e ferramentas instaladas no Ubuntu.

### 5.1. Dependências Python

O arquivo `requirements.txt` contém:

- `numpy`
- `opencv-python`
- `psutil`

O `psutil` é utilizado em ferramentas auxiliares de monitoramento. A lista de dependências deve ser atualizada caso novas bibliotecas passem a ser necessárias.

### 5.2. Dependências do sistema

O fluxo principal depende de componentes do GStreamer e da integração entre Python e GStreamer.

Pacotes utilizados no ambiente atual incluem:

- `python3-gi`
- `gir1.2-gstreamer-1.0`
- `gstreamer1.0-tools`
- `gstreamer1.0-plugins-base`
- `gstreamer1.0-plugins-good`
- `v4l-utils`

O pipeline utiliza os elementos GStreamer `v4l2src`, `jpegdec`, `videoconvert` e `appsink`.

Os pacotes acima correspondem ao ambiente verificado durante o desenvolvimento. Uma instalação nova pode precisar de outros pacotes ou plugins, dependendo da distribuição e da configuração utilizada.

## 6. Instalação do ambiente

Os comandos abaixo são destinados ao Ubuntu no WSL2.

### 6.1. Instalar ferramentas e bibliotecas do sistema

```bash
sudo apt update

sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-gi \
    gir1.2-gstreamer-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    v4l-utils \
    usbutils
```

Esses comandos instalam os pacotes principais documentados para o ambiente atual. Caso algum elemento do pipeline não esteja disponível, pode ser necessário instalar o pacote GStreamer correspondente à distribuição.

### 6.2. Criar e ativar o ambiente virtual

Na pasta do componente P4:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
```

O parâmetro `--system-site-packages` permite que o ambiente virtual acesse pacotes Python disponibilizados pelo sistema, como a integração `gi` instalada pelo Ubuntu.

### 6.3. Instalar as dependências Python

```bash
python -m pip install -r requirements.txt
```

### 6.4. Verificar a instalação do GStreamer

```bash
gst-inspect-1.0 v4l2src
gst-inspect-1.0 jpegdec
gst-inspect-1.0 videoconvert
gst-inspect-1.0 appsink
```

Os quatro comandos devem reconhecer seus respectivos elementos.

Verifique também a integração com Python:

```bash
python -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print(Gst.version_string())"
```

Se o comando imprimir a versão do GStreamer sem apresentar erro, a integração básica está funcionando.

### 6.5. Disponibilizar a webcam ao WSL2

No Windows, o `usbipd` é utilizado para disponibilizar o dispositivo USB ao WSL2. O procedimento de conexão depende do estado atual do dispositivo e da instalação do `usbipd`.

Depois de conectar a câmera, no Ubuntu, verifique:

```bash
lsusb
v4l2-ctl --list-devices
ls /dev/video*
```

Se a câmera não aparecer, verifique a conexão USB, o vínculo do dispositivo com o WSL2 e as permissões de acesso aos dispositivos de vídeo.

A configuração de acesso USB descrita aqui é específica do ambiente Windows/WSL2 e não deve ser aplicada automaticamente ao Raspberry Pi ou à Jetson.

## 7. Como executar

Na pasta raiz do componente P4, com o ambiente virtual ativado:

```bash
python -m src.main
```

O programa apresenta as câmeras reconhecidas pela configuração atual e solicita a seleção da câmera e do modo de captura disponível.

Durante a execução:

- Os frames são capturados continuamente.
- Os metadados são impressos no terminal em formato JSON.
- O vídeo é gravado no diretório `videos/`.
- A captura pode ser encerrada com `Ctrl+C`.

O caminho padrão do vídeo gerado é:

```text
videos/video_capturado.mp4
```

O encerramento por `Ctrl+C` foi validado no ambiente de desenvolvimento atual.

## 8. Frames e metadados

### 8.1. Representação do frame

A classe `Frame`, definida em `src/frame.py`, representa uma imagem capturada com os seguintes campos:

| Campo | Descrição |
|---|---|
| `image` | Imagem do frame representada como array NumPy |
| `timestamp_ns` | Timestamp associado ao buffer, em nanossegundos |
| `frame_id` | Identificador sequencial atribuído aos frames retornados pela implementação |

O identificador sequencial é gerado pelo software. Ele não deve ser interpretado como o número original do frame fornecido pelo sensor.

### 8.2. Metadados

A classe `FrameMetadata`, definida em `src/metadata.py`, organiza as informações descritivas da captura:

| Campo | Descrição |
|---|---|
| `camera_id` | Identificador lógico da câmera selecionada |
| `width` | Largura do frame em pixels |
| `height` | Altura do frame em pixels |
| `fps` | FPS configurado para a captura |
| `is_undistorted` | Indica se o frame foi corrigido quanto à distorção |

O programa principal emite os metadados no terminal em formato JSON. Os campos atuais incluem:

- `camera_id`
- `frame_id`
- `timestamp_ns`
- `resolution_width`
- `resolution_height`
- `fps`
- `is_undistorted`
- `shutter_speed_us`
- `gain_db`

Os campos `shutter_speed_us` e `gain_db` são atualmente preenchidos com `null`, pois não há coleta desses valores no fluxo principal validado.

O campo `fps` representa a configuração escolhida, e não uma medição contínua da taxa real de frames.

### 8.3. Considerações sobre o timestamp

Na implementação principal, o timestamp é obtido do buffer do GStreamer. Ele é expresso em nanossegundos e associado ao processamento do frame dentro do pipeline.

Esse valor não deve ser tratado automaticamente como o instante físico de exposição do sensor. A semântica temporal exata, a origem do relógio e a adequação aos requisitos do ODS precisam ser verificadas antes de uma integração que dependa de sincronização precisa.

## 9. Estrutura do projeto

A estrutura abaixo destaca os principais arquivos existentes no componente:

```text
P4/
├── config/
│   └── camera_calibration.json
├── data/
│   └── dataset_calibracao/
├── src/
│   ├── __init__.py
│   ├── camera_config.py
│   ├── camera_detector.py
│   ├── capture.py
│   ├── fake_capture.py
│   ├── frame.py
│   ├── gstreamer_capture.py
│   ├── imx519_capture.py
│   ├── main.py
│   ├── menu.py
│   ├── metadata.py
│   ├── undistort.py
│   ├── v4l2_capture.py
│   └── video_recorder.py
├── tests/
│   ├── coletar_calibracao.py
│   ├── teste_captura_video.py
│   ├── teste_frame_drops.py
│   ├── teste_memoria.py
│   ├── teste_undistort.py
│   └── teste_v4l2_timestamp.py
├── .gitignore
├── README.md
└── requirements.txt
```

Os diretórios de dados de calibração e de vídeos gerados podem conter arquivos locais que não são versionados pelo Git. A listagem acima descreve os arquivos de código e configuração, não garante que todos os diretórios de dados estejam presentes em um clone novo.

### 9.1. Principais módulos

| Arquivo | Responsabilidade |
|---|---|
| `camera_config.py` | Configurações e modos conhecidos das câmeras |
| `camera_detector.py` | Detecção de dispositivos de vídeo |
| `menu.py` | Seleção da câmera e do modo de captura |
| `gstreamer_capture.py` | Captura principal via pipeline GStreamer |
| `frame.py` | Representação do frame |
| `metadata.py` | Estrutura de metadados |
| `video_recorder.py` | Gravação do vídeo em MP4 |
| `undistort.py` | Aplicação da correção de distorção |
| `main.py` | Orquestração da captura e gravação |

## 10. Testes auxiliares e implementações experimentais

Além do fluxo principal, o repositório contém implementações anteriores e ferramentas destinadas à investigação de aspectos específicos da captura.

Esses módulos devem ser tratados separadamente do fluxo principal baseado em GStreamer. Sua presença no repositório não significa que estejam integrados ao programa principal nem que todos os testes tenham sido aprovados no ambiente atual.

### 10.1. Captura experimental com V4L2

- `src/v4l2_capture.py`: implementação de captura de baixo nível por meio de V4L2.
- `src/capture.py`: abstração de captura e implementação `WebcamCapture` baseada no módulo V4L2.

Esses módulos exploram o acesso direto ao dispositivo de vídeo no Linux e o tratamento de buffers e timestamps do V4L2.

### 10.2. Captura simulada

- `src/fake_capture.py`: fornece frames sintéticos para testes sem uma câmera real.

A captura simulada pode ser útil para testar partes da aplicação que dependem da estrutura de um frame, mas não comprova o funcionamento de uma câmera física.

### 10.3. Captura experimental para IMX519

- `src/imx519_capture.py`: implementação baseada em `Picamera2`, destinada à investigação da captura pela câmera IMX519.

Essa implementação ainda precisa ser validada no hardware correspondente e integrada ao fluxo principal, caso seja escolhida como parte da arquitetura final.

### 10.4. Ferramentas de teste

| Arquivo | Objetivo |
|---|---|
| `tests/teste_captura_video.py` | Avaliar captura, sequência de frames e intervalos |
| `tests/teste_frame_drops.py` | Investigar intervalos entre frames e possíveis perdas |
| `tests/teste_memoria.py` | Observar o consumo de memória durante a captura |
| `tests/teste_undistort.py` | Experimentar o processamento de correção de distorção |
| `tests/teste_v4l2_timestamp.py` | Inspecionar sequência e timestamps de buffers V4L2 |
| `tests/coletar_calibracao.py` | Coletar imagens para um conjunto de calibração |

Os testes que dependem de V4L2 utilizam a implementação experimental correspondente e podem depender do dispositivo, dos formatos suportados e das permissões do sistema.

A coleta de imagens para calibração não calcula, por si só, a matriz intrínseca nem os coeficientes de distorção.

Os testes auxiliares devem ser executados individualmente e ter seus resultados registrados antes de serem considerados validados. Não há garantia de que todos funcionem com a implementação principal baseada em GStreamer sem adaptações.

## 11. Calibração e correção de distorção

O arquivo `config/camera_calibration.json` contém campos para a matriz da câmera e os coeficientes de distorção utilizados por `src/undistort.py`.

Os valores presentes atualmente são ilustrativos e não representam uma calibração real da webcam EMEET, da IMX519 ou da IMX477.

A correção de distorção ainda não faz parte do fluxo principal validado. Para utilizá-la corretamente, será necessário:

1. Coletar imagens apropriadas da câmera que será utilizada.
2. Calcular os parâmetros de calibração a partir dessas imagens.
3. Salvar os parâmetros reais no arquivo de configuração.
4. Aplicar a correção aos frames capturados.
5. Verificar visualmente e quantitativamente o resultado.
6. Atualizar os metadados para refletir o processamento efetivamente aplicado.

Os parâmetros devem corresponder à câmera e à configuração óptica utilizadas. Não se deve reutilizar uma calibração ilustrativa ou de outra câmera como se fosse válida.

## 12. Próximos passos

As próximas atividades do P4 incluem:

- Consolidar e documentar os testes de captura e temporização.
- Avaliar perdas de frames e consumo de memória no fluxo principal.
- Definir a interface de entrega dos frames e metadados aos demais componentes ODS.
- Implementar e validar a calibração real e a correção de distorção.
- Investigar os requisitos temporais e a origem dos timestamps.
- Validar a captura com a Arducam IMX519 no Raspberry Pi 4.
- Adaptar e validar o fluxo para a plataforma Jetson.
- Revisar as implementações experimentais e decidir quais devem ser mantidas, integradas ou removidas.

## 13. Controle de versão e arquivos gerados

O repositório utiliza `.gitignore` para evitar o versionamento de arquivos locais, como o ambiente virtual, arquivos temporários e vídeos gerados durante os testes.

Antes de adicionar novos arquivos ao repositório, verificar se são código-fonte, configuração necessária ou artefatos gerados localmente. Conjuntos de calibração e vídeos devem ser versionados somente quando houver uma necessidade definida pelo projeto.

---

**Resumo do estado atual:** a captura contínua pela webcam EMEET via GStreamer, a emissão de metadados e a gravação em MP4 foram validadas no ambiente WSL2 utilizado no desenvolvimento. A calibração real, a integração com as demais câmeras, a validação dos testes auxiliares e a execução na plataforma Jetson continuam pendentes.
