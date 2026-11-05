# SIS-2 — P4: Fonte de Vídeo

**Projeto ODS 2026/2 · Componente P4 · Squad SIS-2 (Sinal e Dispositivo)**

**Estado documentado:** 05/11/2026 · **Plataforma de validação atual:** NVIDIA Jetson Orin, Ubuntu 22.04 / JetPack R36.4.7

O **P4** fornece quadros e metadados de vídeo para outros componentes do ODS. Há duas fontes selecionáveis por variável de ambiente:

- **Câmera CSI:** captura das **IMX519** e **IMX477** por V4L2/LinuxPy, preservando os bytes brutos `RG10` (Bayer RAW10) da imagem.

- **Câmera simulada por arquivo:** decodifica um vídeo MP4 com OpenCV e entrega os quadros `BGR8` no ritmo de reprodução do arquivo. O teste atual utiliza `cars_extended.mp4` a `640 × 360`, com FPS informado de `60`.

As duas fontes seguem a mesma interface `VideoSource` e alimentam o mesmo componente `P4`. O componente publica dados e eventos por canais distintos:

- **GStreamer + memória compartilhada (SHM):** um pacote identificado por `P4R1` por frame, com cabeçalho JSON e bytes da imagem (`RG10` ou `BGR8`).

- **Apache Kafka (opcional):** eventos leves `ods.session.started` e `ods.p4.frame`, **sem transportar os pixels**.

O **modo diagnóstico** lê 30 quadros sem iniciar SHM ou Kafka. O **modo completo** transmite pelo SHM e, se habilitado, publica os metadados no Kafka.

> **Estado real em 05/11/2026:** IMX519 e IMX477 validadas **individualmente** na Jetson (`1920 × 1080`, `RG10`). Fonte MP4 validada pelo `main.py` (`640 × 360`, `BGR8`): **900 frames processados**, **900 buffers aceitos pelo `appsrc`** e leitura independente do **frame 219** com **691.200 bytes** e timestamp de reprodução. **20 testes automatizados passaram**. Além disso, **dois consumidores simultâneos** da IMX519 receberam os mesmos 30 frames consecutivos (`12493` a `12522`), sem saltos observados. Permanecem pendentes a integração com um consumidor real do ODS (I7), a publicação Kafka confirmada no broker compartilhado, a execução simultânea das CSI e os testes prolongados de estabilidade.

## 1. Arquitetura

```text
 IMX519 / IMX477 (CSI)        Vídeo MP4 (câmera simulada)
          |                               |
          v                               v
 V4L2Source / linuxpy            VideoFileSource / OpenCV
       RG10 / RAW10                        BGR8
          |                               |
          +---------------+---------------+
                          |
                          v
          P4 (VideoSource, Frame, metadados,
                  sessão e métricas)
                          |
           +--------------+--------------+
           |                             |
           v                             v
     SHMPublisher                   KafkaPublisher
   appsrc → shmsink             ods.session.started
    pacote P4R1                 ods.p4.frame (JSON)
      + pixels                         (sem pixels)
           |                             |
           v                             v
    SHM local /tmp/...          Broker e consumidores
           |
           v
   Um ou mais leitores SHM na Jetson (I7: integração real pendente)
```

**Atenção:** o SHM funciona **localmente, na mesma máquina**. Há **um socket por fonte**, não por aplicativo: dois leitores podem conectar ao mesmo fluxo sem reabrir a câmera. Esse compartilhamento foi comprovado em um teste curto com a IMX519. Um consumidor em outro computador não lê diretamente `/tmp/p4_file_shm` ou os sockets CSI da Jetson. No caso das câmeras CSI, P4 **não** realiza demosaicing, calibração ou correção de distorção; o consumidor precisa interpretar os dados `RG10`. A fonte MP4, por sua vez, **decodifica** o vídeo comprimido e disponibiliza pixels `BGR8`, sem transformá-los em RAW10.

## 2. Estado de implementação

| Item | Situação e evidência |
| --- | --- |
| Drivers/overlays CSI IMX519 e IMX477 | **Validado na Jetson**: dispositivos acessíveis e quadros reais capturados. |
| Captura por V4L2/LinuxPy | **Validada** nas duas câmeras, individualmente, a `1920 × 1080` e `RG10`. |
| Modo diagnóstico | **Validado**; captura 30 quadros por padrão, sem inicializar SHM ou Kafka. |
| Frame, metadados e sessões | **Implementados** em `Frame`, `FrameMetadata` e `P4` para ambas as fontes. |
| Transporte de vídeo via GStreamer/SHM | **Validado** com `RG10` nas câmeras CSI e `BGR8` na fonte MP4, em testes separados. |
| Protocolo P4R1 | **Implementado e testado**; identifica fonte/sessão/frame, formato, dimensões, tamanho dos dados e timestamps opcionais. |
| Recepção e integridade no leitor de teste | **Validada em testes separados**, inclusive por SHA-256; não equivale à homologação com o consumidor I7. |
| Eventos `ods.session.started` e `ods.p4.frame` | **Implementados**; gerados em JSON para câmera CSI e MP4. |
| Fonte MP4 (`VideoFileSource`) | **Validada** com `cars_extended.mp4` por OpenCV, simulação de ~60 FPS e seleção por `P4_SOURCE=file`. |
| SHM do MP4 para leitor independente | **Validado** com o `main.py`: leitor recebeu frame 219, `BGR8`, 691.200 bytes e timestamp de reprodução. |
| Dois consumidores simultâneos da IMX519 | **Validado em teste curto**: dois processos receberam 30 frames cada, IDs `12493` a `12522`, na mesma sessão e sem saltos observados. |
| Kafka no código | **Implementado**, com callbacks de confirmação, tratamento de falhas e testes simulados. |
| Kafka compartilhado na Jetson | **Broker acessível** em `172.18.4.56:9092`, ID `1`, após autorização do professor para iniciar o contêiner. Na consulta, não havia tópicos e a criação automática estava habilitada. **Publicação e consumo reais do P4 ainda não validados**; aguardar alinhamento dos nomes dos tópicos. |
| Timestamps do driver | **Conversão opcional implementada e testada**: TSC → `CLOCK_MONOTONIC_RAW` na IMX477 e IMX519; origem `driver_eof` observada. O salto inicial ocasional ainda não foi explicado. |
| Execução simultânea de IMX519 e IMX477 | **Não validada**. |
| Integração com consumidor real (I7/outros) | **Pendente**. |
| Estabilidade prolongada, perdas, memória e recuperação | **Pendente**. |
| Testes automatizados | **20 testes aprovados** em 05/11/2026, incluindo timestamps de reprodução MP4 em eventos e SHM. |

