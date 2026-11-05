# SIS-2 — P4: Fonte de Vídeo

**Projeto ODS 2026/2 · Componente P4 · Squad SIS-2 (Sinal e Dispositivo)**  
**Estado documentado:** 05/11/2026 · **Plataforma de validação atual:** NVIDIA Jetson Orin, Ubuntu 22.04 / JetPack R36.4.7

O **P4** captura quadros de câmeras CSI por V4L2, preserva o conteúdo bruto da imagem e disponibiliza **vídeo** e **eventos de metadados** por canais distintos:

- **GStreamer + memória compartilhada (SHM):** transporta os bytes RAW10 de cada quadro, acompanhados de um cabeçalho de identificação `P4R1`.
- **Apache Kafka:** publica eventos leves de início de sessão e metadados por quadro, **sem transportar os pixels**.

O componente oferece um **modo diagnóstico**, para testar somente a captura, e um **modo completo**, para publicar os quadros via SHM e, opcionalmente, os eventos via Kafka.

> **Estado real em 05/11/2026:** as câmeras **IMX519** e **IMX477** já foram validadas **individualmente** na Jetson, com captura `1920 × 1080`, formato `RG10` (Bayer RAW10) e transmissão pelo SHM. O leitor de teste conseguiu receber pacotes P4R1, verificar os metadados e comparar a integridade dos bytes RAW com SHA-256 em testes anteriores. **Ainda não concluímos** a integração com um consumidor real do ODS, a validação simultânea das câmeras, a confirmação de publicação Kafka na Jetson nem os testes prolongados de estabilidade.

## 1. Arquitetura

```text
IMX519 / IMX477 (CSI)
       │
       ▼
Driver CSI + V4L2 / linuxpy
       │  RG10 / RAW10; sequência e timestamp do driver
       ▼
P4 (Frame, FrameMetadata, sessão e métricas)
       │
       ├─────────────────────────────────────┐
       │                                     │
       ▼                                     ▼
SHMPublisher                           KafkaPublisher
GStreamer: appsrc → shmsink            Eventos JSON (formato B2)
P4R1 + bytes RAW10                     ods.session.started
       │                                ods.p4.frame
       ▼                                     │
Socket SHM local                             ▼
       │                              Broker / consumidores
       ▼
Leitor SHM (tests/shm_reader.py)
       │
       ▼
Cabeçalho + bytes RAW10
(visualização Bayer/RGB requer etapa adicional)
```

**Atenção:** o SHM é um transporte **local à mesma máquina**. Um processo em outro computador não acessa diretamente o socket `/tmp/...` da Jetson. O P4 **não** converte a imagem para RGB nem aplica correção de distorção; conforme a arquitetura ODS 6c, entrega o quadro bruto. Correção/calibração é responsabilidade de etapas posteriores.

## 2. Estado de implementação

| Item | Situação e evidência |
| --- | --- |
| Drivers/overlays CSI IMX519 e IMX477 | **Validado na Jetson**: dispositivos acessíveis e quadros reais capturados. |
| Captura por V4L2/LinuxPy | **Validada** nas duas câmeras, individualmente, a `1920 × 1080` e `RG10`. |
| Modo diagnóstico | **Validado**; captura 30 quadros por padrão, sem inicializar SHM ou Kafka. |
| Frame, metadados e sessões | **Implementados** em `Frame`, `FrameMetadata` e `P4`. |
| Transporte RAW10 via GStreamer/SHM | **Validado** em execuções limitadas, nas duas câmeras separadamente. |
| Protocolo P4R1 | **Implementado e testado**; inclui IDs, timestamp, formato, dimensões e tamanho RAW. |
| Recepção e integridade no leitor de teste | **Validada em testes separados**, inclusive por SHA-256; não equivale à homologação do I1 real. |
| Eventos `ods.session.started` e `ods.p4.frame` | **Implementados**; gerados em JSON. |
| Kafka no código | **Implementado**, com callbacks de confirmação, tratamento de falhas e testes simulados. |
| Kafka compartilhado na Jetson | **Pendente de teste de publicação/consumo confirmado**. Contratos e tópicos devem ser alinhados com TRA-1/Rafael. |
| Timestamps do driver | **Parcial**: origem `driver_eof` observada; ainda há uma discrepância temporal e um intervalo inicial a investigar. |
| Execução simultânea de IMX519 e IMX477 | **Não validada**. |
| Integração com consumidor real (I1/P6/outros) | **Pendente**. |
| Estabilidade prolongada, perdas, memória e recuperação | **Pendente**. |
| Testes automatizados | **14 testes aprovados** na última execução registrada durante o desenvolvimento. |

