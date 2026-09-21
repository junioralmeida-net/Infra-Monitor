#!/usr/bin/env bash
# =============================================================================
# Infra-Monitor — update INSIDE the LXC (run via pct enter / SSH into CT)
#
# Usage inside the container:
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/junioralmeida-net/Infra-Monitor/main/tools/infra-monitor-update-ct.sh)"
#
# Or if /usr/bin/update already exists (created by the installer):
#   update
# =============================================================================
set -euo pipefail

export COMMUNITY_SCRIPTS_URL="${COMMUNITY_SCRIPTS_URL:-https://raw.githubusercontent.com/junioralmeida-net/Infra-Monitor/main}"
export PHS_SILENT="${PHS_SILENT:-1}"
export VERBOSE="${VERBOSE:-no}"

if command -v pveversion >/dev/null 2>&1; then
  echo "ERROR: Este script deve rodar DENTRO do LXC, não no host Proxmox." >&2
  echo "No host use: tools/infra-monitor-update.sh" >&2
  exit 1
fi

if [[ ! -x /usr/bin/hbbr && ! -d /opt/rustdesk-server ]]; then
  echo "ERROR: Instalação Infra-Monitor / RustDesk não encontrada neste container." >&2
  exit 1
fi

echo "==> Atualizando Infra-Monitor (RustDesk Server + API)..."
bash -c "$(curl -fsSL "${COMMUNITY_SCRIPTS_URL}/ct/infra-monitor.sh")"
echo "==> Update concluído."