### 2.1. Resultados obtidos na Jetson

Em testes do **modo completo com Kafka desativado**, usando **120 quadros por execução**:

| Câmera | Frames capturados | Buffers aceitos pelo `appsrc` | Perdas estimadas | FPS médio informado |
| --- | ---: | ---: | ---: | ---: |
| IMX519 | 120 | 120 | 0 | 58,07 |
| IMX477 | 120 | 120 | 0 | 58,05 |

Cada execução reportou aproximadamente **497,69 MB** aceitos pelo `appsrc`, incluindo os cabeçalhos P4R1. Em testes **isolados de captura** e de **captura + SHM instrumentada**, a IMX477 apresentou aproximadamente **60 FPS**.

O valor de aproximadamente 58 FPS foi influenciado por um intervalo de **83,331 ms entre os frames 1 e 2** em uma execução do `main.py`, seguido de intervalos próximos de 16,667 ms. O intervalo entre leituras nesse ponto foi de aproximadamente 17,288 ms. A causa da descontinuidade nos timestamps ainda é desconhecida; **não há evidência suficiente de uma perda contínua de 2 FPS**. Essa investigação foi deixada como limitação conhecida para priorizar a integração.

> `frames_aceitos_appsrc` significa que o GStreamer aceitou o buffer de entrada. **Não comprova que outro processo recebeu aquele quadro.** Essa recepção foi testada separadamente. Analogamente, `frames_perdidos_estimados = 0` não garante ausência absoluta de descartes no driver.

### 2.2. Resultados da fonte MP4 simulada

No teste de 05/11/2026 com `P4_SOURCE=file`, `P4_MODO_DIAGNOSTICO=false`, `P4_ATIVAR_KAFKA=false` e `P4_FRAME_LIMIT=900`:

| Indicador | Resultado |
| --- | --- |
| Arquivo utilizado | `cars_extended.mp4` (H.264/MP4) |
| Resolução e formato após decodificação | `640 × 360`, `BGR8` |
| FPS informado pelo arquivo | `60.0` |
| Quadros processados pelo P4 | `900` |
| Buffers aceitos pelo `appsrc` | `900` |
| Bytes aceitos pelo `appsrc`, incluindo cabeçalhos | `622.368.790` |
| Frames perdidos estimados | `0` |
| Frame recebido em outro processo | `219`, com `691.200` bytes de pixels |
| Timestamp recebido | `received_at_monotonic_raw_ns` presente |
| Suíte de testes | `20` aprovados |

O intervalo entre os eventos de frame impressos a cada 30 quadros foi próximo de **0,5 s**, coerente com uma reprodução em torno de 60 FPS. O indicador `fps_medio` aparece como `null` porque o cálculo atual usa timestamps de captura física; **não deve ser usado para concluir que o MP4 não está sendo temporizado**.

**Limite da evidência:** 900 buffers aceitos pelo `appsrc` não comprovam entrega ou consumo de todos os 900 quadros. O leitor independente validou **um quadro real recebido**. A integração com o consumidor I7 ainda precisa ser realizada.

### 2.3. Dois consumidores simultâneos da IMX519

Em 05/11/2026, **uma única instância do P4** manteve a IMX519 aberta e publicou `RG10` em `/tmp/p4_imx519_shm`. Dois processos leitores independentes foram iniciados em paralelo, conectados ao **mesmo socket SHM**.

| Indicador | Leitor A | Leitor B |
| --- | --- | --- |
| Frames recebidos | 30 | 30 |
| Primeiro / último ID | `12493` / `12522` | `12493` / `12522` |
| Saltos observados | 0 | 0 |
| Sessão | `ce8dbe90-f97c-4693-bddc-918a63dac411` | Mesma sessão |
| Formato | `RG10`, 1920 × 1080 | `RG10`, 1920 × 1080 |
| Código de saída | 0 | 0 |

Em um teste anterior de um único frame por leitor, ambos receberam o **frame 4689** da mesma sessão, com **4.147.200 bytes** e hashes SHA-256 iguais. Os resultados indicam que o SHM atual permite compartilhar a captura com dois consumidores, **sem abrir `/dev/video1` duas vezes**.

**Limites:** foram testados apenas dois leitores por períodos curtos. O teste não comprova que consumidores lentos, múltiplas equipes sob carga pesada ou execuções prolongadas receberão todos os frames sem descarte ou impacto de desempenho. O leitor temporário de 30 frames foi usado fora do repositório (`/tmp/p4_reader_30.py`); não faz parte da suíte automatizada.

## 3. Câmeras e configuração atual

As definições estão em [`src/config.py`](src/config.py):

| Parâmetro | IMX519 | IMX477 |
| --- | --- | --- |
| Nome em `P4_CAMERA` | `imx519` | `imx477` |
| Dispositivo no ambiente testado | `/dev/video1` | `/dev/video0` |
| `sensor_mode` | `2` | `1` |
| Resolução | `1920 × 1080` | `1920 × 1080` |
| Formato V4L2 | `RG10` | `RG10` |
| `raw` | `true` | `true` |
| Socket SHM | `/tmp/p4_imx519_shm` | `/tmp/p4_imx477_shm` |

Ambas estão habilitadas. **Os caminhos `/dev/videoX` dependem da configuração da Jetson e podem mudar** após alterações de driver, overlay, conexão física ou reinicialização. Confirme os dispositivos antes de executar o programa:

```bash
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
v4l2-ctl -d /dev/video1 --list-formats-ext
```

Os sensores exigem drivers e overlays CSI compatíveis com cada câmera. A instalação desses drivers/overlays é específica do hardware e **não é automatizada por este repositório**; não troque overlays da Jetson compartilhada sem alinhar com a equipe.