### 2.1. Resultados obtidos na Jetson

Em testes do **modo completo com Kafka desativado**, usando **120 quadros por execução**:

| Câmera | Frames capturados | Buffers aceitos pelo `appsrc` | Perdas estimadas | FPS médio informado |
| --- | ---: | ---: | ---: | ---: |
| IMX519 | 120 | 120 | 0 | 58,07 |
| IMX477 | 120 | 120 | 0 | 58,05 |

Cada execução reportou aproximadamente **497,69 MB** aceitos pelo `appsrc`, incluindo os cabeçalhos P4R1. Em testes **isolados de captura** e de **captura + SHM instrumentada**, a IMX477 apresentou aproximadamente **60 FPS**.

O valor de 58 FPS foi influenciado por um intervalo de **83,331 ms entre os frames 1 e 2**, seguido de intervalos próximos de 16,667 ms. A causa ainda está sob investigação. Os testes não justificam afirmar uma perda contínua de 2 FPS.

> `frames_aceitos_appsrc` significa que o GStreamer aceitou o buffer de entrada. **Não comprova que outro processo recebeu aquele quadro.** Essa recepção foi testada separadamente. Analogamente, `frames_perdidos_estimados = 0` não garante ausência absoluta de descartes no driver.

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

### 3.1. Representação dos bytes RAW10

`RG10` representa dados brutos de um sensor com **mosaico Bayer**, não uma imagem RGB pronta. Nas capturas atuais, cada quadro `1920 × 1080` possui **4.147.200 bytes** (2 bytes por pixel, usados como contêiner para amostras de 10 bits). O consumidor precisa interpretar corretamente a disposição das amostras e a matriz Bayer para obter uma imagem visualizável.

**Não** trate esses bytes como JPEG, PNG ou `RGB888`, nem tente exibi-los diretamente como `video/x-raw` convencional. O protocolo de SHM usa caps personalizados: `application/x-ods-frame`.

## 4. Dependências e preparação

Requisitos do ambiente validado:

- Jetson Orin com acesso às câmeras CSI pelo V4L2.
- Python 3.10 ou outra versão compatível com as bibliotecas instaladas no dispositivo.
- Pacotes Python do [`requirements.txt`](requirements.txt): `linuxpy==0.25.0`, `confluent-kafka==2.16.1`, `numpy` e `opencv-python`.
- GStreamer com `appsrc`, `shmsink`, `shmsrc`, `appsink` e bindings Python `gi` / PyGObject.

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
  v4l-utils
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

## 5. Executando o P4

Execute os comandos **na raiz do repositório**, com o ambiente virtual ativo.

### 5.1. Variáveis de ambiente

| Variável | Valor padrão atual | Função |
| --- | --- | --- |
| `P4_CAMERA` | `imx519` | Câmera selecionada (`imx519` ou `imx477`). |
| `P4_MODO_DIAGNOSTICO` | `true` | `true`: somente captura; `false`: modo completo. |
| `P4_ATIVAR_KAFKA` | `true` | No modo completo, `false` desativa o envio ao Kafka. |
| `P4_FRAME_LIMIT` | Não definido | Limita o total de quadros **no modo completo**; sem valor, o fluxo é contínuo. |
| `P4_KAFKA_BOOTSTRAP_SERVERS` | Não definido | Endereço do broker, obrigatório quando Kafka está ativo no modo completo. |

**Nota de versão:** `P4_FRAME_LIMIT` e `P4_ATIVAR_KAFKA` foram adicionadas ao `src/main.py` **na cópia local da Jetson**. Elas precisam ser incluídas em um commit e enviadas ao GitHub para os comandos desta seção funcionarem em um clone novo. O modo diagnóstico permanece limitado a **30 quadros**, independentemente de `P4_FRAME_LIMIT`.

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

### 5.3. Modo completo — SHM sem Kafka

**IMX519 — teste limitado a 120 quadros:**

```bash
PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx519 \
P4_MODO_DIAGNOSTICO=false \
P4_ATIVAR_KAFKA=false \
P4_FRAME_LIMIT=120 \
python -m src.main
```

**IMX477 — teste limitado a 120 quadros:**

```bash
PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx477 \
P4_MODO_DIAGNOSTICO=false \
P4_ATIVAR_KAFKA=false \
P4_FRAME_LIMIT=120 \
python -m src.main
```

