# SIS-2 — P4: Fonte de Vídeo

**Projeto ODS 2026/2 · Componente P4 · Squad SIS-2 (Sinal e Dispositivo)**  
**Estado documentado:** 05/11/2026 · **Plataforma de validação atual:** NVIDIA Jetson Orin, Ubuntu 22.04 / JetPack R36.4.7

O **P4** captura quadros de câmeras CSI por V4L2, preserva o conteúdo bruto da imagem e disponibiliza **vídeo** e **eventos de metadados** por canais distintos:

- **GStreamer + memória compartilhada (SHM):** transporta os bytes RAW10 de cada quadro, acompanhados de um cabeçalho de identificação `P4R1`.
- **Apache Kafka:** publica eventos leves de início de sessão e metadados por quadro, **sem transportar os pixels**.

O componente oferece um **modo diagnóstico**, para testar somente a captura, e um **modo completo**, para publicar os quadros via SHM e, opcionalmente, os eventos via Kafka.

> **Estado real em 05/11/2026:** as câmeras **IMX519** e **IMX477** foram validadas **individualmente** na Jetson em `1920 × 1080`, `RG10` (Bayer RAW10). O SHM foi testado com outro processo: o leitor recebeu, por exemplo, o frame 220 da IMX477, com 4.147.200 bytes RAW e SHA-256 calculado. Foi implementada e testada a normalização opcional dos timestamps TSC para `CLOCK_MONOTONIC_RAW`, e **19 testes automatizados** passaram. **Ainda não concluímos** a integração com um consumidor real do ODS, a validação simultânea das câmeras, a confirmação de publicação Kafka na Jetson nem os testes prolongados de estabilidade.

## 1. Arquitetura

