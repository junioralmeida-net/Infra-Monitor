#!/usr/bin/env bash
# Infra-Monitor — Proxmox LXC installer for RustDesk Server + API (self-host fork)
# Based on community-scripts rustdeskserver (MIT)
# Source packages: https://github.com/rustdesk/rustdesk-server | https://github.com/lejianwen/rustdesk-api

# Override when hosting this fork on GitHub/Gitea/raw HTTP:
#   export COMMUNITY_SCRIPTS_URL="https://raw.githubusercontent.com/junioralmeida-net/Infra-Monitor/main"
export COMMUNITY_SCRIPTS_URL="${COMMUNITY_SCRIPTS_URL:-https://raw.githubusercontent.com/junioralmeida-net/Infra-Monitor/main}"
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export COMMUNITY_SCRIPTS_ROOT="${COMMUNITY_SCRIPTS_ROOT:-$(cd "${_script_dir}/.." && pwd)}"

if [[ -f "${COMMUNITY_SCRIPTS_ROOT}/misc/build.func" ]]; then
  # Local clone on the Proxmox host
  # shellcheck source=/dev/null
  source "${COMMUNITY_SCRIPTS_ROOT}/misc/build.func"
else
  source <(curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/build.func")
fi

APP="Infra-Monitor"
var_tags="${var_tags:-remote-desktop}"
var_cpu="${var_cpu:-1}"
var_arm64="${var_arm64:-yes}"
var_unprivileged="${var_unprivileged:-1}"
if [[ -z "${var_os:-}" ]] && command -v pveversion >/dev/null 2>&1; then
  var_os=$(msg_menu "Choose the container OS" \
    "debian" "Debian 13" \
    "alpine" "Alpine (smaller footprint)")
fi

if [[ "${var_os:-}" == "alpine" ]]; then
  var_ram="${var_ram:-512}"
  var_disk="${var_disk:-3}"
  var_version="${var_version:-3.24}"
else
  var_ram="${var_ram:-512}"
  var_disk="${var_disk:-2}"
  var_version="${var_version:-13}"
fi

header_info "$APP"
variables
color
catch_errors

apply_infra_monitor_webui() {
  msg_info "Applying Infra-Monitor WebUI (logo, pt-BR, banner)"
  if ! command -v python3 >/dev/null 2>&1; then
    if [[ -f /etc/alpine-release ]]; then
      $STD apk add --no-cache python3
    elif command -v apt-get >/dev/null 2>&1; then
      $STD apt-get install -y -qq python3
    fi
  fi

  local i18n_dir=""
  if [[ -n "${COMMUNITY_SCRIPTS_ROOT:-}" && -f "${COMMUNITY_SCRIPTS_ROOT}/misc/apply-pt-br.py" ]]; then
    i18n_dir="${COMMUNITY_SCRIPTS_ROOT}/misc"
  else
    i18n_dir="$(mktemp -d)"
    mkdir -p "${i18n_dir}/images"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/apply-pt-br.py" -o "${i18n_dir}/apply-pt-br.py"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/i18n/pt_BR.json" -o "${i18n_dir}/pt_BR.json"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/i18n/pt_BR.toml" -o "${i18n_dir}/pt_BR.toml"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/apply-network-logo.py" -o "${i18n_dir}/apply-network-logo.py"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/images/logo-webui.png" -o "${i18n_dir}/images/logo-webui.png"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/images/favicon.ico" -o "${i18n_dir}/images/favicon.ico"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/images/favicon.png" -o "${i18n_dir}/images/favicon.png"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/apply-lang-menu-ptbr.py" -o "${i18n_dir}/apply-lang-menu-ptbr.py"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/images/idioma.png" -o "${i18n_dir}/images/idioma.png"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/apply-hello-ptbr.py" -o "${i18n_dir}/apply-hello-ptbr.py"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/hello.html" -o "${i18n_dir}/hello.html"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/apply-admin-theme.py" -o "${i18n_dir}/apply-admin-theme.py"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/images/admin-theme.css" -o "${i18n_dir}/images/admin-theme.css"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/images/brand-tokens.css" -o "${i18n_dir}/images/brand-tokens.css"
  fi

  local -a roots=()
  local candidate=""
  for candidate in /var/lib/rustdesk-api /opt/rustdesk-api /opt/rustdesk /usr/share/rustdesk-api; do
    [[ -d "$candidate" ]] && roots+=("$candidate")
  done
  if command -v systemctl >/dev/null 2>&1; then
    candidate="$(systemctl show -p WorkingDirectory --value rustdesk-api.service 2>/dev/null || true)"
    [[ -n "$candidate" && "$candidate" != "/" && -d "$candidate" ]] && roots+=("$candidate")
  fi
  if ((${#roots[@]} == 0)); then
    msg_ok "WebUI branding skipped (path not found)"
    return 0
  fi

  python3 "${i18n_dir}/apply-pt-br.py" "${roots[@]}" || true
  python3 "${i18n_dir}/apply-network-logo.py" "${roots[@]}" || true
  python3 "${i18n_dir}/apply-lang-menu-ptbr.py" "${roots[@]}" || true
  python3 "${i18n_dir}/apply-hello-ptbr.py" "${roots[@]}" || true
  python3 "${i18n_dir}/apply-admin-theme.py" "${roots[@]}" || true
  msg_ok "WebUI branding applied (logo, pt-BR, banner, tema Infra-Guardian)"
}

restart_rustdesk_api() {
  if command -v systemctl >/dev/null 2>&1 && [[ -f /lib/systemd/system/rustdesk-api.service || -f /etc/systemd/system/rustdesk-api.service ]]; then
    systemctl restart rustdesk-api || systemctl start rustdesk-api || true
  elif command -v rc-service >/dev/null 2>&1; then
    rc-service rustdesk-api restart || rc-service rustdesk-api start || true
  elif command -v service >/dev/null 2>&1; then
    service rustdesk-api restart || service rustdesk-api start || true
  fi
}

update_deb_based() {
  if [[ ! -x /usr/bin/hbbr ]]; then
    msg_error "No ${APP} Installation Found!"
    exit
  fi

  local need_server=0 need_api=0
  if check_for_gh_release "rustdesk-hbbs" "lejianwen/rustdesk-server"; then
    need_server=1
  fi
  if check_for_gh_release "rustdesk-api" "lejianwen/rustdesk-api"; then
    need_api=1
  fi

  if ((need_server || need_api)); then
    msg_info "Stopping Service"
    if ((need_server)); then
      systemctl stop rustdesk-hbbr || true
      systemctl stop rustdesk-hbbs || true
    fi
    systemctl stop rustdesk-api 2>/dev/null || true
    msg_ok "Stopped Service"

    if ((need_server)); then
      fetch_and_deploy_gh_release "rustdesk-hbbr" "lejianwen/rustdesk-server" "binary" "latest" "/opt/rustdesk" "rustdesk-server-hbbr*$(arch_resolve).deb"
      fetch_and_deploy_gh_release "rustdesk-hbbs" "lejianwen/rustdesk-server" "binary" "latest" "/opt/rustdesk" "rustdesk-server-hbbs*$(arch_resolve).deb"
      fetch_and_deploy_gh_release "rustdesk-utils" "lejianwen/rustdesk-server" "binary" "latest" "/opt/rustdesk" "rustdesk-server-utils*$(arch_resolve).deb"
    fi
    if ((need_api)); then
      fetch_and_deploy_gh_release "rustdesk-api" "lejianwen/rustdesk-api" "binary" "latest" "/opt/rustdesk" "rustdesk-api-server*$(arch_resolve).deb"
    fi
  fi

  # Branding is independent of upstream package versions (hbbs 0.1.2 can be current
  # while the WebUI still needs logo / pt-BR / hello patches).
  apply_infra_monitor_webui

  msg_info "Starting services"
  if ((need_server)); then
    systemctl start rustdesk-hbbr || true
    systemctl start rustdesk-hbbs || true
  fi
  restart_rustdesk_api
  msg_ok "Services started"

  if ((need_server || need_api)); then
    msg_ok "Updated successfully!"
  else
    msg_ok "Packages already current — WebUI branding reapplied"
  fi
}

update_alpine() {
  if [[ ! -d /opt/rustdesk-server ]]; then
    msg_error "No ${APP} Installation Found!"
    exit
  fi

  APIRELEASE=$(curl -s https://api.github.com/repos/lejianwen/rustdesk-api/releases/latest | grep "tag_name" | awk '{print substr($2, 3, length($2)-4) }')
  RELEASE=$(curl -s https://api.github.com/repos/lejianwen/rustdesk-server/releases/latest | grep "tag_name" | awk '{print substr($2, 2, length($2)-3) }')
  if [ "${RELEASE}" != "$(cat ~/.rustdesk-server 2>/dev/null)" ] || [ ! -f ~/.rustdesk-server ]; then
    msg_info "Updating Infra-Monitor (RustDesk Server) to v${RELEASE}"
    $STD apk -U upgrade
    $STD service rustdesk-server-hbbs stop
    $STD service rustdesk-server-hbbr stop
    temp_file1=$(mktemp)
    ARCH=$(arch_resolve "amd64" "arm64v8")
    curl -fsSL "https://github.com/lejianwen/rustdesk-server/releases/download/${RELEASE}/rustdesk-server-linux-${ARCH}.zip" -o "$temp_file1"
    $STD unzip "$temp_file1"
    cp -r "$ARCH"/* /opt/rustdesk-server/
    echo "${RELEASE}" >~/.rustdesk-server
    $STD service rustdesk-server-hbbs start
    $STD service rustdesk-server-hbbr start
    rm -rf "$ARCH"
    rm -f "$temp_file1"
    msg_ok "Updated Infra-Monitor (RustDesk Server)"
  else
    msg_ok "No package update. ${APP} server is already at v${RELEASE}"
  fi
  if [ "${APIRELEASE}" != "$(cat ~/.rustdesk-api 2>/dev/null)" ] || [ ! -f ~/.rustdesk-api ]; then
    msg_info "Updating Infra-Monitor API to v${APIRELEASE}"
    $STD service rustdesk-api stop
    temp_file2=$(mktemp)
    curl -fsSL "https://github.com/lejianwen/rustdesk-api/releases/download/v${APIRELEASE}/linux-$(arch_resolve).tar.gz" -o "$temp_file2"
    $STD tar zxvf "$temp_file2"
    cp -r release/* /opt/rustdesk-api
    echo "${APIRELEASE}" >~/.rustdesk-api
    rm -rf release
    rm -f "$temp_file2"
    msg_ok "Updated Infra-Monitor API"
  else
    msg_ok "No package update. Infra-Monitor API is already at v${APIRELEASE}"
  fi

  apply_infra_monitor_webui
  restart_rustdesk_api
  msg_ok "Updated successfully!"
}

function update_script() {
  header_info
  check_container_storage
  check_container_resources
  # Fallback if remote tools.func is outdated
  if ! declare -f run_os_update >/dev/null 2>&1; then
    run_os_update() {
      if [[ -f /etc/alpine-release ]] || [[ "${PCT_OSTYPE:-}" == "alpine" ]] || [[ "${var_os:-}" == "alpine" ]]; then
        update_alpine
      else
        update_deb_based
      fi
    }
  fi
  run_os_update
}

start
# start() already exits after an in-container update. Guard anyway so a
# leftover/old build.func cannot fall through into pct create.
if ! command -v pveversion >/dev/null 2>&1; then
  exit 0
fi
build_container
description

msg_ok "Completed successfully!\n"
echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW}Access it using the following URL:${CL}"
echo -e "${GATEWAY}${BGN}http://${IP}:21114/_admin/${CL}"