O programa abre a câmera selecionada, publica pacotes P4R1 no socket configurado, imprime eventos de exemplo e encerra automaticamente após o limite. **Não há envio ao Kafka** quando `P4_ATIVAR_KAFKA=false`.

Se quiser conectar um leitor em outro terminal, **120 quadros duram aproximadamente 2 segundos**. Use um limite maior, por exemplo `P4_FRAME_LIMIT=600` (cerca de 10 segundos), ou omita o limite e finalize depois com `Ctrl+C`.

### 5.4. Modo completo — SHM + Kafka

**Somente após confirmar os tópicos e contratos com TRA-1/Rafael**, configure um broker autorizado:

```bash
export P4_KAFKA_BOOTSTRAP_SERVERS="HOST_DO_BROKER:PORTA"

PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx519 \
P4_MODO_DIAGNOSTICO=false \
P4_ATIVAR_KAFKA=true \
P4_FRAME_LIMIT=30 \
python -m src.main
```

Não use esse comando como primeiro teste de integração com um broker compartilhado sem validar o contrato e o tópico `ods.p4.frame`. `produce()` enfileira mensagens assincronamente; a confirmação real depende dos callbacks de entrega e dos contadores no encerramento.

## 6. Como outra equipe pode receber os quadros pelo SHM

### 6.1. Interface de transporte

O publicador usa, entre outros parâmetros:

```text
appsrc
  caps=application/x-ods-frame,version=1,
       width=1920,height=1080,storage-bits=16,framerate=0/1
  ! shmsink socket-path=/tmp/p4_imx519_shm
```

O socket varia conforme a câmera. Cada **buffer GStreamer** contém **um pacote P4R1 completo**: cabeçalho e bytes brutos do quadro. Os sockets só existem durante a execução do publicador (salvo resíduos de encerramento anormal).

O consumidor deve utilizar `shmsrc` e `appsink` para acessar os bytes, depois validar e interpretar o pacote conforme a próxima seção.

### 6.2. Testar a recepção com `tests/shm_reader.py`

O arquivo [`tests/shm_reader.py`](tests/shm_reader.py) é um **leitor de validação**, não um decodificador de imagem. Ele recebe **um pacote**, interpreta o cabeçalho e imprime `source_id`, `session_id`, `frame_id`, formato, quantidade de bytes RAW e hash SHA-256.

**Importante:** a versão atual do script aponta para **`/tmp/p4_raw_teste_shm`**, utilizado nos testes isolados. Para ler uma câmera real, é necessário mudar o caminho do socket. Um modo de testar **sem editar arquivos versionados** é criar uma cópia temporária:

**Terminal A — iniciar a IMX519 na Jetson:**

```bash
cd ~/SIS-2/p4
source venv/bin/activate

PYTHONPATH=/usr/lib/python3/dist-packages \
P4_CAMERA=imx519 \
P4_MODO_DIAGNOSTICO=false \
P4_ATIVAR_KAFKA=false \
P4_FRAME_LIMIT=600 \
python -m src.main
```

**Terminal B — enquanto o P4 está em execução, ler um pacote:**

```bash
cd ~/SIS-2/p4
source venv/bin/activate

sed 's@/tmp/p4_raw_teste_shm@/tmp/p4_imx519_shm@' \
  tests/shm_reader.py > /tmp/p4_imx519_reader.py

PYTHONPATH="$PWD:/usr/lib/python3/dist-packages" \
  python /tmp/p4_imx519_reader.py
```

Para a **IMX477**, troque `P4_CAMERA=imx519` por `P4_CAMERA=imx477` no terminal A e substitua o caminho no comando `sed` por `/tmp/p4_imx477_shm` no terminal B.

Exemplo de saída esperada do leitor (identificadores variam):

```text
Câmera: imx519
Sessão: <uuid-da-execucao>
Frame ID: <numero-do-quadro>
Formato: RG10
Bytes RAW recebidos: 4147200
SHA-256 RAW: <hash-hexadecimal>
```

O leitor precisa conectar **enquanto o produtor estiver ativo**. Se o socket não existir, confirme a seleção da câmera, se o produtor ainda está executando e se ambos os processos estão na **mesma Jetson**. Caso encontre um socket residual, investigue se há outro produtor ativo antes de removê-lo.

### 6.3. Como obter uma imagem visualizável

Receber os bytes RAW **não significa receber um PNG ou JPG**. Para obter uma imagem visualizável, o consumidor precisa:

