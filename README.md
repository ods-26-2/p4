# SIS-2 — P4: Fonte de Vídeo

Componente **P4 — Fonte de Vídeo**, integrante do SIS-2 (Sinal e Dispositivo) do projeto ODS.

O P4 captura quadros de uma câmera, preserva as informações temporais e de sequência disponibilizadas pelo driver e entrega **vídeo** e **metadados** por canais distintos:

- **GStreamer + memória compartilhada (SHM):** transmissão local de imagens para o consumidor de vídeo, como o I1.
- **Apache Kafka:** publicação de eventos de início de sessão e de metadados dos quadros.

O projeto também possui um **modo diagnóstico**, usado para verificar a captura sem depender de GStreamer/SHM ou Kafka. Esse é o modo previsto para o primeiro teste com a IMX519 na Jetson.

> **Estado atual:** captura, modo diagnóstico, transmissão SHM e publicação Kafka foram testados com a webcam **EMEET SmartCam C60E 4K no WSL2**. A captura das câmeras **Arducam IMX519 e IMX477 na Jetson ainda não foi validada**. A correspondência exata entre os quadros recebidos pelo I1 e seus eventos Kafka também está pendente.

## 1. Responsabilidades e arquitetura

O componente é responsável por:

1. Inicializar uma fonte de vídeo e capturar seus buffers.
2. Representar cada quadro por meio de `Frame` e gerar seus metadados em `FrameMetadata`.
3. Preservar, quando disponíveis, número de sequência e timestamp fornecidos pelo driver V4L2.
4. Disponibilizar os quadros ao consumidor por GStreamer/SHM.
5. Publicar eventos leves no Kafka sem enviar os pixels pelo broker.
6. Oferecer diagnóstico de captura, permitindo investigar sensores e drivers isoladamente.

Fluxo implementado para a webcam EMEET:

```text
EMEET (USB) ── V4L2 / linuxpy ── Frame ── P4
                                        │
                  ┌─────────────────────┴──────────────────────┐
                  │                                            │
           SHMPublisher                                 KafkaPublisher
        MJPEG → JPEG decoder → BGR                  Eventos JSON por quadro
                  │                                            │
       GStreamer shmsink                            ods.session.started
                  │                                 ods.p4.frame
        /tmp/p4_video_shm                                     │
                  │                                   Consumidores Kafka
       shmsrc → I1 (simulado)
```

**Importante:** a câmera EMEET entrega **MJPEG** ao `V4L2Source`, mas a pipeline SHM transmite **BGR** após decodificação. O campo `format` dos metadados atualmente descreve o formato **capturado**, não o formato de saída SHM.

A implementação atual da `SHMPublisher` aceita **MJPEG** e usa `jpegdec`; portanto, o **modo completo não está pronto para transmitir diretamente o Bayer RAW10 da IMX519**. Primeiro será validada a captura no modo diagnóstico; a adaptação da transmissão virá depois.

A correção da distorção da lente **não integra as responsabilidades atuais do P4**. Quando necessária, deverá ser executada por componentes posteriores a partir dos parâmetros de calibração apropriados.

## 2. Estado de implementação

| Recurso | Estado |
|---|---|
| Captura de quadros da EMEET via V4L2 | Validado no WSL2 |
| Leitura de resolução, formato, sequência e timestamps | Validado com EMEET |
| Modo diagnóstico independente de SHM/Kafka | Validado com EMEET (30 quadros) |
| Transmissão de vídeo GStreamer/SHM | Validada com EMEET |
| Recepção por processo Python simulando I1 | Validada (30 quadros, 640 × 480) |
| Publicação de `ods.p4.frame` no Kafka | Validada (150 mensagens no teste integrado) |
| Publicação de `ods.session.started` | Validada |
| Conversão opcional do timestamp para UTC | Validada como apresentação aproximada |
| Correlação inequívoca de cada buffer SHM com o `frame_id` Kafka | Pendente |
| Captura IMX519 / IMX477 na Jetson | Pendente |
| SHM para formatos RAW10 / câmeras CSI | Pendente |
| Ensaios prolongados de perdas, memória e recuperação de falhas | Pendentes |

Esses resultados descrevem os testes realizados; não representam homologação de desempenho ou confiabilidade em produção.

## 3. Estrutura do projeto

Arquivos principais da implementação atual:

```text
P4/
├── src/
│   ├── __init__.py
│   ├── main.py             # Seleção de câmera, modo e execução
│   ├── config.py           # Configurações EMEET, IMX519 e IMX477
│   ├── source.py           # Interface VideoSource
│   ├── v4l2_source.py      # Captura V4L2 via linuxpy
│   ├── webcam_source.py    # Alternativa de captura via OpenCV
│   ├── frame.py            # Estrutura Frame
│   ├── metadata.py         # Estrutura FrameMetadata
│   ├── p4.py               # Sessão, leitura e processamento dos quadros
│   ├── clock.py            # Conversão aproximada monotônico → UTC
│   ├── events.py           # Montagem dos eventos de metadados
│   ├── shm_publisher.py    # Publicação de vídeo via GStreamer/SHM
│   └── kafka_publisher.py  # Produtor de eventos Kafka
├── tests/
│   └── shm_reader.py       # Leitor SHM que simula o consumidor I1
├── .gitignore
├── requirements.txt
└── README.md
```

Outros testes ou diretórios antigos podem estar presentes localmente. A pasta `src_old/` é um backup da implementação anterior e **não faz parte da aplicação atual**.

## 4. Configurações

### 4.1. Câmeras — `src/config.py`

As configurações ficam em `CAMERAS`, com uma entrada para cada fonte:

| Câmera | Finalidade atual | Situação |
|---|---|---|
| `emeet` | Desenvolvimento e integração no WSL2 | Habilitada e validada |
| `imx519` | Primeira câmera CSI para testes na Jetson | Configuração preliminar; captura pendente |
| `imx477` | Segunda câmera CSI planejada para a Jetson | Configuração incompleta; desabilitada |

Cada entrada contém `source_id`, `device`, `width`, `height`, `fps`, `pixel_format`, `raw`, `socket_path` e `enabled`.

Na EMEET, os valores testados foram `/dev/video0`, **640 × 480**, `MJPG` e `raw=False`.

Para a IMX519, a configuração inicial de diagnóstico utiliza **1920 × 1080** e **`RG10`** (Bayer RAW10), com dispositivo inicialmente indicado como `/dev/video0`. Esses parâmetros foram anunciados anteriormente pelo driver, **mas a entrega real dos buffers ainda precisa ser confirmada**. Os caminhos `/dev/videoX` podem mudar; sempre verificar na Jetson.

Os sockets SHM são configuráveis por fonte. **A existência de duas entradas no dicionário não significa que a captura simultânea das duas câmeras já esteja implementada**: o `main.py` atual seleciona uma fonte por execução.

### 4.2. Execução — `src/main.py`

As variáveis no início do arquivo controlam o comportamento:

```python
CAMERA_SELECIONADA = "emeet"       # "emeet", "imx519" ou "imx477"
MODO_DIAGNOSTICO = True         # True: somente captura
LIMITE_QUADROS = 30             # Usado no modo diagnóstico
CONVERTER_TIMESTAMP_UTC = False # Adiciona campo UTC sem remover timestamp original
ATIVAR_KAFKA = True             # Usado somente no modo completo
```

- **Diagnóstico (`True`):** captura `LIMITE_QUADROS`, mostra periodicamente formato, bytes, timestamp, origem e FPS; não inicializa SHM nem Kafka. Ainda imprime o evento local `ods.session.started`.
- **Completo (`False`):** captura continuamente, envia vídeo por SHM e, se `ATIVAR_KAFKA=True`, publica eventos no Kafka. O pipeline atual requer MJPEG.
- **UTC (`True`):** adiciona `captured_at_utc` à mensagem, preservando o inteiro `timestamp` em nanossegundos.

O endereço Kafka é lido da variável de ambiente `P4_KAFKA_BOOTSTRAP_SERVERS`. Quando o Kafka estiver ativado no modo completo, ela deverá estar configurada.

## 5. Dependências

### 5.1. Python

O `requirements.txt` da implementação atual deve incluir:

```text
linuxpy==0.25.0
confluent-kafka==2.16.1
numpy
opencv-python
```

As versões fixadas de `linuxpy` e `confluent-kafka` correspondem ao ambiente WSL testado. **Não foi comprovada ainda a compatibilidade dessas versões com o Python e o sistema ARM64 da Jetson.** Para o primeiro diagnóstico CSI, a dependência principal é `linuxpy`.

### 5.2. Ubuntu / GStreamer

Para captura e teste SHM no Ubuntu/WSL2:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip \
  python3-gi gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
  gstreamer1.0-tools gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
  v4l-utils usbutils