```text
IMX519 / IMX477 (CSI)
       │
       ▼
Driver CSI + V4L2 / linuxpy
       │  RG10 / RAW10; sequência e timestamp do driver
       ▼
P4 (Frame, FrameMetadata, sessão e métricas)
       │  conversão TSC → MONOTONIC_RAW opcional (metadados)
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
| Protocolo P4R1 | **Implementado e testado**; inclui IDs, timestamp original, timestamp normalizado opcional, formato, dimensões e tamanho RAW. |
| Recepção e integridade no leitor de teste | **Validada em testes separados**, inclusive por SHA-256; não equivale à homologação do I1 real. |
| Eventos `ods.session.started` e `ods.p4.frame` | **Implementados**; gerados em JSON. |
| Kafka no código | **Implementado**, com callbacks de confirmação, tratamento de falhas e testes simulados. |
| Kafka compartilhado na Jetson | **Pendente de teste de publicação/consumo confirmado**. Contratos e tópicos devem ser alinhados com TRA-1/Rafael. |
| Timestamps do driver | **Conversão opcional implementada e testada**: TSC → `CLOCK_MONOTONIC_RAW` na IMX477 e IMX519; origem `driver_eof` observada. O salto inicial ocasional ainda não foi explicado. |
| Execução simultânea de IMX519 e IMX477 | **Não validada**. |
| Integração com consumidor real (I1/P6/outros) | **Pendente**. |
| Estabilidade prolongada, perdas, memória e recuperação | **Pendente**. |
| Testes automatizados | **19 testes aprovados** em 05/11/2026, incluindo conversor nativo simulado, integração P4 e timestamps nos pacotes SHM e eventos. |

### 2.1. Resultados obtidos na Jetson

Em testes do **modo completo com Kafka desativado**, usando **120 quadros por execução**:

| Câmera | Frames capturados | Buffers aceitos pelo `appsrc` | Perdas estimadas | FPS médio informado |
| --- | ---: | ---: | ---: | ---: |
| IMX519 | 120 | 120 | 0 | 58,07 |
| IMX477 | 120 | 120 | 0 | 58,05 |

Cada execução reportou aproximadamente **497,69 MB** aceitos pelo `appsrc`, incluindo os cabeçalhos P4R1. Em testes **isolados de captura** e de **captura + SHM instrumentada**, a IMX477 apresentou aproximadamente **60 FPS**.

O valor de aproximadamente 58 FPS foi influenciado por um intervalo de **83,331 ms entre os frames 1 e 2** em uma execução do `main.py`, seguido de intervalos próximos de 16,667 ms. O intervalo entre leituras nesse ponto foi de aproximadamente 17,288 ms. A causa da descontinuidade nos timestamps ainda é desconhecida; **não há evidência suficiente de uma perda contínua de 2 FPS**. Essa investigação foi deixada como limitação conhecida para priorizar a integração.

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
| `P4_CAMERA` | `imx519` | Câmera selecionada (`imx519` ou `imx477`). |
| `P4_MODO_DIAGNOSTICO` | `true` | `true`: somente captura; `false`: modo completo. |
| `P4_ATIVAR_KAFKA` | `true` | No modo completo, `false` desativa o envio ao Kafka. |
| `P4_NORMALIZAR_TSC` | `false` | `true`: usa a biblioteca TSC para preencher timestamps em `CLOCK_MONOTONIC_RAW`; requer compilação prévia. |
| `P4_FRAME_LIMIT` | Não definido | Limita o total de quadros **no modo completo**; sem valor, o fluxo é contínuo. |
| `P4_KAFKA_BOOTSTRAP_SERVERS` | Não definido | Endereço do broker, obrigatório quando Kafka está ativo no modo completo. |

O modo diagnóstico permanece limitado a **30 quadros**, independentemente de `P4_FRAME_LIMIT`. Para incluir os novos timestamps no SHM e nos eventos JSON, configure `P4_NORMALIZAR_TSC=true`; caso contrário, os campos normalizados ficam ausentes. Após clonar, gere primeiro a biblioteca com `bash scripts/build_tsc_clock.sh`.

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

O leitor seleciona o socket automaticamente por `P4_CAMERA`, consultando [`src/config.py`](src/config.py); não é necessário editar o código nem criar cópias temporárias.

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
  "timestamp_monotonic_raw_ns": 20074308307688,
  "timestamp_monotonic_raw_clock": "CLOCK_MONOTONIC_RAW",
  "width": 1920,
  "height": 1080,
  "format": "RG10",
  "raw": true,
  "data_size": 4147200
}
```

`timestamp` continua sendo o valor **original** do driver V4L2, na referência observada como TSC nesta Jetson. Os campos `timestamp_monotonic_raw_ns` e `timestamp_monotonic_raw_clock` são **opcionais** e só aparecem quando `P4_NORMALIZAR_TSC=true`. O número `timestamp_monotonic_raw_ns` representa uma base monotônica RAW, **não UTC**. Estes campos foram adicionados sem mudar o prefixo binário `P4R1`; consumidores com esquema rígido de JSON devem conferir a compatibilidade antes da integração.

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

**Semântica temporal importante:**

- `payload.timestamp` e o campo homônimo do P4R1 contêm o timestamp **original** do driver V4L2, em nanossegundos. Para as câmeras CSI da Jetson testada, as medições indicam uma referência baseada no **TSC do hardware**, apesar da sinalização monotônica nos flags V4L2. **Não é data UTC nem deve ser comparado diretamente com `CLOCK_MONOTONIC` do Python.**
- `timestamp_monotonic_raw_ns` (no payload e no P4R1) e `timestamp_monotonic_raw_clock` aparecem **somente com a normalização ativada**. A conversão estimada aplica `timestamp_original_ns - offset_tsc_raw_ns`, onde o offset é medido dinamicamente com o auxiliar C e `CLOCK_MONOTONIC_RAW`.
- `FrameMetadata` também pode conter `captured_at_monotonic_raw_ns` e `received_at_monotonic_raw_ns` para comparar os dois instantes na mesma referência; `received_at_ns` continua seguindo a lógica antiga, em `CLOCK_MONOTONIC` para frames do driver. **Não subtraia valores de bases diferentes.**
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