1. Ler o pacote completo do `appsink`.
2. Separar e validar o cabeçalho `P4R1`.
3. Extrair os `data_size` bytes RAW e reconstruir a matriz `1920 × 1080` com amostras de 16 bits que contêm os dados de 10 bits.
4. Interpretar o alinhamento dos 10 bits e aplicar o **demosaicing Bayer RGGB**, seguido de normalização/conversão para exibição.
5. Salvar ou apresentar a imagem com uma ferramenta apropriada (por exemplo, OpenCV).

**Atenção:** a implementação atual de `tests/shm_reader.py` **não salva imagem em disco**; ela imprime metadados e SHA-256. A geração automatizada de PNG/JPG pode ser adicionada em um leitor de visualização, após confirmar a disposição dos valores RAW no sensor. A visualização não deve alterar os bytes originais transportados pelo P4.

## 7. Protocolo P4R1 — identificação dos quadros

A serialização fica em [`src/shm_protocol.py`](src/shm_protocol.py).

Formato de cada buffer:

| Ordem | Tamanho | Conteúdo |
| --- | --- | --- |
| 1 | 4 bytes | ASCII `P4R1` (identificador do protocolo). |
| 2 | 4 bytes | Comprimento do cabeçalho JSON (`uint32`, **big-endian**). |
| 3 | Variável | JSON em UTF-8 com os metadados do quadro. |
| 4 | `data_size` bytes | Quadro RAW original. |

Exemplo ilustrativo de cabeçalho JSON:

```json
{
  "source_id": "imx519",
  "session_id": "<uuid>",
  "frame_id": 30,
  "timestamp": 20116516463000,
  "width": 1920,
  "height": 1080,
  "format": "RG10",
  "raw": true,
  "data_size": 4147200
}
```

O consumidor pode utilizar diretamente `ler_cabecalho(pacote)`:

```python
from src.shm_protocol import ler_cabecalho

campos, inicio_raw = ler_cabecalho(pacote)
dados_raw = pacote[inicio_raw:]

assert len(dados_raw) == campos["data_size"]
```

