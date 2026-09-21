#!/usr/bin/env bash

# Infra-Monitor — in-container install (RustDesk Server + API)
# Based on community-scripts rustdeskserver-install (MIT)
# Source: https://github.com/rustdesk/rustdesk-server

source /dev/stdin <<<"$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

apply_webui_ptbr() {
  msg_info "Adding Português (Brasil) to the WebUI language menu"
  if ! command -v python3 >/dev/null 2>&1; then
    if [[ -f /etc/alpine-release ]]; then
      $STD apk add --no-cache python3
    elif command -v apt-get >/dev/null 2>&1; then
      $STD apt-get install -y -qq python3
    fi
  fi
  local i18n_dir=""
  if [[ -n "${COMMUNITY_SCRIPTS_ROOT:-}" && -f "${COMMUNITY_SCRIPTS_ROOT}/misc/i18n/apply-pt-br.py" ]]; then
    i18n_dir="${COMMUNITY_SCRIPTS_ROOT}/misc/i18n"
  else
    i18n_dir="$(mktemp -d)"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/i18n/pt_BR.json" -o "${i18n_dir}/pt_BR.json"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/i18n/pt_BR.toml" -o "${i18n_dir}/pt_BR.toml"
    curl -fsSL "${COMMUNITY_SCRIPTS_URL}/misc/i18n/apply-pt-br.py" -o "${i18n_dir}/apply-pt-br.py"
  fi
  python3 "${i18n_dir}/apply-pt-br.py" /opt/rustdesk-api /opt/rustdesk
  msg_ok "Português (Brasil) available in Language menu"
}

setup_deb_based() {
  fetch_and_deploy_gh_release "rustdesk-hbbr" "lejianwen/rustdesk-server" "binary" "latest" "/opt/rustdesk" "rustdesk-server-hbbr*$(arch_resolve).deb"
  fetch_and_deploy_gh_release "rustdesk-hbbs" "lejianwen/rustdesk-server" "binary" "latest" "/opt/rustdesk" "rustdesk-server-hbbs*$(arch_resolve).deb"
  fetch_and_deploy_gh_release "rustdesk-utils" "lejianwen/rustdesk-server" "binary" "latest" "/opt/rustdesk" "rustdesk-server-utils*$(arch_resolve).deb"
  fetch_and_deploy_gh_release "rustdesk-api" "lejianwen/rustdesk-api" "binary" "latest" "/opt/rustdesk" "rustdesk-api-server*$(arch_resolve).deb"
  apply_webui_ptbr
  systemctl enable -q --now rustdesk-hbbr
  systemctl enable -q --now rustdesk-hbbs
  systemctl enable -q --now rustdesk-api
}

