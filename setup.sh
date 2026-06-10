#!/bin/bash
# setup.sh - Setup completo del proyecto en Arch (o cualquier Linux)
# Uso: bash setup.sh
# Después: source .venv/bin/activate && python app.py

set -e  # salir si algo falla

echo "==> Verificando uv..."
if ! command -v uv &> /dev/null; then
    echo "uv no está instalado. Instalando..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env" 2>/dev/null || source "$HOME/.cargo/env" 2>/dev/null || true
fi

echo "==> Creando entorno virtual con uv..."
uv venv

echo "==> Activando venv..."
source .venv/bin/activate

echo "==> Instalando dependencias desde requirements.txt..."
uv pip install -r requirements.txt

echo ""
echo "================================================"
echo "Setup completo."
echo ""
echo "Para correr la app:"
echo "  source .venv/bin/activate"
echo "  python app.py"
echo ""
echo "Después abrir: http://localhost:5000"
echo "================================================"