### 3.1. Fonte simulada por arquivo

A implementação `src/video_file_source.py` utiliza OpenCV (`cv2.VideoCapture`), devolve `Frame` com formato **`BGR8`**, lê as dimensões e o FPS do arquivo e controla o ritmo da reprodução com relógio monotônico. No arquivo atual, a saída é **640 × 360**; não há redimensionamento automático para `1280 × 720`.

O `main.py` seleciona o socket `/tmp/p4_file_shm` para essa fonte, possui `source_id` derivado do nome do arquivo (por exemplo, `file_cars_extended`) e define `raw=False`. O vídeo é reproduzido **uma vez**; no fim, o `main.py` trata `StopIteration` como encerramento normal. Não existe loop automático.

### 3.2. Representação dos bytes RAW10

`RG10` representa dados brutos de um sensor com **mosaico Bayer**, não uma imagem RGB pronta. Nas capturas atuais, cada quadro `1920 × 1080` possui **4.147.200 bytes** (2 bytes por pixel, usados como contêiner para amostras de 10 bits). O consumidor precisa interpretar corretamente a disposição das amostras e a matriz Bayer para obter uma imagem visualizável.

**Não** trate esses bytes como JPEG, PNG ou `RGB888`, nem tente exibi-los diretamente como `video/x-raw` convencional. O protocolo de SHM usa caps personalizados: `application/x-ods-frame`.

## 4. Dependências e preparação

Requisitos do ambiente validado:

- Jetson Orin com acesso às câmeras CSI pelo V4L2 (para o modo CSI); a fonte por arquivo funciona sem as câmeras.

- Python 3.10 ou outra versão compatível com as bibliotecas instaladas no dispositivo.

- Dependências Python declaradas no `requirements.txt`: `linuxpy==0.25.0`, `confluent-kafka==2.16.1`, `numpy==2.2.6` e `opencv-python-headless==5.0.0.93`. Evite instalar simultaneamente `opencv-python` e `opencv-python-headless` na mesma `venv`.

- GStreamer com `appsrc`, `shmsink`, `shmsrc`, `appsink` e bindings Python `gi` / PyGObject.

- Para ativar a normalização TSC: arquitetura **AArch64** e compilador **GCC**, usados para gerar uma biblioteca nativa local.

Na **Jetson já configurada do projeto**, entre na pasta do repositório e ative o ambiente virtual existente:

```bash
cd ~/SIS-2/p4
source venv/bin/activate
```

Se for preparar **outro ambiente Ubuntu autorizado**, instale as dependências de sistema necessárias (pode ser necessário adaptar à imagem do sistema):

```bash
sudo apt update
sudo apt install -y \
  python3-venv python3-pip python3-gi \
  gir1.2-gstreamer-1.0 \
  gstreamer1.0-tools gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
  v4l-utils gcc
```

Para clonar e instalar as dependências Python:

```bash
git clone https://github.com/ods-26-2/p4.git
cd p4
python3 -m venv --system-site-packages venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Na Jetson usada nos testes, o binding `gi` instalado pelo sistema ficou acessível ao Python do ambiente virtual com:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages python -c \
  "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print(Gst.version_string())"
```

Confirme também a instalação dos elementos GStreamer:

```bash
gst-inspect-1.0 shmsink
gst-inspect-1.0 shmsrc
```

> O `PYTHONPATH` acima reflete o **ambiente da Jetson testada**. Em outros sistemas, o caminho dos pacotes de sistema pode ser diferente. Não é necessário instalar ou iniciar um broker Kafka para testar **somente o SHM**.

**Dependências testadas na Jetson:** `opencv-python-headless==5.0.0.93` e `numpy==2.2.6`, agora declaradas no `requirements.txt`. O comando `python -m pip check` não encontrou conflitos, e os 20 testes automatizados foram aprovados. Isso não substitui testes de instalação em outras máquinas.

### 4.1. Compilar o conversor de relógios TSC (opcional)

Na Jetson AArch64, a partir da raiz do repositório:

```bash
bash scripts/build_tsc_clock.sh
```

O script compila `src/tsc_clock.c` para `build/libp4_tsc_clock.so`, usando o contador ARM e `CLOCK_MONOTONIC_RAW` para medir, em execução, o deslocamento TSC → RAW. **Não existe offset fixo gravado no código.** A biblioteca compilada fica em `build/`, ignorada pelo Git; após clonar o repositório em outra Jetson, é necessário compilá-la novamente para utilizar `P4_NORMALIZAR_TSC=true`.

A classe `src/tsc_converter.py` acessa a biblioteca via `ctypes`. A medição do offset acontece na inicialização do conversor, não a cada quadro. O teste na Jetson encontrou aproximadamente **42.208,155 ms** de offset; esse número é **resultado observado**, não uma constante a reutilizar em outros sistemas.

A normalização só deve ser habilitada para as câmeras CSI verificadas (**IMX477** e **IMX519**) na Jetson testada. Os testes curtos indicaram diferenças estimadas de captura → leitura de cerca de **14–16 ms** para IMX477 e **20–22 ms** para IMX519, mas **não são uma calibração absoluta de latência** nem garantem sincronização com o áudio. A precisão e a estabilidade em sessões longas ainda precisam de avaliação.

## 5. Executando o P4

Execute os comandos **na raiz do repositório**, com o ambiente virtual ativo.

### 5.1. Variáveis de ambiente

| Variável | Valor padrão atual | Função |
| --- | --- | --- |
| `P4_SOURCE` | `camera` | `camera`: CSI; `file`: vídeo por arquivo. |
| `P4_VIDEO_PATH` | Não definido | Caminho do arquivo MP4; obrigatório se `P4_SOURCE=file`. |
| `P4_CAMERA` | `imx519` | Câmera CSI (`imx519` ou `imx477`); utilizado apenas em `P4_SOURCE=camera`. |
| `P4_MODO_DIAGNOSTICO` | `true` | `true`: somente captura; `false`: modo completo. |
| `P4_ATIVAR_KAFKA` | `true` | No modo completo, `false` desativa o envio ao Kafka. |
| `P4_NORMALIZAR_TSC` | `false` | `true`: usa a biblioteca TSC para preencher timestamps em `CLOCK_MONOTONIC_RAW`; requer compilação prévia. |
| `P4_FRAME_LIMIT` | Não definido | Limita o total de quadros **no modo completo**; sem valor, o fluxo é contínuo. |
| `P4_KAFKA_BOOTSTRAP_SERVERS` | Não definido | Endereço do broker, obrigatório quando Kafka está ativo no modo completo. |