setup_alpine() {
  RELEASE=$(curl -s https://api.github.com/repos/lejianwen/rustdesk-server/releases/latest | grep "tag_name" | awk '{print substr($2, 2, length($2)-3) }')
  msg_info "Installing Infra-Monitor (RustDesk Server) v${RELEASE}"
  temp_file1=$(mktemp)
  ARCH=$(arch_resolve "amd64" "arm64v8")
  curl -fsSL "https://github.com/lejianwen/rustdesk-server/releases/download/${RELEASE}/rustdesk-server-linux-${ARCH}.zip" -o "$temp_file1"
  $STD unzip "$temp_file1"
  mv "$ARCH" /opt/rustdesk-server
  mkdir -p /root/.config/rustdesk
  cd /opt/rustdesk-server
  ./rustdesk-utils genkeypair >/tmp/rustdesk_keys.txt
  grep "Public Key" /tmp/rustdesk_keys.txt | awk '{print $3}' >/root/.config/rustdesk/id_ed25519.pub
  grep "Secret Key" /tmp/rustdesk_keys.txt | awk '{print $3}' >/root/.config/rustdesk/id_ed25519
  chmod 600 /root/.config/rustdesk/id_ed25519
  chmod 644 /root/.config/rustdesk/id_ed25519.pub
  rm /tmp/rustdesk_keys.txt
  echo "${RELEASE}" >~/.rustdesk-server
  msg_ok "Installed Infra-Monitor (RustDesk Server) v${RELEASE}"

  APIRELEASE=$(curl -s https://api.github.com/repos/lejianwen/rustdesk-api/releases/latest | grep "tag_name" | awk '{print substr($2, 3, length($2)-4) }')
  msg_info "Installing Infra-Monitor API v${APIRELEASE}"
  temp_file2=$(mktemp)
  curl -fsSL "https://github.com/lejianwen/rustdesk-api/releases/download/v${APIRELEASE}/linux-$(arch_resolve).tar.gz" -o "$temp_file2"
  $STD tar zxvf "$temp_file2"
  mv release /opt/rustdesk-api
  cd /opt/rustdesk-api
  ADMINPASS=$(head -c 16 /dev/urandom | xxd -p -c 16)
  $STD ./apimain reset-admin-pwd "$ADMINPASS"
  cat <<EOF >~/rustdesk.creds
Infra-Monitor WebUI (RustDesk API)

Username: admin
Password: $ADMINPASS
EOF
  echo "${APIRELEASE}" >~/.rustdesk-api
  msg_ok "Installed Infra-Monitor API v${APIRELEASE}"

  msg_info "Enabling Infra-Monitor Services"
  cat <<EOF >/etc/init.d/rustdesk-server-hbbs
#!/sbin/openrc-run
description="Infra-Monitor HBBS Service"
directory="/opt/rustdesk-server"
command="/opt/rustdesk-server/hbbs"
command_args=""
command_background="true"
command_user="root"
pidfile="/var/run/rustdesk-server-hbbs.pid"
output_log="/var/log/rustdesk-hbbs.log"
error_log="/var/log/rustdesk-hbbs.err"

depend() {
    use net
}
EOF

  cat <<EOF >/etc/init.d/rustdesk-server-hbbr
#!/sbin/openrc-run
description="Infra-Monitor HBBR Service"
directory="/opt/rustdesk-server"
command="/opt/rustdesk-server/hbbr"
command_args=""
command_background="true"
command_user="root"
pidfile="/var/run/rustdesk-server-hbbr.pid"
output_log="/var/log/rustdesk-hbbr.log"
error_log="/var/log/rustdesk-hbbr.err"

depend() {
    use net
}
EOF

  cat <<EOF >/etc/init.d/rustdesk-api
#!/sbin/openrc-run
description="Infra-Monitor API Service"
directory="/opt/rustdesk-api"
command="/opt/rustdesk-api/apimain"
command_args=""
command_background="true"
command_user="root"
pidfile="/var/run/rustdesk-api.pid"
output_log="/var/log/rustdesk-api.log"
error_log="/var/log/rustdesk-api.err"

depend() {
    use net
}
EOF
  chmod +x /etc/init.d/rustdesk-server-hbbs
  chmod +x /etc/init.d/rustdesk-server-hbbr
  chmod +x /etc/init.d/rustdesk-api
  $STD rc-update add rustdesk-server-hbbs default
  $STD rc-update add rustdesk-server-hbbr default
  $STD rc-update add rustdesk-api default
  msg_ok "Enabled Infra-Monitor Services"

  apply_webui_ptbr

  msg_info "Starting Infra-Monitor"
  $STD service rustdesk-server-hbbs start
  $STD service rustdesk-server-hbbr start
  $STD service rustdesk-api start
  msg_ok "Started Infra-Monitor"

  rm -f "$temp_file1" "$temp_file2"
}

# Fallback if install.func on the remote is outdated (missing run_os_setup)
if ! declare -f run_os_setup >/dev/null 2>&1; then
  run_os_setup() {
    if [[ -f /etc/alpine-release ]] || [[ "${PCT_OSTYPE:-}" == "alpine" ]] || [[ "${var_os:-}" == "alpine" ]]; then
      setup_alpine
    else
      setup_deb_based
    fi
  }
fi

run_os_setup

motd_ssh
customize
cleanup_lxc
