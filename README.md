# SIS-2 — P4: Fonte de Vídeo

Componente **P4 — Fonte de Vídeo**, integrante do SIS-2 (Sinal e Dispositivo) do projeto ODS.

O P4 captura quadros de uma câmera, preserva as informações temporais e de sequência disponibilizadas pelo driver e entrega **vídeo** e **metadados** por canais distintos:

- **GStreamer + memória compartilhada (SHM):** transmissão local de imagens para o consumidor de vídeo, como o I1.
- **Apache Kafka:** publicação de eventos de início de sessão e de metadados dos quadros.

O projeto também possui um **modo diagnóstico**, usado para verificar a captura sem depender de GStreamer/SHM ou Kafka. Esse é o modo previsto para o primeiro teste com a IMX519 na Jetson.

> **Estado em 04/11/2026:** o fluxo principal foi validado com a webcam **EMEET SmartCam C60E 4K no WSL2**: captura V4L2, timestamps do driver, métricas, transmissão GStreamer/SHM e eventos Kafka. Há **5 testes automatizados aprovados**. A Jetson já executa o código e reconhece um dispositivo V4L2, mas **ainda não entregou quadros das câmeras CSI**; foram identificadas inconsistências no driver/overlay. A associação exata dos quadros SHM aos eventos Kafka e os testes de simultaneidade de duas câmeras continuam pendentes.

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

| Recurso | Estado / evidência |
|---|---|
| Captura EMEET por V4L2 e `linuxpy` | Validada no WSL2 (640 × 480, MJPEG) |
| Origem e numeração dos timestamps | Observada na EMEET (`driver_soe`); não validada nas IMX |
| Modo diagnóstico | Validado: 30 quadros sem SHM nem Kafka |
| Métricas de captura | Contagem de quadros, saltos de sequência e FPS médio; validadas com EMEET e simulações |
| Saída GStreamer/SHM | 69 quadros aceitos pelo `appsrc` no último ensaio de encerramento; leitor I1 simulado recebeu 30 quadros em ensaio separado |
| Kafka | 70/70 eventos confirmados no último ensaio de encerramento (69 frames + 1 sessão) |
| Contagem de falhas de Kafka | Implementada; queda do broker durante captura observada, mas o novo encerramento sob falha ainda não foi revalidado |
| Encerramento do SHM | Validado: `release()` fecha a pipeline e o GStreamer remove o socket na execução normal |
| Evento de início após o primeiro quadro | Validado com EMEET e com fonte simulada que falha antes de capturar |
| Seleção de câmera e modo por variáveis de ambiente | Validada com `P4_CAMERA=emeet` e ambos os modos |
| Isolamento lógico de duas fontes | Validado sequencialmente em testes unitários; execução simultânea não validada |
| Testes automatizados | **5 testes `unittest` aprovados** |
| Associação exata imagem SHM ↔ evento Kafka | Pendente; exige contrato com o I1 |
| Captura IMX519 / IMX477 na Jetson | Pendente: nenhum quadro real recebido |
| Pipeline SHM para Bayer RG10 / RAW10 | Pendente: publicador atual aceita MJPEG |
| Testes prolongados de estabilidade, uso de memória e falhas | Pendentes |

**Limite das evidências:** `push-buffer = OK` comprova aceitação pelo `appsrc`, não recebimento pelo I1. Uma confirmação Kafka comprova entrega de mensagem ao broker, não correlação com a imagem. Os ensaios com a EMEET não homologam o desempenho na Jetson.

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
│   ├── capture_metrics.py  # Quadros, saltos estimados e FPS médio
│   ├── clock.py            # Conversão aproximada monotônico → UTC
│   ├── events.py           # Montagem dos eventos de metadados
│   ├── shm_publisher.py    # Publicação de vídeo via GStreamer/SHM
│   └── kafka_publisher.py  # Produtor de eventos Kafka
├── tests/
│   ├── shm_reader.py       # Leitor SHM que simula o consumidor I1
│   ├── test_p4.py          # Testes de sessão, FPS e isolamento das fontes
│   └── test_capture_metrics.py # Teste de saltos na numeração
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

