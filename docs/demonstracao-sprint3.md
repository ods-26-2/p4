# P4 — Demonstração da Sprint 3

## Objetivo

Demonstrar que o P4 consegue:

1. Capturar imagens de câmeras físicas.
2. Utilizar um arquivo MP4 como fonte de vídeo.
3. Distribuir os frames pelo SHM.
4. Permitir que consumidores independentes recuperem imagens.
5. Publicar e recuperar eventos pelo Kafka.

Os testes são executados no ambiente da Jetson.

## Preparação

Acessar a Jetson e entrar no repositório:

```bash
cd ~/SIS-2/p4
```

Verificar se o ambiente virtual, as câmeras e o vídeo de teste estão disponíveis. Para o teste Kafka, o broker e os tópicos precisam estar ativos.

Não executar duas instâncias da mesma fonte simultaneamente.

## Demonstração 1 — Câmera física

No Terminal 1:

```bash
./scripts/p4_demo.sh imx519
```

No Terminal 2:

```bash
./scripts/p4_ler.sh imx519
```

**O que mostrar:**

- Captura em 1920×1080, formato RG10.
- Identificação da fonte e da sessão.
- Recebimento dos pixels em um processo independente.
- Imagem gerada em `/tmp/p4_imx519_recebido.png`.

O P4 transmite os dados RAW. O consumidor realiza a conversão Bayer para gerar o PNG.

Encerrar a câmera no Terminal 1 com `Ctrl+C`.

### Testar a segunda câmera

```bash
./scripts/p4_demo.sh imx477
```

Em outro terminal:

```bash
./scripts/p4_ler.sh imx477
```

Imagem resultante:

```text
/tmp/p4_imx477_recebido.png
```

Encerrar a captura após o teste.

## Demonstração 2 — Câmera simulada

No Terminal 1:

```bash
./scripts/p4_demo.sh video
```

No Terminal 2:

```bash
./scripts/p4_ler.sh video
```

**O que mostrar:**

- Reprodução do vídeo MP4 a aproximadamente 60 FPS.
- Dados BGR8 recebidos pelo consumidor.
- Identificação da sessão e do frame.
- Imagem em `/tmp/p4_frame_recebido.png`.

Essa fonte permite testar consumidores sem depender das câmeras físicas.

Encerrar o P4 com `Ctrl+C`.

## Demonstração 3 — Kafka

Publicar os eventos:

```bash
./scripts/p4_demo.sh kafka
```

Resultado observado nos testes:

```text
Frames processados: 60
Mensagens enfileiradas: 61
Mensagens confirmadas: 61
Falhas de envio: 0
Falhas de entrega: 0
Pendentes: 0
```

Ler os eventos:

```bash
./scripts/p4_kafka_ler.sh
```

Resultado observado:

```text
Eventos de início: 1
Frames recuperados: 60
Primeiro frame: 0
Último frame: 59
PUBLICAÇÃO E CONSUMO VALIDADOS!
```

O consumidor de demonstração consulta a sessão mais recente em tópicos configurados com uma partição. Não é um consumidor contínuo de produção.

## Evidências da Sprint 3

| Recurso | Evidência |
|---|---|
| IMX519 | Captura próxima de 60 FPS e PNG recebido |
| IMX477 | Captura RAW e PNG recebido |
| MP4 | Reprodução e recepção independente pelo SHM |
| SHM | Teste com dois consumidores simultâneos |
| Kafka | 61 mensagens confirmadas e 60 frames recuperados |

Esses resultados demonstram os cenários testados. Não comprovam ausência de falhas em uso prolongado.

## Responsabilidades de integração

O P4 é responsável por disponibilizar os frames e os metadados.

Os componentes consumidores são responsáveis por conectar-se às interfaces publicadas e processar os dados recebidos.

O SHM atende consumidores locais à Jetson. O Kafka disponibiliza eventos para clientes com conectividade ao broker.

## Decisão arquitetural pendente

**Quem deve iniciar e encerrar as fontes de vídeo?**

Existem duas possibilidades a discutir:

- Fontes mantidas ativas continuamente.
- Fontes iniciadas e encerradas conforme solicitações de outros componentes.

Atualmente, a operação é manual.

Os scripts simplificam a inicialização, mas ainda não implementam uma interface de controle sob demanda.

## Explicação sugerida para a apresentação

"O P4 é responsável por disponibilizar vídeo para os outros componentes do ODS.

Validamos a captura das duas câmeras físicas e também implementamos uma fonte simulada por MP4.

Os pixels são distribuídos via SHM, permitindo que outros processos recebam os frames sem acessar diretamente a câmera.

Também validamos a publicação e o consumo de metadados pelo Kafka.

Hoje as fontes são iniciadas manualmente. Precisamos definir com a arquitetura geral se elas devem permanecer sempre ativas ou se outros componentes poderão solicitar sua ativação."
