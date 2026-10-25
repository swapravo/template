#!/usr/bin/env bash
# =============================================================================
# manage.sh — App lifecycle manager
# Usage: ./manage.sh [start|restart|reset|backup]
#        Run without arguments for an interactive menu.
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
header()  {
  echo -e "\n${BOLD}${CYAN}══════════════════════════════════════${RESET}"
  echo -e "${BOLD}${CYAN}  $*${RESET}"
  echo -e "${BOLD}${CYAN}══════════════════════════════════════${RESET}\n"
}

# Load .env so we can reference POSTGRES_* variables in backup
load_env() {
  if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -E '^[A-Z_]+=.' "$SCRIPT_DIR/.env")
    set +a
  else
    error ".env not found — copy .env.example to .env and fill it in."
    exit 1
  fi
}

require_docker() {
  if ! command -v docker &>/dev/null; then
    error "docker not found. Install Docker Desktop and try again."
    exit 1
  fi
  if ! docker info &>/dev/null; then
    error "Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
  fi
}

# ── 1. Pull latest & start ────────────────────────────────────────────────────
cmd_start() {
  header "Pull latest & start"
  require_docker
  load_env

  info "Pulling latest code from git..."
  git -C "$SCRIPT_DIR" pull --ff-only

  info "Building images and starting all services..."
  docker compose -f "$SCRIPT_DIR/docker-compose.yml" up --build -d

  success "All services started. Streaming logs (Ctrl+C to detach)..."
  echo ""
  docker compose -f "$SCRIPT_DIR/docker-compose.yml" logs -f
}

# ── 2. Restart ────────────────────────────────────────────────────────────────
cmd_restart() {
  header "Restart"
  require_docker

  info "Restarting all services..."
  docker compose -f "$SCRIPT_DIR/docker-compose.yml" restart

  success "All services restarted. Streaming logs (Ctrl+C to detach)..."
  echo ""
  docker compose -f "$SCRIPT_DIR/docker-compose.yml" logs -f
}

# ── 3. Reset (remove volumes) ─────────────────────────────────────────────────
cmd_reset() {
  header "Reset — Volume Wipe"
  require_docker

  warn "This will DESTROY all data volumes (database, redis, file storage)."
  warn "This action is IRREVERSIBLE."
  echo ""
  read -rp "$(echo -e "${RED}Type 'yes' to confirm: ${RESET}")" confirm
  if [[ "$confirm" != "yes" ]]; then
    info "Aborted — no changes made."
    exit 0
  fi

  info "Stopping and removing containers + volumes..."
  docker compose -f "$SCRIPT_DIR/docker-compose.yml" down --volumes --remove-orphans

  success "Volumes removed. To start fresh run:  ./manage.sh start"
}

# ── 4. Backup ─────────────────────────────────────────────────────────────────
cmd_backup() {
  header "Backup"
  require_docker
  load_env

  TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
  DEST="$BACKUP_DIR/$TIMESTAMP"
  mkdir -p "$DEST"

  info "Backup destination: $DEST"
  echo ""

  # ── PostgreSQL ──────────────────────────────────────────────────────────────
  info "Dumping PostgreSQL (pg_dumpall)..."
  if docker compose -f "$SCRIPT_DIR/docker-compose.yml" ps postgres | grep -q "running\|Up"; then
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" exec -T postgres \
      pg_dumpall -U "${POSTGRES_USER:-postgres}" \
      > "$DEST/postgres.sql"
    success "PostgreSQL → $DEST/postgres.sql"
  else
    warn "postgres container is not running — skipping DB backup."
  fi

  # ── Redis ───────────────────────────────────────────────────────────────────
  info "Snapshotting Redis (BGSAVE)..."
  if docker compose -f "$SCRIPT_DIR/docker-compose.yml" ps redis | grep -q "running\|Up"; then
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" exec -T redis redis-cli BGSAVE > /dev/null
    sleep 2
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" cp \
      redis:/data/dump.rdb "$DEST/redis.rdb" 2>/dev/null \
      && success "Redis → $DEST/redis.rdb" \
      || warn "Could not copy Redis RDB (may not exist if redis has no data yet)."
  else
    warn "redis container is not running — skipping Redis backup."
  fi

  # ── .env ────────────────────────────────────────────────────────────────────
  info "Backing up .env..."
  cp "$SCRIPT_DIR/.env" "$DEST/.env"
  success ".env → $DEST/.env"

  # ── Manifest ─────────────────────────────────────────────────────────────────
  {
    echo "Backup created at: $TIMESTAMP"
    echo "Git commit: $(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || echo 'unknown')"
    echo "Git branch: $(git -C "$SCRIPT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
  } > "$DEST/manifest.txt"

  echo ""
  success "Backup complete → $DEST"
  echo ""
  ls -lh "$DEST"
}

# ── Menu ──────────────────────────────────────────────────────────────────────
show_menu() {
  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${CYAN}║         App Manager                  ║${RESET}"
  echo -e "${BOLD}${CYAN}╚══════════════════════════════════════╝${RESET}"
  echo ""
  echo -e "  ${GREEN}1)${RESET} Pull latest & start"
  echo -e "  ${YELLOW}2)${RESET} Restart"
  echo -e "  ${RED}3)${RESET} Reset  ${RED}(destroys all data volumes)${RESET}"
  echo -e "  ${CYAN}4)${RESET} Backup"
  echo -e "  ${BOLD}5)${RESET} Exit"
  echo ""
  read -rp "Choose an option [1-5]: " choice
  case "$choice" in
    1) cmd_start   ;;
    2) cmd_restart ;;
    3) cmd_reset   ;;
    4) cmd_backup  ;;
    5) exit 0      ;;
    *) error "Invalid option: $choice"; show_menu ;;
  esac
}

# ── Entry point ───────────────────────────────────────────────────────────────
case "${1:-}" in
  start)   cmd_start   ;;
  restart) cmd_restart ;;
  reset)   cmd_reset   ;;
  backup)  cmd_backup  ;;
  "")      show_menu   ;;
  *)
    error "Unknown command: $1"
    echo "Usage: $0 [start|restart|reset|backup]"
    exit 1
    ;;
esac
