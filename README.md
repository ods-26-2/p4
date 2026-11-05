# P4 — Fonte de Vídeo

**ODS 2026/2 | Squad SIS-2 — Sinal e Dispositivo**

Componente responsável por capturar e disponibilizar frames de vídeo para os demais componentes do sistema ODS.

O P4 suporta câmeras físicas conectadas à Jetson e arquivos MP4 utilizados como fontes simuladas. Os frames são disponibilizados por memória compartilhada (SHM), enquanto seus eventos e metadados podem ser publicados no Apache Kafka.

## Visão geral

```text
IMX519 ────┐
IMX477 ────┼──> P4 ──> SHM ────> Consumidores de vídeo
MP4 ───────┘       └──> Kafka ──> Consumidores de eventos
```

O P4 não executa reconhecimento de imagens ou outras tarefas de inteligência artificial. Sua função é fornecer os dados necessários para os componentes consumidores.

## Funcionalidades

| Funcionalidade | Estado |
|---|---|
| Captura pela IMX519 | Validada |
| Captura pela IMX477 | Validada |
| Simulação de câmera com MP4 | Validada |
| Publicação de frames pelo SHM | Validada |
| Múltiplos consumidores no mesmo SHM | Validada em teste |
| Publicação de eventos no Kafka | Validada |
| Consumo independente dos eventos Kafka | Validado |
| Inicialização automática sob demanda | Não implementada |

As câmeras foram validadas individualmente. Os testes realizados não substituem uma validação prolongada da operação integrada.

## Pré-requisitos

O ambiente de referência é uma **NVIDIA Jetson Orin**, com:

- Python e ambiente virtual em `venv/`;
- dependências de `requirements.txt`;
- GStreamer e bindings Python (`gi`);
- dispositivos V4L2 e drivers das câmeras;
- Kafka acessível, quando utilizado.

Os scripts abaixo pressupõem o ambiente da Jetson já configurado.

## Início rápido

Execute os comandos a partir da raiz do repositório.

### Iniciar uma câmera física

IMX519:

```bash
./scripts/p4_demo.sh imx519
```

IMX477:

```bash
./scripts/p4_demo.sh imx477
```

### Iniciar uma câmera simulada

```bash
./scripts/p4_demo.sh video
```

Por padrão, o script utiliza:

```text
../videos/cars_extended.mp4
```

Para selecionar outro arquivo:

```bash
./scripts/p4_demo.sh video /caminho/para/video.mp4
```

As fontes são iniciadas manualmente. Utilize `Ctrl+C` para encerrar a captura.

Os comandos acima habilitam o SHM, mas mantêm o Kafka desativado.

## Consumir um frame pelo SHM

Com o P4 em execução, abra outro terminal.

IMX519:

```bash
./scripts/p4_ler.sh imx519
```

IMX477:

```bash
./scripts/p4_ler.sh imx477
```

Vídeo MP4:

```bash
./scripts/p4_ler.sh video
```

O consumidor independente recupera o frame, exibe os metadados e salva uma imagem PNG.

As câmeras físicas enviam dados RAW Bayer (`RG10`). A conversão para PNG acontece somente no consumidor, para visualização.

## Publicação e consumo Kafka

Para realizar uma demonstração com 60 frames do MP4 e Kafka ativado:

```bash
./scripts/p4_demo.sh kafka
```

Consultar os eventos publicados:

```bash
./scripts/p4_kafka_ler.sh
```

O teste publica um evento de início de sessão e um evento por frame, totalizando 61 mensagens.

Tópicos utilizados:

| Tópico | Conteúdo |
|---|---|
| `ods.session.started` | Identificação do início de uma sessão |
| `ods.p4.frame` | Metadados dos frames |

**Os pixels não são enviados pelo Kafka.** As imagens são disponibilizadas pelo SHM.

## Interfaces de saída

| Fonte | Socket SHM | Formato validado |
|---|---|---|
| IMX519 | `/tmp/p4_imx519_shm` | 1920×1080, RG10 |
| IMX477 | `/tmp/p4_imx477_shm` | 1920×1080, RG10 |
| MP4 | `/tmp/p4_file_shm` | BGR8, conforme vídeo |

Os pacotes SHM utilizam o protocolo `P4R1`, contendo cabeçalho JSON e bytes dos pixels.

**O SHM é local à Jetson.** Consumidores em outras máquinas não acessam diretamente esses sockets. Para transferência remota de imagens, será necessário um mecanismo adicional.

## Testes automatizados

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

A última bateria registrada antes da inclusão dos scripts de demonstração teve 20 testes aprovados.

## Documentação

- [Demonstração da Sprint 3](docs/demonstracao-sprint3.md) — roteiro de execução, resultados e pontos para apresentação.
- [Referência técnica](docs/referencia-tecnica.md) — documentação detalhada anterior, preservada para consulta.

## Limitações e próximos passos

Atualmente, as fontes são iniciadas e encerradas manualmente. Ainda é necessário definir com a arquitetura geral do ODS se elas deverão permanecer continuamente ativas ou ser controladas sob demanda.

A versão atual também possui um socket compartilhado para fontes MP4, não oferecendo isolamento entre diferentes arquivos executados simultaneamente.

A sincronização efetiva com o componente P5 e a integração com consumidores reais dos demais squads ainda dependem de validação conjunta.

## Equipe

**Squad SIS-2 — Sinal e Dispositivo**

- Arthur Carvalho
- João Lucas
- Felipe de Araujo