```

O pacote `gstreamer1.0-plugins-bad` disponibilizou os elementos `shmsink` e `shmsrc` no ambiente testado. As bibliotecas `gi`/GStreamer são providas pelo sistema e não apenas pelo `pip`.

Criar um ambiente virtual na raiz do projeto:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`--system-site-packages` permite que o ambiente virtual encontre o `gi` instalado pelo Ubuntu. Na Jetson, o procedimento de instalação deve ser ajustado conforme a versão do Python e as bibliotecas disponíveis no JetPack.

Verificações úteis:

```bash
python -c "import linuxpy; print('linuxpy OK')"
python -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print(Gst.version_string())"
gst-inspect-1.0 shmsink
gst-inspect-1.0 shmsrc
```

## 6. Conectar a EMEET ao WSL2

O Windows precisa compartilhar a câmera USB com o Linux do WSL2 por meio do **usbipd**. O procedimento pode precisar ser repetido após reiniciar o computador ou desconectar o dispositivo.

**No PowerShell do Windows:**

```powershell
usbipd list
```

Encontre a câmera EMEET e seu `BUSID` atual. No ambiente de desenvolvimento, o dispositivo foi identificado como `328f:00f3`. **O BUSID não é fixo**: use o exibido no seu computador.

Se necessário, no PowerShell **como administrador**, compartilhe o dispositivo (substitua `BUSID`):

```powershell
usbipd bind --busid BUSID
```

Depois conecte ao WSL:

```powershell
usbipd attach --wsl --busid BUSID
```

**No Ubuntu/WSL2:**

```bash
lsusb
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Confirme qual `/dev/videoX` corresponde à captura da EMEET. No ambiente testado foi `/dev/video0`, mas a numeração pode mudar. Se necessário, atualize `device` em `src/config.py`.

Se houver erro de permissão, verifique o grupo do dispositivo (`ls -l /dev/video0`). Em configurações usuais, o usuário precisa pertencer ao grupo `video`; uma mudança de grupo pode exigir novo login.

## 7. Executar o P4

Todos os comandos a seguir devem ser executados na raiz do repositório, com o ambiente virtual ativado.

### 7.1. Modo diagnóstico — somente captura

Em `src/main.py`:

```python
CAMERA_SELECIONADA = "emeet"
MODO_DIAGNOSTICO = True
LIMITE_QUADROS = 30
```

Execute:

```bash
python -m src.main
```

Exemplo de saída observada com a EMEET:

```text
P4 iniciado | Câmera: emeet | Modo: DIAGNÓSTICO
{"event": "ods.session.started", "source_id": "emeet", "session_id": "..."}
Frame 0 | 640x480 | Formato: MJPG | Tamanho: 22532 bytes | Timestamp: 10731128077000 ns | Origem: driver_soe | FPS: None
Frame 10 | 640x480 | Formato: MJPG | ... | FPS: 15.64
Frame 20 | 640x480 | Formato: MJPG | ... | FPS: 15.63
Diagnóstico finalizado com sucesso!
Recursos liberados.
```

O programa finaliza automaticamente após o número configurado de quadros. Esse modo é a primeira etapa para testar a IMX519 na Jetson.

### 7.2. Modo completo — SHM + Kafka

Este modo **já foi validado com a EMEET**, não com RAW10 das câmeras CSI.

Em `src/main.py`:

```python
CAMERA_SELECIONADA = "emeet"
MODO_DIAGNOSTICO = False
ATIVAR_KAFKA = True
```

No terminal do P4:

```bash
source .venv/bin/activate
export P4_KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
python -m src.main
```

`localhost:9092` é o broker **local de desenvolvimento** descrito na seção seguinte; não é o endereço definitivo da infraestrutura da equipe. Para utilizar somente SHM, defina `ATIVAR_KAFKA = False`.

Em outro terminal, com o P4 ainda em execução, inicie o leitor que simula o I1:

```bash
source .venv/bin/activate
python tests/shm_reader.py
```

O leitor deve receber 30 quadros, informar as dimensões e salvar `i1_frame.jpg` para inspeção visual. O leitor usa GStreamer diretamente pelo Python (`gi`), sem depender de OpenCV compilado com suporte a `CAP_GSTREAMER`.

Encerre o P4 com `Ctrl+C`.

## 8. Kafka local para desenvolvimento

Instalar somente `confluent-kafka` **não instala o broker**. Nos testes, o broker foi executado por Docker no WSL2, com a imagem `apache/kafka:4.4.0`.

### 8.1. Inicializar o broker

Com Docker instalado e ativo:

```bash
sudo service docker start
sudo docker run -d --name p4-kafka -p 127.0.0.1:9092:9092 apache/kafka:4.4.0
```

O comando `docker run` cria o contêiner **uma vez**. Se ele já existir e estiver parado, reutilize-o:

```bash
sudo docker start p4-kafka
```

Verifique:

```bash
sudo docker ps
```

A porta foi exposta somente no endereço de loopback do computador de desenvolvimento. Isso não configura acesso de outras máquinas ao broker.

