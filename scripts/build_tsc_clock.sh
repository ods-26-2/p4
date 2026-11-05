#!/usr/bin/env bash

set -euo pipefail

# Executa a partir da raiz do projeto
cd "$(dirname "$0")/.."

# O código utiliza registradores ARM64
if [ "$(uname -m)" != "aarch64" ]; then
    echo "Erro: biblioteca TSC requer arquitetura ARM64."
    exit 1
fi

# Cria o diretório de saída
mkdir -p build

# Compila a biblioteca nativa
gcc -O2 -fPIC -shared -Wall -Wextra \
    -o build/libp4_tsc_clock.so \
    src/tsc_clock.c

echo "Biblioteca TSC compilada com sucesso!"