O modo diagnóstico permanece limitado a **30 quadros**, independentemente de `P4_FRAME_LIMIT`. A opção `P4_NORMALIZAR_TSC=true` aplica-se **somente às câmeras CSI validadas** e exige compilar previamente `bash scripts/build_tsc_clock.sh`. Para o MP4, o P4 fornece o timestamp de reprodução em `received_at_monotonic_raw_ns` mesmo sem normalização TSC. No modo completo, Kafka está **ativado por padrão**: configure `P4_ATIVAR_KAFKA=false` para executar localmente apenas com SHM.

### 5.2. Modo diagnóstico — somente captura

**IMX519:**

```bash
P4_CAMERA=imx519 P4_MODO_DIAGNOSTICO=true python -m src.main
```

**IMX477:**

```bash
P4_CAMERA=imx477 P4_MODO_DIAGNOSTICO=true python -m src.main
```

Captura 30 quadros e imprime metadados periodicamente. Não inicializa os publicadores de SHM ou Kafka; o evento de início da sessão aparece **apenas no terminal**.

Para inspecionar a conversão com a IMX477, após compilar a biblioteca:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx477 \
P4_MODO_DIAGNOSTICO=true \
P4_NORMALIZAR_TSC=true \
P4_ATIVAR_KAFKA=false \
python -m src.main
```

Nesse modo, o P4 exibe periodicamente a diferença **estimada** entre captura e leitura em `CLOCK_MONOTONIC_RAW`. Ambas as câmeras foram testadas nessa condição, com cerca de 60 FPS em execuções de 30 frames.

### 5.3. Modo completo — SHM sem Kafka

**IMX519 — teste limitado a 120 quadros:**

```bash
PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx519 \
P4_MODO_DIAGNOSTICO=false \
P4_NORMALIZAR_TSC=true \
P4_ATIVAR_KAFKA=false \
P4_FRAME_LIMIT=120 \
python -m src.main
```

**IMX477 — teste limitado a 120 quadros:**

```bash
PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx477 \
P4_MODO_DIAGNOSTICO=false \
P4_NORMALIZAR_TSC=true \
P4_ATIVAR_KAFKA=false \
P4_FRAME_LIMIT=120 \
python -m src.main
```

O programa abre a câmera selecionada, publica pacotes P4R1 no socket configurado, imprime eventos de exemplo e encerra automaticamente após o limite. **Não há envio ao Kafka** quando `P4_ATIVAR_KAFKA=false`. Nos exemplos acima, `P4_NORMALIZAR_TSC=true` adiciona ao cabeçalho SHM o timestamp convertido sem substituir o original; compile a biblioteca antes de executar.

Se quiser conectar um leitor em outro terminal, **120 quadros duram aproximadamente 2 segundos**. Use um limite maior, por exemplo `P4_FRAME_LIMIT=600` (cerca de 10 segundos), ou omita o limite e finalize depois com `Ctrl+C`.

### 5.4. Modo completo — SHM + Kafka

**Somente após confirmar os tópicos e contratos com TRA-1/Rafael**, configure um broker autorizado:

```bash
export P4_KAFKA_BOOTSTRAP_SERVERS="HOST_DO_BROKER:PORTA"
PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx519 \
P4_MODO_DIAGNOSTICO=false \
P4_NORMALIZAR_TSC=true \
P4_ATIVAR_KAFKA=true \
P4_FRAME_LIMIT=30 \
python -m src.main
```

Não use esse comando como primeiro teste de integração com um broker compartilhado sem validar o contrato e o tópico `ods.p4.frame`. `produce()` enfileira mensagens assincronamente; a confirmação real depende dos callbacks de entrega e dos contadores no encerramento.

### 5.5. Câmera simulada — reproduzir MP4 como fonte do P4

O arquivo MP4 **simula uma câmera de vídeo**, sem converter seu conteúdo para RG10. Os pixels entregues são `BGR8`, adequados para leitores que consigam interpretar quadros BGR. Para reproduzir o vídeo de teste, deixe-o, por exemplo, em `~/SIS-2/videos/cars_extended.mp4`. **O arquivo MP4 não precisa ser versionado no repositório.**

**Diagnóstico (30 quadros; sem SHM/Kafka):**

```bash
P4_SOURCE=file \
P4_VIDEO_PATH=/home/sys2/SIS-2/videos/cars_extended.mp4 \
P4_MODO_DIAGNOSTICO=true \
python -m src.main
```

**Modo completo (120 quadros; SHM local, Kafka desligado):**

```bash
PYTHONPATH="$PWD:/usr/lib/python3/dist-packages" \
P4_SOURCE=file \
P4_VIDEO_PATH=/home/sys2/SIS-2/videos/cars_extended.mp4 \
P4_MODO_DIAGNOSTICO=false \
P4_ATIVAR_KAFKA=false \
P4_NORMALIZAR_TSC=false \
P4_FRAME_LIMIT=120 \
python -m src.main
```

**Para conectar um consumidor em outro terminal**, use por exemplo `P4_FRAME_LIMIT=900` (cerca de 15 s) e conecte ao socket `/tmp/p4_file_shm` enquanto o produtor está ativo. O frame entregue é `640 × 360 × 3 = 691.200` bytes, com `format=BGR8`, `raw=false` e cabeçalho P4R1.

O `P4_VIDEO_PATH` pode apontar para outro arquivo compatível com `cv2.VideoCapture`; resolução e FPS são lidos do arquivo. O programa não realiza loop nem força resolução de `1280 × 720`.

**Quando chega ao fim do arquivo**, sem `P4_FRAME_LIMIT` menor que a duração, o processo encerra a reprodução normalmente. O timestamp da reprodução **não corresponde à data da filmagem**; veja a seção 8.

## 6. Como outra equipe pode receber os quadros pelo SHM

### 6.1. Interface de transporte

O publicador usa, entre outros parâmetros:

```text
appsrc
  caps=application/x-ods-frame,version=1,
       width=1920,height=1080,storage-bits=16,framerate=0/1
  ! shmsink socket-path=/tmp/p4_imx519_shm