Os sockets SHM são configuráveis por fonte. O `main.py` seleciona **uma fonte por processo**. Duas instâncias do P4 já foram testadas em sequência, com IDs e métricas independentes; **a execução simultânea de dois processos com câmeras CSI ainda não foi validada**.

### 4.2. Execução — `src/main.py`

A câmera e o modo agora podem ser escolhidos pelo **terminal**, sem editar o Python:

```python
CAMERA_SELECIONADA = os.getenv("P4_CAMERA", "emeet")
MODO_DIAGNOSTICO = (
    os.getenv("P4_MODO_DIAGNOSTICO", "true").lower() == "true"
)
LIMITE_QUADROS = 30
CONVERTER_TIMESTAMP_UTC = False
ATIVAR_KAFKA = True
```

- **Diagnóstico:** captura um número limitado de quadros, exibe formato, timestamp e FPS, sem inicializar SHM/Kafka. O evento de sessão é apenas exibido localmente.
- **Completo:** captura continuamente, envia vídeo pelo SHM e, se ativado, publica metadados no Kafka. A entrada atual da pipeline exige MJPEG.
- **UTC:** acrescenta um timestamp UTC aproximado aos eventos, sem alterar o valor original monotônico.

O broker é definido com `P4_KAFKA_BOOTSTRAP_SERVERS`, obrigatório no modo completo quando Kafka está ativado. **Uma sessão só é anunciada depois de receber o primeiro quadro**; isso não equivale à confirmação da entrega pelo Kafka.

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

Todos os comandos são executados na raiz do projeto com a `.venv` ativa. Em ambos os modos a EMEET deve estar acessível no WSL2.

### 7.1. Modo diagnóstico — somente captura

```bash
P4_CAMERA=emeet P4_MODO_DIAGNOSTICO=true python -m src.main
```

O padrão é 30 quadros. Uma saída real do desenvolvimento foi:

```text
P4 iniciado | Câmera: emeet | Modo: DIAGNÓSTICO
{"event": "ods.session.started", "source_id": "emeet", "session_id": "..."}
Frame 0 | 640x480 | Formato: MJPG | ... | Origem: driver_soe | FPS: None
Frame 10 | 640x480 | Formato: MJPG | ... | FPS: 15.66
Frame 20 | 640x480 | Formato: MJPG | ... | FPS: 15.63
Diagnóstico finalizado com sucesso!
Métricas de captura: {"frames_recebidos": 30, "frames_perdidos_estimados": 0, "fps_medio": 15.11}
Recursos de captura liberados.
```

A taxa de quadros e os timestamps variam entre execuções. O diagnóstico é a primeira modalidade a validar com uma câmera CSI real, **depois** de corrigidos driver, overlay e captura V4L2 na Jetson.

### 7.2. Modo completo — SHM + Kafka

Com o broker local em funcionamento:

```bash
export P4_KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
P4_CAMERA=emeet P4_MODO_DIAGNOSTICO=false python -m src.main
```

No segundo terminal, enquanto o P4 está rodando:

```bash
python tests/shm_reader.py
```

O leitor simula o I1, recebe 30 quadros via `shmsrc`, informa a resolução e salva `i1_frame.jpg`. O seu contador `i` **não é** o `frame_id` original do P4. Encerre o publicador com `Ctrl+C` **uma vez**; o `publisher.release()` encerra a pipeline e o `shmsink` remove o socket normalmente.

Exemplo real do relatório de encerramento no modo completo:

```text
Métricas de captura: {"frames_recebidos": 69, "frames_perdidos_estimados": 0, "fps_medio": 14.97}
Métricas de transmissão: {"frames_aceitos_appsrc": 69, "bytes_aceitos_appsrc": 1774572}
Kafka | Enfileiradas: 70 | Confirmadas: 70 | Falhas de entrega: 0 | Falhas de envio: 0 | Pendentes: 0
Recursos de captura liberados.
```

