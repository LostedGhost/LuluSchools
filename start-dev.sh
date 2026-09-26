#!/usr/bin/env bash
# ============================================================
#  LuluSchools — Script de démarrage développement
#  Lance : Backend FastAPI + ngrok + Frontend Vite
#  Usage  : bash start-dev.sh
#  Arrêt  : Ctrl+C  (tous les processus sont stoppés)
# ============================================================

set -e

# ── Chemins absolus (ajustez si besoin) ─────────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
PYTHON="$BACKEND_DIR/.venv/Scripts/python.exe"   # Windows (Git Bash / WSL)
# PYTHON="$BACKEND_DIR/.venv/bin/python"           # Linux / macOS — décommentez cette ligne

# ── Ports ────────────────────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=5173

# ── Couleurs terminal ────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Nettoyage à la sortie (Ctrl+C) ──────────────────────────
cleanup() {
  echo ""
  echo -e "${YELLOW}⏹  Arrêt de tous les serveurs...${RESET}"
  kill $BACKEND_PID $NGROK_PID $FRONTEND_PID 2>/dev/null || true
  wait $BACKEND_PID $NGROK_PID $FRONTEND_PID 2>/dev/null || true
  echo -e "${GREEN}✓  Tous les serveurs sont arrêtés.${RESET}"
  exit 0
}
trap cleanup INT TERM

# ── Vérifications ────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
echo "  ██╗     ██╗   ██╗██╗     ██╗   ██╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██╗     "
echo "  ██║     ██║   ██║██║     ██║   ██║██╔════╝██╔════╝██║  ██║██╔═══██╗██╔═══██╗██║     "
echo "  ██║     ██║   ██║██║     ██║   ██║███████╗██║     ███████║██║   ██║██║   ██║██║     "
echo "  ██║     ██║   ██║██║     ██║   ██║╚════██║██║     ██╔══██║██║   ██║██║   ██║██║     "
echo "  ███████╗╚██████╔╝███████╗╚██████╔╝███████║╚██████╗██║  ██║╚██████╔╝╚██████╔╝███████╗"
echo "  ╚══════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝"
echo -e "${RESET}"
echo -e "${BOLD}  🚀 Démarrage de l'environnement de développement${RESET}"
echo "  ──────────────────────────────────────────────────"

# Vérifier Python
if [ ! -f "$PYTHON" ]; then
  echo -e "${RED}✗  Python introuvable : $PYTHON${RESET}"
  echo    "   Créez le venv : cd backend && python -m venv .venv && pip install -r requirements.txt"
  exit 1
fi

# Vérifier ngrok
if ! command -v ngrok &>/dev/null; then
  echo -e "${RED}✗  ngrok n'est pas installé ou pas dans le PATH${RESET}"
  echo    "   Téléchargez-le sur https://ngrok.com/download"
  exit 1
fi

# Vérifier npm
if ! command -v npm &>/dev/null; then
  echo -e "${RED}✗  npm n'est pas installé${RESET}"
  exit 1
fi

echo ""

# ── 1. Backend FastAPI ────────────────────────────────────────
echo -e "${GREEN}▶  [1/3] Démarrage du backend FastAPI (port $BACKEND_PORT)...${RESET}"
cd "$BACKEND_DIR"
"$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload \
  > /tmp/luluschools-backend.log 2>&1 &
BACKEND_PID=$!

# Attendre que le backend soit prêt
echo -n "   En attente du backend"
for i in $(seq 1 20); do
  sleep 1
  if curl -s "http://localhost:$BACKEND_PORT/docs" > /dev/null 2>&1; then
    echo -e " ${GREEN}✓${RESET}"
    break
  fi
  echo -n "."
  if [ $i -eq 20 ]; then
    echo -e " ${RED}✗ Timeout${RESET}"
    echo "   Vérifiez les logs : /tmp/luluschools-backend.log"
  fi
done

# ── 2. ngrok ─────────────────────────────────────────────────
echo -e "${GREEN}▶  [2/3] Démarrage du tunnel ngrok...${RESET}"
ngrok http $BACKEND_PORT --log=stdout > /tmp/luluschools-ngrok.log 2>&1 &
NGROK_PID=$!

# Récupérer l'URL publique
echo -n "   En attente de l'URL ngrok"
NGROK_URL=""
for i in $(seq 1 15); do
  sleep 1
  NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null \
    | grep -o '"public_url":"[^"]*"' \
    | grep https \
    | sed 's/"public_url":"//;s/"//')
  if [ -n "$NGROK_URL" ]; then
    echo -e " ${GREEN}✓${RESET}"
    break
  fi
  echo -n "."
done

# ── 3. Frontend Vite ─────────────────────────────────────────
echo -e "${GREEN}▶  [3/3] Démarrage du frontend Vite (port $FRONTEND_PORT)...${RESET}"
cd "$FRONTEND_DIR"
npm run dev > /tmp/luluschools-frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 2

# ── Récap ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}┌─────────────────────────────────────────────────────┐${RESET}"
echo -e "${BOLD}│  ✅  LuluSchools — Tous les serveurs sont démarrés   │${RESET}"
echo -e "${BOLD}├─────────────────────────────────────────────────────┤${RESET}"
echo -e "│  🎨  Frontend  →  ${CYAN}http://localhost:$FRONTEND_PORT${RESET}"
echo -e "│  ⚙️   Backend   →  ${CYAN}http://localhost:$BACKEND_PORT${RESET}"
echo -e "│  📖  API Docs  →  ${CYAN}http://localhost:$BACKEND_PORT/docs${RESET}"
if [ -n "$NGROK_URL" ]; then
echo -e "│  🌍  Ngrok     →  ${CYAN}$NGROK_URL${RESET}"
else
echo -e "│  🌍  Ngrok     →  ${YELLOW}(voir http://127.0.0.1:4040)${RESET}"
fi
echo -e "│                                                     │"
echo -e "│  📋  Logs :                                         │"
echo -e "│     Backend  → /tmp/luluschools-backend.log         │"
echo -e "│     Ngrok    → /tmp/luluschools-ngrok.log           │"
echo -e "│     Frontend → /tmp/luluschools-frontend.log        │"
echo -e "${BOLD}├─────────────────────────────────────────────────────┤${RESET}"
echo -e "│  Appuyez sur ${BOLD}Ctrl+C${RESET} pour tout arrêter               │"
echo -e "${BOLD}└─────────────────────────────────────────────────────┘${RESET}"
echo ""

# ── Garder le script vivant ───────────────────────────────────
wait $BACKEND_PID $NGROK_PID $FRONTEND_PID