```

O socket varia conforme a fonte. Para MP4, a caps correspondente é `application/x-ods-frame,version=1,width=640,height=360,storage-bits=24,framerate=0/1`, em `/tmp/p4_file_shm`. Cada **buffer GStreamer** contém **um pacote P4R1 completo**: cabeçalho JSON e bytes de um quadro (`RG10` ou `BGR8`). Os sockets só existem durante a execução do publicador (salvo resíduos de encerramento anormal).

O consumidor deve utilizar `shmsrc` e `appsink` para acessar os bytes, depois validar e interpretar o pacote conforme a próxima seção. **Uma mesma fonte pode atender mais de um consumidor ao mesmo tempo**, conforme o teste da seção 2.3.

### 6.2. Testar a recepção com `tests/shm_reader.py`

O arquivo [`tests/shm_reader.py`](tests/shm_reader.py) é um **leitor de validação**, não um decodificador de imagem. Ele recebe **um pacote**, interpreta o cabeçalho e imprime `source_id`, `session_id`, `frame_id`, formato, quantidade de bytes RAW e hash SHA-256.

Esse leitor de teste seleciona as **câmeras CSI** automaticamente por `P4_CAMERA`, consultando [`src/config.py`](src/config.py). Para a fonte MP4, foi utilizado um consumidor independente conectado a `/tmp/p4_file_shm`; **não presuma que `tests/shm_reader.py` já tenha seleção por `P4_SOURCE=file`**.

**Terminal A — iniciar a IMX477 na Jetson:**

```bash
cd ~/SIS-2/p4
source venv/bin/activate
PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx477 \
P4_MODO_DIAGNOSTICO=false \
P4_NORMALIZAR_TSC=true \
P4_ATIVAR_KAFKA=false \
P4_FRAME_LIMIT=600 \
python -m src.main
```

**Terminal B — conectar enquanto o produtor estiver em execução:**

```bash
cd ~/SIS-2/p4
source venv/bin/activate
P4_CAMERA=imx477 \
PYTHONPATH="$PWD:/usr/lib/python3/dist-packages" \
python tests/shm_reader.py
```

Para a IMX519, substitua `P4_CAMERA=imx477` por `P4_CAMERA=imx519` **nos dois terminais**.

Uma execução real em 05/11/2026 recebeu o frame **220** da IMX477, identificou o formato `RG10`, leu **4.147.200 bytes** RAW e calculou SHA-256. Isso confirma que outro processo consegue receber e interpretar **um pacote**; o hash calculado isoladamente não prova que foi comparado com um hash do produtor nesta execução, nem que todos os 600 frames foram entregues.

O leitor deve conectar **enquanto o produtor está ativo**, na **mesma Jetson**. Se não houver socket, confira a câmera selecionada, o processo produtor e eventuais sockets residuais; não remova sockets sem verificar se outro produtor está em uso.

**Exemplo de consumidor independente para MP4:** com o produtor da seção 5.5 ainda em execução, abra outro terminal na mesma Jetson, dentro da raiz do repositório:

```bash
PYTHONPATH="$PWD:/usr/lib/python3/dist-packages" python - <<'PY'
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
from src.shm_protocol import ler_cabecalho
Gst.init(None)
pipeline = Gst.parse_launch(
    "shmsrc socket-path=/tmp/p4_file_shm "
    "is-live=true do-timestamp=true "
    "! application/x-ods-frame,version=1,"
    "width=640,height=360,storage-bits=24,framerate=0/1 "
    "! appsink name=sink sync=false max-buffers=1 drop=true"
)
try:
    pipeline.set_state(Gst.State.PLAYING)
    sink = pipeline.get_by_name("sink")
    sample = sink.emit("try-pull-sample", 5 * Gst.SECOND)
    assert sample is not None, "Nenhum frame recebido"
    buffer = sample.get_buffer()
    ok, mapped = buffer.map(Gst.MapFlags.READ)
    assert ok, "Falha ao mapear buffer"
    try:
        pacote = bytes(mapped.data)
    finally:
        buffer.unmap(mapped)
    campos, inicio = ler_cabecalho(pacote)
    assert campos["format"] == "BGR8"
    assert campos["raw"] is False
    assert campos["timestamp"] is None
    assert campos.get("received_at_monotonic_raw_ns") is not None
    assert len(pacote[inicio:]) == 640 * 360 * 3
    print("Fonte:", campos["source_id"])
    print("Frame:", campos["frame_id"])
    print("Bytes de pixels:", len(pacote[inicio:]))
    print("Reprodução MONOTONIC_RAW:", campos["received_at_monotonic_raw_ns"])
    print("Integração P4 → SHM → consumidor validada!")
finally:
    pipeline.set_state(Gst.State.NULL)