- `frames_recebidos`: quantidade de buffers recebidos da câmera.
- `frames_perdidos_estimados`: lacunas na numeração do driver; não mede todas as perdas possíveis.
- `fps_medio`: taxa média entre o primeiro e o último timestamp monotônico válido.
- `frames_aceitos_appsrc`: buffers aceitos pela **entrada** do GStreamer; não prova entrega ao I1.
- `bytes_aceitos_appsrc`: soma dos bytes MJPEG na entrada, não do vídeo BGR transmitido.
- `Confirmadas`: mensagens Kafka confirmadas pelo broker.

**Socket ocupado:** o publicador evita iniciar silenciosamente em um caminho alternativo quando `/tmp/p4_video_shm` já existe. Se a execução anterior caiu abruptamente, verifique a existência de outro P4 e se há listener com `ss -xlpn | grep -F '/tmp/p4_video_shm'`. Apenas se tiver certeza de que o socket está abandonado, remova o arquivo antigo e reinicie. Não remova sockets de processos em uso.

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

O envio do produtor é **assíncrono**: enfileirar uma mensagem não equivale à entrega. O `KafkaPublisher` conta mensagens enfileiradas, confirmadas, falhas de entrega, falhas de enfileiramento e mensagens ainda pendentes ao encerrar. Usa `on_delivery`, fila limitada, timeout de mensagem e idempotência do produtor; **não garante persistência local nem entrega exata ponta a ponta**. A queda do broker durante captura já foi observada, mas o encerramento após falha, depois das correções, ainda precisa ser testado novamente. O `flush()` tem espera limitada.

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

O `session_id` é gerado por instância do P4 e permite relacionar o início da sessão aos eventos dos quadros. O evento `ods.session.started` é gerado **após a primeira captura bem-sucedida**, antes de entregar o quadro ao consumidor. O Kafka recebe **um evento por quadro** no modo completo, enquanto o terminal imprime apenas um evento a cada 30 quadros.

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

## 10. Integração com a Jetson: diagnóstico realizado e retomada presencial

**Estado em 04/11/2026:** foi estabelecido acesso SSH à Jetson, o repositório local está disponível e o ambiente Python com `linuxpy` foi usado para executar o P4. O dispositivo `/dev/video0` aparece no V4L2, mas **ainda não forneceu nenhum quadro real**.

### 10.1. Evidências encontradas

- O `/dev/video0` apareceu como `vi-output, imx519 9-001a`, anunciando `RG10` e resoluções como 1920 × 1080 e 4656 × 3496. **Anunciar um formato não prova captura**.
- Ao solicitar 1920 × 1080, o driver retornou 4656 × 3496; as tentativas de streaming não entregaram quadros antes do timeout.
- O kernel registrou `imx519 9-001a: imx519_board_setup: invalid sensor model id: 477`: o driver da IMX519 encontrou uma identificação de sensor 477 no barramento I²C correspondente.
- Também apareceu `imx519 10-001a: imx519_board_setup: error during i2c read probe (-121)`, indicando problema de comunicação com outro dispositivo.
- A entrada de boot ativa utiliza overlay **`tegra234-p3767-camera-p3768-imx519-dual.dtbo`**, preparado para **duas IMX519**, enquanto o conjunto pretendido é IMX519 + IMX477.
- Ao interromper uma tentativa de captura sem quadros, o kernel também registrou avisos de liberação de buffers `videobuf2` no driver. Por isso, suspenderam-se tentativas repetidas até verificar a configuração física e os drivers.

Essas evidências demonstram **incompatibilidade na configuração atual**, mas **não comprovam qual cabo está conectado a qual porta** nem se há defeito físico. Um overlay misto foi preparado como candidato, mas **não foi ativado** e seu mapeamento precisa ser conferido com o hardware antes de aplicá-lo.

### 10.2. Plano de retomada com acesso físico

