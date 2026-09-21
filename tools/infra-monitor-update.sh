#!/usr/bin/env bash
# =============================================================================
# Infra-Monitor — update from Proxmox HOST
# Updates RustDesk Server + API inside an existing Infra-Monitor LXC.
#
# Usage (on Proxmox shell):
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/junioralmeida-net/Infra-Monitor/main/tools/infra-monitor-update.sh)"
#
# Or with explicit CTID:
#   CTID=106 bash -c "$(curl -fsSL https://raw.githubusercontent.com/junioralmeida-net/Infra-Monitor/main/tools/infra-monitor-update.sh)"
#
# Options via env:
#   CTID=106              # skip interactive CT selection
#   VERBOSE=yes           # verbose update inside container
#   PHS_SILENT=1          # silent (default)
# =============================================================================
set -euo pipefail

export COMMUNITY_SCRIPTS_URL="${COMMUNITY_SCRIPTS_URL:-https://raw.githubusercontent.com/junioralmeida-net/Infra-Monitor/main}"
SCRIPT_URL="${COMMUNITY_SCRIPTS_URL}/ct/infra-monitor.sh"
PHS_SILENT="${PHS_SILENT:-1}"
VERBOSE="${VERBOSE:-no}"

if ! command -v pveversion >/dev/null 2>&1; then
  echo "ERROR: This script must run on the Proxmox VE host (pveversion not found)." >&2
  exit 1
fi

if ! command -v pct >/dev/null 2>&1; then
  echo "ERROR: pct not found." >&2
  exit 1
fi

pick_ctid() {
  if [[ -n "${CTID:-}" ]]; then
    echo "$CTID"
    return 0
  fi

  local candidates=()
  local id name tags status
  while read -r id status name tags; do
    [[ -z "$id" || "$id" == "VMID" ]] && continue
    # Match by hostname / tags used by Infra-Monitor
    if [[ "${name,,}" == *infra-monitor* ]] || [[ "${tags,,}" == *infra-monitor* ]] || [[ "${tags,,}" == *remote-desktop* ]]; then
      candidates+=("$id|$status|$name|$tags")
    fi
  done < <(pct list 2>/dev/null | awk 'NR>1 {print $1, $2, $3, $4}')

  # Fallback: any CT that already has hbbr/hbbs (RustDesk)
  if [[ ${#candidates[@]} -eq 0 ]]; then
    while read -r id status name; do
      [[ -z "$id" || "$id" == "VMID" ]] && continue
      if pct exec "$id" -- test -x /usr/bin/hbbr 2>/dev/null || pct exec "$id" -- test -d /opt/rustdesk-server 2>/dev/null; then
        candidates+=("$id|$status|$name|rustdesk")
      fi
    done < <(pct list 2>/dev/null | awk 'NR>1 {print $1, $2, $3}')
  fi

  if [[ ${#candidates[@]} -eq 0 ]]; then
    echo "ERROR: Nenhum LXC Infra-Monitor encontrado." >&2
    echo "Dica: rode com CTID=<id>  (ex.: CTID=106 bash ...)" >&2
    exit 1
  fi

  if [[ ${#candidates[@]} -eq 1 ]]; then
    echo "${candidates[0]%%|*}"
    return 0
  fi

  echo "Containers candidatos:" >&2
  local i=1
  for c in "${candidates[@]}"; do
    IFS='|' read -r id status name tags <<<"$c"
    printf "  %d) CT %s  [%s]  %s  %s\n" "$i" "$id" "$status" "$name" "$tags" >&2
    ((i++)) || true
  done
  local choice
  read -rp "Escolha o número do CT [1]: " choice </dev/tty
  choice="${choice:-1}"
  local selected="${candidates[$((choice - 1))]:-}"
  if [[ -z "$selected" ]]; then
    echo "ERROR: seleção inválida." >&2
    exit 1
  fi
  echo "${selected%%|*}"
}

CTID="$(pick_ctid)"
echo "==> Infra-Monitor update — CT ${CTID}"

if ! pct status "$CTID" >/dev/null 2>&1; then
  echo "ERROR: CT ${CTID} não existe." >&2
  exit 1
fi

if ! pct status "$CTID" | grep -qi running; then
  echo "==> Iniciando CT ${CTID}..."
  pct start "$CTID"
  sleep 3
fi

echo "==> Atualizando pacotes RustDesk / API dentro do CT ${CTID}..."
pct exec "$CTID" -- bash -c "
  set -euo pipefail
  export COMMUNITY_SCRIPTS_URL='${COMMUNITY_SCRIPTS_URL}'
  export PHS_SILENT='${PHS_SILENT}'
  export VERBOSE='${VERBOSE}'
  bash -c \"\$(curl -fsSL '${SCRIPT_URL}')\"
"

echo "==> Update concluído no CT ${CTID}."
IP="$(pct exec "$CTID" -- hostname -I 2>/dev/null | awk '{print $1}' || true)"
if [[ -n "${IP:-}" ]]; then
  echo "    WebUI: http://${IP}:21114"
fi