PY
```

No teste executado, esse fluxo recebeu o **frame 219**, leu `691.200` bytes e encontrou o campo `received_at_monotonic_raw_ns`. **Isso não comprova entrega integral dos 900 quadros.**

### 6.3. Compartilhamento do mesmo socket por aplicativos diferentes

**Estratégia recomendada: um socket por fonte de vídeo.** Exemplo: o P4 abre a IMX519 **uma vez** e publica em `/tmp/p4_imx519_shm`; dois aplicativos, como I7 e outro componente, podem criar seus próprios `shmsrc` apontando para esse socket. Cada aplicativo processa os bytes recebidos de maneira independente. Não é necessário criar uma segunda instância do P4 para a mesma câmera.

A validação prática ocorreu com dois leitores simultâneos que receberam a **mesma sequência de 30 frames** (`12493`–`12522`) sem saltos observados. Houve também confirmação de hashes iguais para o mesmo frame em um teste de leitura única. **Isso demonstra interoperabilidade básica, não entrega garantida a consumidores lentos**. Filas do `appsink`, velocidade do consumidor e backpressure precisam ser avaliados na integração real.

A fonte MP4 atualmente utiliza um socket **fixo**: `/tmp/p4_file_shm`. Assim, **não é seguro iniciar dois produtores de MP4 independentes ao mesmo tempo nesse mesmo caminho**. Para reproduzir vários MP4 simultaneamente, será necessário configurar sockets distintos por fonte. Esse ajuste ainda não foi implementado.

### 6.4. Como obter uma imagem visualizável

O P4R1 **não transporta PNG ou JPG**. A interpretação depende de `format` no cabeçalho. Para a **fonte CSI (`RG10`)**, o consumidor precisa:

1. Ler o pacote completo do `appsink`.

2. Separar e validar o cabeçalho `P4R1`.

3. Extrair os `data_size` bytes RAW e reconstruir a matriz `1920 × 1080` com amostras de 16 bits que contêm os dados de 10 bits.

4. Interpretar o alinhamento dos 10 bits e aplicar o **demosaicing Bayer RGGB**, seguido de normalização/conversão para exibição.

5. Salvar ou apresentar a imagem com uma ferramenta apropriada (por exemplo, OpenCV).

**Atenção:** a implementação atual de `tests/shm_reader.py` **não salva imagem em disco**; ela imprime metadados e SHA-256. A geração automatizada de PNG/JPG pode ser adicionada em um leitor de visualização, após confirmar a disposição dos valores RAW no sensor. A visualização não deve alterar os bytes originais transportados pelo P4.

Para a **fonte MP4 (`BGR8`)**, cada quadro possui três canais de 8 bits em ordem **B, G, R**. O consumidor pode reconstruir a imagem com `numpy.frombuffer(dados, dtype="uint8").reshape(height, width, 3)` e convertê-la conforme a necessidade. Não é necessário demosaicing Bayer nesse caso. O exemplo de leitura fornecido acima **não** abre uma janela de visualização nem salva imagens.

## 7. Protocolo P4R1 — identificação dos quadros

A serialização fica em [`src/shm_protocol.py`](src/shm_protocol.py).

Formato de cada buffer:

| Ordem | Tamanho | Conteúdo |
| --- | --- | --- |
| 1 | 4 bytes | ASCII `P4R1` (identificador do protocolo). |
| 2 | 4 bytes | Comprimento do cabeçalho JSON (`uint32`, **big-endian**). |
| 3 | Variável | JSON em UTF-8 com os metadados do quadro. |
| 4 | `data_size` bytes | Pixels do quadro, no formato indicado por `format` (`RG10` ou `BGR8`). |

Exemplo ilustrativo de cabeçalho JSON:

```json
{
  "source_id": "imx519",
  "session_id": "<uuid>",
  "frame_id": 30,
  "timestamp": 20116516463000,
  "timestamp_monotonic_raw_ns": 20074308307688,
  "timestamp_monotonic_raw_clock": "CLOCK_MONOTONIC_RAW",
  "width": 1920,
  "height": 1080,
  "format": "RG10",
  "raw": true,
  "data_size": 4147200
}
```

Para as câmeras CSI, `timestamp` continua sendo o valor **original** do driver V4L2, na referência observada como TSC nesta Jetson. Os campos `timestamp_monotonic_raw_ns` e `timestamp_monotonic_raw_clock` são **opcionais** e só aparecem quando `P4_NORMALIZAR_TSC=true`. O número `timestamp_monotonic_raw_ns` representa uma base monotônica RAW, **não UTC**. Estes campos foram adicionados sem mudar o prefixo binário `P4R1`; consumidores com esquema rígido de JSON devem conferir a compatibilidade antes da integração.

**Para MP4**, o campo `timestamp` fica `null`, porque não representa a captura original do vídeo. O instante de reprodução é enviado separadamente em `received_at_monotonic_raw_ns`, acompanhado por `received_at_monotonic_raw_clock="CLOCK_MONOTONIC_RAW"`. Exemplo parcial de cabeçalho MP4:

```json
{
  "source_id": "file_cars_extended",
  "frame_id": 219,
  "timestamp": null,
  "received_at_monotonic_raw_ns": 82049053283040,
  "received_at_monotonic_raw_clock": "CLOCK_MONOTONIC_RAW",
  "width": 640,
  "height": 360,
  "format": "BGR8",
  "raw": false,
  "data_size": 691200
}
```

Esse é um **exemplo parcial**: o pacote real também contém `session_id`.

O consumidor pode utilizar diretamente `ler_cabecalho(pacote)`:

```python
from src.shm_protocol import ler_cabecalho
campos, inicio_raw = ler_cabecalho(pacote)
dados_frame = pacote[inicio_raw:]
assert len(dados_frame) == campos["data_size"]
```

A função rejeita identificadores incorretos, cabeçalhos incompletos e inconsistências entre o tamanho declarado e o recebido, para qualquer formato de pixels aceito. **O protocolo P4R1 ainda é uma interface de integração proposta pelo P4:** é necessário formalizar sua adoção com os consumidores. A ordem de chegada dos eventos Kafka não substitui a identificação por `session_id` + `source_id` + `frame_id`.

## 8. Eventos Kafka e metadados

Os eventos são montados em [`src/events.py`](src/events.py), e a publicação está em [`src/kafka_publisher.py`](src/kafka_publisher.py).

| Evento | Tópico usado no código | Quando ocorre |
| --- | --- | --- |
| Início da sessão | `ods.session.started` | Depois da primeira captura bem-sucedida, antes do primeiro frame ser entregue ao consumidor. |
| Metadados do quadro | `ods.p4.frame` | Para cada quadro, no modo completo com Kafka ativado. |

Envelope atual do evento de quadro (exemplo):

```json
{
  "message_id": "<uuid-da-mensagem>",
  "message_type": "event",
  "schema": "ods.p4.frame",
  "schema_version": "1.0",
  "producer": "P4",
  "occurred_at": "2026-11-04T23:29:21.451088Z",
  "source_id": "imx477",
  "session_id": "<uuid-da-sessao>",
  "payload": {
    "frame_id": 30,
    "timestamp": 20237661252000,
    "timestamp_monotonic_raw_ns": 20195453096688,
    "timestamp_monotonic_raw_clock": "CLOCK_MONOTONIC_RAW",
    "width": 1920,
    "height": 1080,
    "format": "RG10",
    "fps": 60.0,
    "raw": true
  }
}
```

No MP4, o evento `ods.p4.frame` preserva `payload.timestamp=null` e acrescenta opcionalmente `payload.received_at_monotonic_raw_ns` e `payload.received_at_monotonic_raw_clock`. No modo completo com Kafka desligado, os eventos são **montados e alguns são impressos no terminal**, mas não são publicados no broker.

**Semântica temporal importante:**

- `payload.timestamp` e o campo homônimo do P4R1 contêm o timestamp **original** do driver V4L2, em nanossegundos. Para as câmeras CSI da Jetson testada, as medições indicam uma referência baseada no **TSC do hardware**, apesar da sinalização monotônica nos flags V4L2. **Não é data UTC nem deve ser comparado diretamente com `CLOCK_MONOTONIC` do Python.**

- `timestamp_monotonic_raw_ns` (no payload e no P4R1) e `timestamp_monotonic_raw_clock` aparecem **somente com a normalização ativada**. A conversão estimada aplica `timestamp_original_ns - offset_tsc_raw_ns`, onde o offset é medido dinamicamente com o auxiliar C e `CLOCK_MONOTONIC_RAW`.

- `FrameMetadata` também pode conter `captured_at_monotonic_raw_ns` e `received_at_monotonic_raw_ns`. Para MP4, o segundo é o instante de reprodução na base `CLOCK_MONOTONIC_RAW`; o primeiro permanece ausente. `received_at_ns` continua seguindo a base `CLOCK_MONOTONIC`. **Não subtraia valores de bases diferentes.**

- Para os vídeos MP4, `timestamp_origin=file_playback_raw` indica **tempo de reprodução**, não instante físico original de filmagem. O campo legado `timestamp` permanece `null`; consumidores que o exigem não devem assumir valores preenchidos em todas as fontes.

- A origem observada foi `driver_eof`, que descreve a semântica informada pelo driver e **não equivale necessariamente ao início da exposição do sensor**.

- `occurred_at` é o horário UTC de **montagem do evento**, não o instante físico de exposição ou de captura.

- `src/clock.py` contém uma conversão UTC legada baseada em `CLOCK_MONOTONIC`, **desativada** (`CONVERTER_TIMESTAMP_UTC=False`); não a aplique diretamente ao timestamp TSC original.

- A relação TSC → RAW foi consistente nos testes curtos, mas **não foi validada para estabilidade de longo prazo, precisão absoluta ou sincronização com o P5**. Para áudio e vídeo alinhados, P5 e consumidores devem adotar a mesma referência de relógio ou um mapeamento acordado.

- Os campos adicionais, suas unidades e os tópicos precisam de **confirmação com TRA-1/Rafael e consumidores**, incluindo eventuais validadores de esquema estritos. A publicação real no broker Kafka ainda não foi confirmada.

O produtor Kafka possui contadores de mensagens **enfileiradas**, **confirmadas**, **falhas de envio**, **falhas de entrega** e **pendentes**. Uma chamada bem-sucedida a `produce()` **não equivale** à confirmação de entrega; também não comprova que um consumidor recebeu o evento.

## 9. Testes

### 9.1. Testes automatizados

Na raiz do projeto, com `venv` ativado:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Na última execução registrada em **05/11/2026, 20 testes foram aprovados**. A suíte inclui P4, eventos, protocolo SHM, metadados normalizados, conversor TSC com mocks, métricas, V4L2 simulado, publicador Kafka com mocks e `tests/test_file_playback.py` (timestamps MP4 em evento e cabeçalho SHM).

> Use **`test_*.py`**, não `teste_*.py`: há scripts legados que não fazem parte da suíte atual. Esses testes são complementares aos testes físicos de câmeras, SHM, Kafka e consumidores reais.

### 9.2. Evidências e limites

Já foram realizados testes de:

- Captura das duas CSI **individualmente**, em modo diagnóstico e completo.

- Leitura de pacotes P4R1 por um consumidor SHM de teste.

- Integridade dos bytes RAW, por comparação SHA-256 em testes separados.

- Recepção sequencial de 30 pacotes e leitura instrumentada de aproximadamente 120 quadros com taxas próximas de 60 FPS em ensaios específicos.

- Comportamento de sucesso/falha do produtor Kafka usando mocks.

- Leitura real de um frame RAW10 da IMX477 por um processo separado (`tests/shm_reader.py`), inclusive identificação de frame, tamanho e cálculo de SHA-256.

- Normalização opcional TSC → `CLOCK_MONOTONIC_RAW` nas câmeras IMX477 e IMX519, em testes diagnósticos de 30 frames; testes unitários dos novos campos no SHM e nos eventos.

- Reprodução do arquivo MP4 como câmera simulada, com `main.py`, 900 frames e publicação para `appsrc`.

- Recebimento independente de um pacote P4R1 `BGR8` do MP4 (frame 219), com validação de formato, tamanho e timestamp de reprodução.
- Dois consumidores simultâneos do mesmo socket da IMX519: 30 frames consecutivos por leitor, mesmos IDs `12493`–`12522` e zero saltos observados. Em teste separado, ambos receberam o mesmo frame 4689 com hash SHA-256 idêntico.
- Conexão ao broker Kafka em `172.18.4.56:9092` e consulta de metadados concluída; a publicação real ainda está pendente.

**Ainda faltam:** teste end-to-end de publicação/consumo dos eventos do P4 no broker Kafka, interoperabilidade formal com o I7, duas CSI em paralelo, teste prolongado com múltiplos consumidores, memória, backpressure e recuperação após falhas.

## 10. Problemas conhecidos e próximos passos da Sprint 3

1. **Contrato de timestamps e sincronização com P5:** acordar relógio comum, nomenclatura e semântica de timestamp original versus normalizado. A conversão TSC → `CLOCK_MONOTONIC_RAW` está implementada e testada localmente, mas a sincronização de áudio e vídeo **não está homologada**.

2. **Contrato de eventos:** confirmar com TRA-1/Rafael os tópicos, a versão do schema B2 e a aceitação dos campos opcionais `timestamp_monotonic_raw_ns` e `timestamp_monotonic_raw_clock` pelos consumidores.

3. **Kafka integrado:** o contêiner foi iniciado com autorização do professor e o broker responde em `172.18.4.56:9092`. Ainda falta validar a criação/alinhamento de tópicos, a publicação real, a confirmação de entrega e o consumo, sem enviar pixels ao Kafka.

4. **Consumidor real de vídeo:** conectar I7 ou outro componente do ODS ao SHM. Os leitores de teste já recebem pacotes RAW10 e BGR8, mas isso **não substitui** a homologação com o consumidor real.

5. **Duas câmeras:** validar IMX519 e IMX477 simultaneamente com sockets separados e métricas independentes.

6. **Estabilidade e múltiplos consumidores:** dois leitores já receberam 30 frames simultâneos sem saltos; executar testes prolongados com consumidores de diferentes velocidades, monitorando FPS, memória, backpressure, reconexão e recuperação após falhas.

7. **Descontinuidade inicial ocasional:** em uma execução do `main.py`, os timestamps do driver saltaram **83,331 ms** entre os frames 1 e 2, enquanto as leituras ficaram próximas de 17 ms. O FPS médio relatado chegou a aproximadamente 58 FPS, mas o teste isolado de 120 frames com TSC e SHM marcou 60 FPS. **Não foi comprovada perda contínua de 2 FPS; o problema não bloqueia a entrega funcional atual.**

8. **Fonte MP4 e contrato com o I7:** confirmar se o I7 consegue ler `P4R1`/BGR8 (`640 × 360`) ou se é necessário um adaptador de formato/resolução. A publicação no SHM já foi comprovada, mas o consumidor I7 ainda não foi testado.

9. **Próxima melhoria opcional:** configurar sockets distintos por fonte MP4 caso haja necessidade de reproduzir vários arquivos ao mesmo tempo; o socket `/tmp/p4_file_shm` continua compartilhado entre todas as execuções por arquivo.

O P4 é um componente de **aquisição de vídeo**. A correção de distorção e o desenvolvimento do consumidor real não fazem parte da implementação do P4, mas exigem alinhamento de interface. A fonte por arquivo é uma **simulação de entrada** útil para testes de integração com vídeos gravados.

## 11. Arquivos principais

```text
p4/
├── src/
│   ├── main.py                 # Inicialização, modos e execução
│   ├── config.py               # Câmeras CSI e sockets
│   ├── v4l2_source.py          # Captura via V4L2 / linuxpy
│   ├── video_file_source.py    # Arquivo de vídeo como câmera simulada (OpenCV)
│   ├── source.py               # Interface de fonte de vídeo
│   ├── frame.py                # Quadro capturado
│   ├── metadata.py             # Metadados originais e normalizados
│   ├── p4.py                   # Sessão, leitura e normalização opcional
│   ├── capture_metrics.py      # Métricas da captura
│   ├── shm_protocol.py         # Serialização e leitura P4R1
│   ├── shm_publisher.py        # GStreamer / SHM
│   ├── events.py               # Eventos ods.session.started e ods.p4.frame
│   ├── kafka_publisher.py      # Publicação Kafka
│   ├── clock.py                # Conversão UTC legada, desativada
│   ├── tsc_clock.c             # Medição nativa do offset TSC → RAW
│   └── tsc_converter.py        # Wrapper ctypes para conversão TSC
├── scripts/
│   └── build_tsc_clock.sh      # Compilação da biblioteca na Jetson AArch64
├── tests/
│   ├── shm_reader.py           # Leitor SHM de um pacote; não salva imagem
│   ├── test_p4.py              # Testes P4
│   ├── test_p4_tsc.py          # Metadados normalizados no P4
│   ├── test_file_playback.py   # Timestamp de reprodução MP4: evento + SHM
│   ├── test_capture_metrics.py # Testes de métricas
│   ├── test_events.py          # Testes dos eventos
│   ├── test_event_timestamps.py # Timestamp normalizado em eventos
│   ├── test_shm_protocol.py    # Testes do protocolo
│   ├── test_shm_timestamps.py  # Timestamp normalizado em P4R1
│   ├── test_tsc_converter.py   # Conversor TSC com mocks
│   └── test_kafka_publisher.py # Testes de produtor Kafka
├── build/                      # Binários locais: ignorados pelo Git
├── requirements.txt
├── .gitignore
└── README.md
```

**Arquivos locais:** `venv/`, `build/`, sockets, dados RAW capturados e credenciais **não devem ser versionados**. O `.gitignore` atual ignora `/build/`; confira também que o diretório do ambiente virtual `venv/` permaneça excluído antes do commit.

## 12. Versionamento e atualização da documentação

A câmera simulada, os novos metadados, a documentação e as dependências foram publicados no repositório [`ods-26-2/p4`](https://github.com/ods-26-2/p4), branch `main`, no commit **`1ca3faf`** (`feat(p4): adiciona camera simulada por arquivo MP4`). O push foi confirmado em 05/11/2026. O teste de dois consumidores simultâneos ocorreu **depois desse commit** e está sendo registrado nesta atualização do README.

Para verificar as alterações e validar a próxima atualização:

```bash
git status --short
git diff --check
python -m unittest discover -s tests -p 'test_*.py' -v
git diff --stat
```

Não versione `venv/`, `build/libp4_tsc_clock.so`, sockets SHM, vídeos locais de teste, bytes RAW, logs temporários nem credenciais. Os logs e o leitor temporário de 30 frames em `/tmp` serviram como evidência manual e **não estão incluídos no repositório**.

---

**Resumo para integração:** o P4 oferece **duas fontes** selecionáveis (`P4_SOURCE=camera` para IMX519/IMX477 em RG10 e `P4_SOURCE=file` para vídeo MP4 em BGR8). Ambas entregam pacotes P4R1 identificados pelo SHM local da Jetson, e os eventos JSON de metadados são montados sem incluir os pixels. A fonte MP4 foi validada pelo `main.py` com 900 frames e um consumidor independente recebeu o frame 219 com timestamp de reprodução. Dois leitores simultâneos da IMX519 receberam os mesmos 30 frames consecutivos sem saltos observados. **A homologação do contrato com I7, a sincronização com P5, a execução simultânea das CSI e a entrega Kafka fim a fim ainda estão pendentes.**