Na última execução registrada em **05/11/2026, 19 testes foram aprovados**. A suíte inclui P4, eventos, protocolo SHM, metadados normalizados, conversor TSC com mocks, métricas, V4L2 simulado e publicador Kafka com mocks.

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

**Ainda faltam:** teste end-to-end com broker Kafka autorizado na Jetson, interoperabilidade formal com consumidor real, duas CSI em paralelo, estresse, memória, backpressure e recuperação após falhas.

## 10. Problemas conhecidos e próximos passos da Sprint 3

1. **Contrato de timestamps e sincronização com P5:** acordar relógio comum, nomenclatura e semântica de timestamp original versus normalizado. A conversão TSC → `CLOCK_MONOTONIC_RAW` está implementada e testada localmente, mas a sincronização de áudio e vídeo **não está homologada**.
2. **Contrato de eventos:** confirmar com TRA-1/Rafael os tópicos, a versão do schema B2 e a aceitação dos campos opcionais `timestamp_monotonic_raw_ns` e `timestamp_monotonic_raw_clock` pelos consumidores.
3. **Kafka integrado:** validar a publicação real e a confirmação de entrega em broker autorizado, sem enviar pixels ao Kafka.
4. **Consumidor real de vídeo:** conectar I1/P6 ou outro componente do ODS ao SHM. O leitor de teste já recebe um pacote RAW10, mas isso **não substitui** a homologação com o consumidor real.
5. **Duas câmeras:** validar IMX519 e IMX477 simultaneamente com sockets separados e métricas independentes.
6. **Estabilidade:** executar testes prolongados de FPS, memória, backpressure, reconexão e recuperação após falhas.
7. **Descontinuidade inicial ocasional:** em uma execução do `main.py`, os timestamps do driver saltaram **83,331 ms** entre os frames 1 e 2, enquanto as leituras ficaram próximas de 17 ms. O FPS médio relatado chegou a aproximadamente 58 FPS, mas o teste isolado de 120 frames com TSC e SHM marcou 60 FPS. **Não foi comprovada perda contínua de 2 FPS; o problema não bloqueia a entrega funcional atual.**
8. **Versionamento:** revisar, testar e publicar os arquivos modificados; incluir as instruções de compilação nativa e os novos testes.

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

## 12. Preparação para compartilhar o repositório

As alterações atuais incluem código-fonte da biblioteca TSC, wrapper Python, script de compilação, campos opcionais nos contratos SHM e B2, testes e o leitor com seleção de câmera por variável de ambiente.

```bash
# Conferir arquivos modificados e possíveis artefatos locais
git status --short

# Conferir formatação básica
git diff --check

# Executar os testes atuais
python -m unittest discover -s tests -p 'test_*.py' -v

# Conferir arquivos a serem enviados antes de commitar
git diff --stat
```

Revise e versione os arquivos alterados, incluindo `README.md`, `scripts/build_tsc_clock.sh`, `src/tsc_clock.c`, `src/tsc_converter.py` e os testes novos. Não inclua a biblioteca compilada `build/libp4_tsc_clock.so`, ambientes virtuais, sockets, quadros RAW ou credenciais. **As funcionalidades descritas como locais e testadas não devem ser anunciadas como publicadas no GitHub até o push ser concluído.**

---

**Resumo para integração:** o P4 captura vídeo RAW10 das duas CSI **individualmente** e publica pacotes identificados P4R1 no SHM local da Jetson. Um processo de teste recebeu e interpretou um pacote real da IMX477. A normalização opcional TSC → `CLOCK_MONOTONIC_RAW` já está implementada e documentada, preservando os timestamps originais. **A conversão para uma imagem visualizável, a homologação do contrato com consumidores e P5, as duas câmeras em paralelo e a entrega Kafka fim a fim ainda dependem de validação.**