1. **Desligar totalmente** a Jetson antes de manusear cabos CSI e identificar fisicamente as câmeras IMX519 e IMX477 e suas portas.
2. Inspecionar orientação/encaixe dos cabos e registrar o mapeamento real de conectores e barramentos.
3. Conferir o overlay e os drivers apropriados para a configuração mista; manter backup e possibilidade de recuperação antes de alterar boot ou reiniciar.
4. Validar o reconhecimento dos sensores no kernel e os nós V4L2, sem presumir que `/dev/video0` seja sempre a IMX519:

```bash
v4l2-ctl --list-devices
ls -l /dev/video*
v4l2-ctl -d /dev/video0 --list-formats-ext
sudo dmesg | grep -Ei 'imx519|imx477|i2c|tegra-camrtc'
```

5. Somente quando driver/overlay estiverem coerentes, tentar uma captura curta via `v4l2-ctl` com formato e resolução **efetivamente negociados**.
6. Quando V4L2 entregar quadros, atualizar o código na Jetson após confirmar que não há mudanças locais importantes e executar o P4 no diagnóstico:

```bash
P4_CAMERA=imx519 P4_MODO_DIAGNOSTICO=true venv/bin/python -m src.main
```

O comando acima pressupõe que a IMX519 foi identificada corretamente, sua entrada em `src/config.py` foi revisada e a `venv/` da Jetson continua disponível. A IMX477 permanece desabilitada até confirmação do driver e de sua configuração. **Não executar o modo completo com RAW10 usando o `SHMPublisher` atual, que aceita MJPEG.**

## 11. Problemas conhecidos e próximos passos

- **Jetson / sensores:** conferir conexões, driver, I²C, overlay e recepção real de buffers V4L2 antes de testar o P4 com CSI.
- **Pipeline CSI:** adaptar SHM para o formato efetivamente recebido (Bayer RG10 ou formato convertido), com contrato de saída acordado com o I1.
- **Sincronização exata:** definir como o I1 associa uma imagem SHM ao `frame_id` e `session_id` do Kafka; a ordem relativa dos dois canais não é garantia suficiente.
- **Duas câmeras:** cada processo já pode selecionar sua fonte; captura simultânea, recursos e comportamento sob falhas ainda exigem teste.
- **Confiabilidade:** revalidar encerramento após indisponibilidade do broker; testar queda/desconexão do consumidor SHM, estabilidade prolongada, drops, atrasos e uso de memória.
- **Integração:** confirmar tópicos, esquema de metadados, timestamps e interface com os responsáveis pelos consumidores.

### 11.1. Testes automatizados sem câmera

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Foram aprovados **5 testes** em 04/11/2026:

1. Falha ao capturar o primeiro quadro não dispara `ods.session.started`.
2. Evento de sessão é emitido uma única vez e antes da entrega dos frames ao consumidor.
3. Timestamps e FPS calculados são coerentes com timestamps conhecidos.
4. A detecção de saltos reconhece lacunas na sequência de identificadores.
5. Duas instâncias do P4 conservam sessões, origens e métricas independentes, **em teste sequencial**.

A suíte não substitui os ensaios com câmera real nem testes completos do broker e do SHM.

## 12. Controle de versão

A pasta `.venv/`, o backup local `src_old/`, imagens temporárias (como `i1_frame.jpg`), logs e vídeos de testes não devem ser incluídos no Git. Consulte `.gitignore` antes do commit.

Para revisar as alterações:

```bash
git status --short
git diff --stat
```

Após conferir quais arquivos devem ser versionados, registrar a versão e enviar ao repositório remoto. Na Jetson, confirmar antes se a árvore de trabalho contém alterações locais importantes, para não sobrescrevê-las inadvertidamente ao atualizar o código.

---

**Resumo:** o núcleo do P4 está implementado e validado com a EMEET: captura V4L2, timestamps, métricas, SHM, Kafka e testes automatizados. **Na Jetson ainda não houve captura de quadros CSI**: o próximo passo é conferir fisicamente as câmeras e corrigir a configuração dos drivers/overlays. Depois será necessário adaptar RAW10, validar duas câmeras e definir a correlação exata entre vídeo SHM e eventos Kafka.