A função rejeita identificadores incorretos, cabeçalhos incompletos e inconsistências entre o tamanho declarado e o recebido. **O protocolo P4R1 ainda é uma interface de integração proposta pelo P4:** é necessário formalizar sua adoção com os consumidores. A ordem de chegada dos eventos Kafka não substitui a identificação por `session_id` + `source_id` + `frame_id`.

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
    "width": 1920,
    "height": 1080,
    "format": "RG10",
    "fps": 60.0,
    "raw": true
  }
}
```

**Semântica temporal importante:**

- `payload.timestamp` é um número em **nanossegundos** extraído do timestamp V4L2 (quando identificado como monotônico), **não uma data UTC**.
- Nas câmeras CSI testadas, `timestamp_origin` foi observado como `driver_eof`; o instante sinalizado corresponde à semântica do driver, **não necessariamente ao início físico da exposição**.
- `occurred_at` é a data/hora UTC de **montagem do evento**, não o timestamp físico do sensor.
- A conversão opcional para UTC em `src/clock.py` é aproximada e está desativada na configuração principal (`CONVERTER_TIMESTAMP_UTC = False`).
- Em diagnóstico, a diferença `received_at_ns - captured_at_ns` apresentou aproximadamente **−41,6 s** nas câmeras CSI, embora `CLOCK_MONOTONIC` e `CLOCK_BOOTTIME` diferissem apenas cerca de `0,004 ms`. **Ainda não consideramos essa métrica de latência confiável; a causa deve ser investigada antes de qualquer garantia de sincronização.**
- O nome dos campos, suas unidades e os tópicos devem ser **conferidos com os contratos de TRA-1/Rafael** antes da integração final. Não pressupor que o esquema atual está homologado.

O produtor Kafka possui contadores de mensagens **enfileiradas**, **confirmadas**, **falhas de envio**, **falhas de entrega** e **pendentes**. Uma chamada bem-sucedida a `produce()` **não equivale** à confirmação de entrega; também não comprova que um consumidor recebeu o evento.

## 9. Testes

### 9.1. Testes automatizados

Na raiz do projeto, com `venv` ativado:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Na última execução registrada, **14 testes foram aprovados** (incluindo testes de P4, eventos, protocolo SHM, câmera simulada, métricas e publicador Kafka com mocks).

> Use **`test_*.py`**, não `teste_*.py`: há scripts legados que não fazem parte da suíte atual. Esses testes são complementares aos testes físicos de câmeras, SHM, Kafka e consumidores reais.

### 9.2. Evidências e limites

Já foram realizados testes de:

- Captura das duas CSI **individualmente**, em modo diagnóstico e completo.
- Leitura de pacotes P4R1 por um consumidor SHM de teste.
- Integridade dos bytes RAW, por comparação SHA-256 em testes separados.
- Recepção sequencial de 30 pacotes e leitura instrumentada de aproximadamente 120 quadros com taxas próximas de 60 FPS em ensaios específicos.
- Comportamento de sucesso/falha do produtor Kafka usando mocks.

**Ainda faltam:** teste end-to-end com broker Kafka autorizado na Jetson, interoperabilidade formal com consumidor real, duas CSI em paralelo, estresse, memória, backpressure e recuperação após falhas.

## 10. Problemas conhecidos e próximos passos da Sprint 3

1. **Timestamps:** investigar o salto inicial de 83,331 ms e a diferença negativa entre captura/recebimento; definir/validar a base temporal com as equipes responsáveis.
2. **Contrato de eventos:** confirmar com TRA-1/Rafael os tópicos e o payload definitivo, incluindo a convenção de IDs e o relógio.
3. **Kafka integrado:** validar entrega real em teste curto e autorizado, sem enviar pixels ao broker.
4. **Consumidor de vídeo:** conectar I1/P6 ou outro componente real ao SHM e conferir `source_id`, `session_id`, `frame_id` e conteúdo bruto.
5. **Duas câmeras:** executar IMX519 + IMX477 simultaneamente, com sockets separados, métricas e isolamento.
6. **Estabilidade:** executar testes prolongados de FPS, memória, limites de buffers e desligamento/desconexão de consumidores.
7. **Documentação e versionamento:** consolidar evidências, comandos reproduzíveis, validações e alterações ainda locais.

O P4 é um componente de **aquisição de vídeo**. A correção de distorção e o desenvolvimento do consumidor real não fazem parte da implementação do P4, mas exigem alinhamento de interface.

## 11. Arquivos principais

```text
p4/
├── src/
│   ├── main.py                 # Inicialização, modos e execução
│   ├── config.py               # Câmeras CSI e sockets
│   ├── v4l2_source.py          # Captura via V4L2 / linuxpy
│   ├── source.py               # Interface de fonte de vídeo
│   ├── frame.py                # Quadro capturado
│   ├── metadata.py             # Metadados do quadro
│   ├── p4.py                   # Sessão, leitura e entrega dos quadros
│   ├── capture_metrics.py      # Métricas da captura
│   ├── shm_protocol.py         # Serialização e leitura P4R1
│   ├── shm_publisher.py        # GStreamer / SHM
│   ├── events.py               # Eventos ods.session.started e ods.p4.frame
│   ├── kafka_publisher.py      # Publicação Kafka
│   └── clock.py                # Conversão temporal opcional
├── tests/
│   ├── shm_reader.py           # Leitor SHM de um pacote; não salva imagem
│   ├── test_p4.py              # Testes P4
│   ├── test_capture_metrics.py # Testes de métricas
│   ├── test_events.py          # Testes dos eventos
│   ├── test_shm_protocol.py    # Testes do protocolo
│   └── test_kafka_publisher.py # Testes de produtor Kafka
├── requirements.txt
├── .gitignore
└── README.md
```

**Nota sobre o repositório:** a pasta `venv/` contém o ambiente virtual local e **não deve entrar no Git**. O `.gitignore` publicado atualmente ignora `.venv/`, mas não `venv/`; na Jetson, `venv/` foi ignorada localmente em `.git/info/exclude`. Se for padronizar o repositório, acrescente `venv/` ao `.gitignore` versionado.

## 12. Preparação para compartilhar o repositório

As funcionalidades `P4_FRAME_LIMIT` e `P4_ATIVAR_KAFKA` e as últimas correções locais devem ser enviadas **junto com este README**. Antes de compartilhar comandos novos como se já estivessem publicados:

```bash
# Conferir arquivos modificados
git status --short

# Conferir formatação básica
git diff --check

# Executar os testes atuais
python -m unittest discover -s tests -p 'test_*.py' -v
```

Depois de revisar as alterações, preparar um commit específico incluindo `README.md`, `src/main.py` e os testes alterados. **Não inclua `venv/`, sockets, arquivos RAW, capturas ou credenciais.**

---

**Resumo para integração:** o P4 já captura vídeo RAW10 das duas CSI e o publica em pacotes identificados P4R1 pelo SHM local da Jetson. Um consumidor pode começar a validar a recepção pelos sockets documentados. **A conversão para uma imagem visualizável, o contrato definitivo com os consumidores, os timestamps e a entrega Kafka fim a fim ainda precisam de validação.**