### 8.2. Criar os tópicos

```bash
sudo docker exec p4-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic ods.session.started \
  --partitions 1 --replication-factor 1

sudo docker exec p4-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic ods.p4.frame \
  --partitions 1 --replication-factor 1

sudo docker exec p4-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```

Os tópicos esperados são `ods.session.started` e `ods.p4.frame`.

### 8.3. Consumir mensagens e confirmar a publicação

Com o P4 em modo completo e Kafka ativado:

```bash
sudo docker exec p4-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ods.p4.frame --max-messages 5
```

Para conferir eventos de início de sessão:

```bash
sudo docker exec p4-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ods.session.started --max-messages 1
```

Sem `--from-beginning`, os comandos aguardam eventos novos; inicie o consumidor antes de iniciar a próxima sessão do P4. Para investigar eventos antigos, acrescente `--from-beginning`.

O envio do produtor é **assíncrono**: colocar uma mensagem na fila não equivale a receber uma confirmação de entrega. O código atual trata callbacks de erro e tenta finalizar envios pendentes ao encerrar, mas ainda falta monitoramento sistemático de perdas e recuperação de falhas.

## 9. Frames, timestamps e metadados

### 9.1. Estrutura `Frame`

`src/frame.py` representa cada quadro por:

| Campo | Significado |
|---|---|
| `data` | Bytes capturados do dispositivo (por exemplo, JPEG comprimido na EMEET) |
| `width`, `height` | Dimensões do quadro |
| `pixel_format` | Formato informado pela captura V4L2 |
| `timestamp_ns` | Timestamp em unidade de nanossegundos |
| `frame_index` | Número sequencial fornecido pelo buffer V4L2 no código atual |
| `timestamp_origin` | Origem/semântica conhecida do timestamp |

### 9.2. Metadados e eventos

`src/p4.py` organiza `FrameMetadata`, incluindo `source_id`, `session_id`, `frame_index`, dimensões, formato, FPS, indicador `raw` e timestamps capturado/recebido.

O evento de sessão é enviado ao tópico `ods.session.started`:

```json
{
  "event": "ods.session.started",
  "source_id": "emeet",
  "session_id": "identificador-da-sessao"
}
```

Os eventos por quadro são enviados ao tópico `ods.p4.frame`:

```json
{
  "schema": "ods.p4.frame",
  "producer": "P4",
  "source_id": "emeet",
  "session_id": "identificador-da-sessao",
  "payload": {
    "frame_id": 30,
    "timestamp": 10731799672000,
    "width": 640,
    "height": 480,
    "format": "MJPG",
    "fps": 15.64,
    "raw": false
  }
}
```

O `session_id` é gerado por execução e permite relacionar o início da sessão aos seus eventos de quadro. O Kafka recebe **um evento por quadro** no modo completo, enquanto o terminal imprime apenas um evento a cada 30 quadros.

`fps` é calculado a partir da diferença entre timestamps consecutivos quando não há FPS fixo configurado; pode ser `null` no primeiro quadro. O indicador `raw` distingue imagens brutas de sensor de formatos como o MJPEG da EMEET.

### 9.3. Semântica temporal

- O `timestamp` publicado é um inteiro em **nanossegundos**, derivado do timestamp do buffer V4L2 quando seu relógio é identificado como monotônico.
- Na EMEET, o driver apresentou `driver_soe` (*start of exposure*). Em outros drivers pode haver timestamp associado ao fim do quadro (*EOF*) ou outra origem.
- A implementação converte o valor V4L2 de segundos e microssegundos para **unidade de nanossegundos**; isso **não cria precisão física de nanossegundos**.
- Um timestamp monotônico **não é diretamente uma data UTC**. A opção `CONVERTER_TIMESTAMP_UTC=True` acrescenta `captured_at_utc` usando uma correspondência aproximada entre os relógios do sistema, preservando `payload.timestamp`.
- Quando o relógio do driver não é reconhecido, a captura usa uma marca de recebimento; ela não deve ser apresentada como instante físico de exposição.

A validação dos timestamps das câmeras CSI continua necessária.

### 9.4. Limitação de sincronização entre SHM e Kafka

O SHM transporta os pixels e o Kafka transporta os metadados. **O leitor `tests/shm_reader.py` ainda não recupera o `frame_id` original do buffer enviado pelo P4.** Seu contador de quadros é local.

Portanto, **a transmissão simultânea já foi validada, mas a associação exata imagem ↔ evento Kafka ainda não foi implementada**. A solução precisa ser alinhada com o contrato do consumidor I1, especialmente para suportar início tardio e descartes de quadros.

