# ==========================================
# 0. PREPARAÇÃO — NOS DOIS TERMINAIS
# ==========================================

# Entrar no projeto
cd ~/SIS-2/p4

# Ativar o ambiente virtual
source venv/bin/activate


# ==========================================
# 1. IMX519 — CÂMERA FÍSICA
# ==========================================

# Terminal 1 — Iniciar captura RAW pelo SHM
./scripts/p4_demo.sh imx519

# Terminal 2 — Receber um frame e gerar PNG
./scripts/p4_ler.sh imx519

# Terminal 2 — Mostrar a imagem capturada
xdg-open /tmp/p4_imx519_recebido.png

# Terminal 1 — Ctrl+C para encerrar


# ==========================================
# 2. IMX477 — SEGUNDA CÂMERA
# ==========================================

# Terminal 1 — Iniciar captura RAW
./scripts/p4_demo.sh imx477

# Terminal 2 — Receber frame pelo SHM
./scripts/p4_ler.sh imx477

# Terminal 2 — Mostrar a imagem
xdg-open /tmp/p4_imx477_recebido.png

# Terminal 1 — Ctrl+C para encerrar


# ==========================================
# 3. MP4 — CÂMERA SIMULADA
# ==========================================

# Terminal 1 — Reproduzir vídeo como câmera
./scripts/p4_demo.sh video

# Terminal 2 — Receber frame BGR8 pelo SHM
./scripts/p4_ler.sh video

# Terminal 2 — Mostrar o frame recebido
xdg-open /tmp/p4_frame_recebido.png

# Terminal 1 — Ctrl+C para encerrar


# ==========================================
# 4. KAFKA — PUBLICAÇÃO E CONSUMO
# ==========================================

# Conferir se o broker está ativo
sudo docker ps --filter name=^/kafka$

# Se estiver parado, iniciar o Kafka
sudo docker start kafka

# Conferir os tópicos existentes
sudo docker exec kafka kafka-topics \
  --bootstrap-server localhost:9092 --list

# Publicar 60 eventos de frames + 1 de sessão
# Este comando encerra automaticamente
./scripts/p4_demo.sh kafka

# Recuperar e verificar os eventos publicados
./scripts/p4_kafka_ler.sh


# ==========================================
# 5. TESTES AUTOMATIZADOS
# ==========================================

# Executar os 20 testes
python -m unittest discover -s tests -p 'test_*.py' -v


# ==========================================
# 6. GITHUB
# ==========================================

# Mostrar último commit
git log -1 --oneline

# Verificar alterações pendentes
git status --short