## 10. Primeiro teste da IMX519 na Jetson (via SSH)

**Objetivo inicial:** confirmar que o sensor e o driver entregam quadros ao V4L2 antes de depender da aplicação Python, SHM ou Kafka.

### 10.1. Conferir a câmera e o dispositivo

Após conectar-se à Jetson pela rede autorizada:

```bash
ssh sys2@ods-pc
```

O nome `ods-pc` deve ser acessível na rede usada; caso contrário, utilizar o endereço SSH fornecido pela equipe.

Na Jetson:

```bash
v4l2-ctl --list-devices
ls -l /dev/video*
v4l2-ctl -d /dev/video0 --list-formats-ext
```

**Não presumir que `/dev/video0` seja sempre a IMX519.** Identificar o nó correto antes de continuar.

### 10.2. Testar streaming sem o P4

Se `/dev/video0` corresponder à IMX519 e anunciar `1920×1080` com `RG10`:

```bash
timeout 15s v4l2-ctl \
  -d /dev/video0 \
  --set-fmt-video=width=1920,height=1080,pixelformat=RG10 \
  --stream-mmap \
  --stream-count=5 \
  --verbose
```

O comando tenta capturar cinco buffers e limita a duração da tentativa. **A enumeração de formatos não comprova que o sensor esteja transmitindo:** em verificações anteriores, a câmera foi reconhecida, mas o streaming apresentou timeout. Também houve indícios de problemas com driver, overlay e comunicação I²C dos sensores.

Se o V4L2 não entregar buffers, investigar primeiro a câmera, a alimentação/conexões e a configuração do driver/overlay. Não alterar a configuração de boot da Jetson apenas para fazer o teste Python.

### 10.3. Testar a aplicação no modo diagnóstico

Depois de confirmar a captura via `v4l2-ctl`:

1. Fazer `git pull` da versão revisada do P4 na Jetson, no repositório correto.
2. Criar um ambiente Python compatível e instalar `linuxpy` (a compatibilidade da versão com o Python da Jetson ainda precisa ser verificada).
3. Conferir `device`, `width`, `height` e `pixel_format` da IMX519 no `src/config.py`.
4. Em `src/main.py`, selecionar `CAMERA_SELECIONADA = "imx519"` e `MODO_DIAGNOSTICO = True`.
5. Executar:

```bash
python -m src.main
```

O resultado esperado é a captura e exibição de informações sobre os buffers, sem inicializar SHM nem Kafka. Os valores reais, especialmente tamanho do buffer, flags, timestamps e FPS, deverão ser observados na Jetson; não são resultados já validados.

**A IMX477 será tratada depois da IMX519**, confirmando primeiro seu driver e dispositivo próprio. O funcionamento simultâneo das duas fontes ainda precisa ser implementado e testado.

## 11. Problemas conhecidos e próximos passos

- **IMX519/IMX477:** validar driver, Device Tree/overlays e entrega real de buffers V4L2 na Jetson.
- **SHM para CSI:** adaptar a pipeline para o formato efetivamente recebido e determinar a representação que será consumida pelo I1.
- **Sincronização:** estabelecer uma associação recuperável entre imagem SHM e `frame_id`/`session_id` Kafka.
- **Duas câmeras:** implementar e testar captura simultânea, quando o contrato do sistema exigir.
- **Confiabilidade:** medir drops, taxa de quadros, atraso, uso de memória e comportamento diante de falhas do Kafka ou de desconexão do consumidor.
- **Integração:** validar os esquemas dos eventos e os requisitos temporais com a equipe.

## 12. Controle de versão

A pasta `.venv/`, o backup local `src_old/`, imagens temporárias (como `i1_frame.jpg`), logs e vídeos de testes não devem ser incluídos no Git. Consulte `.gitignore` antes do commit.

Para revisar as alterações:

```bash
git status --short
git diff --stat
```

Após conferir quais arquivos devem ser versionados, registrar a versão e enviar ao repositório remoto. Na Jetson, confirmar antes se a árvore de trabalho contém alterações locais importantes, para não sobrescrevê-las inadvertidamente ao atualizar o código.

---

**Resumo:** a implementação atual do P4 já captura vídeo real da EMEET com timestamps do V4L2, dispõe de modo diagnóstico independente, transmite BGR via GStreamer/SHM e publica metadados e eventos de sessão no Kafka. O próximo marco é **capturar quadros reais da IMX519 na Jetson**, começando pela validação do driver e pelo modo diagnóstico; posteriormente, adaptar a transmissão CSI, integrar a IMX477 e resolver a sincronização exata com o I1.
