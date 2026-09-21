<div align="center">
  <img src="misc/images/LOGO1.png" height="96" alt="NETWORK Informática / Infra-Monitor" />

  <h1>Infra-Monitor</h1>
  <p><strong>Instalador LXC self-host no Proxmox VE</strong> para <em>RustDesk Server</em> + API<br/>
  Identidade NETWORK Informática — fork baseado no community-scripts</p>
</div>

---

## O que é

**Infra-Monitor** cria um container LXC no Proxmox e instala:

- **RustDesk Server** (`hbbs` / `hbbr`) — relay e ID server
- **RustDesk API** — WebUI de administração (porta **21114**)

Os binários e serviços dentro do guest continuam com os nomes upstream (`rustdesk-*`). O que muda é a marca do instalador (nome, header, logos e URLs self-host).

---

## Requisitos

| Componente | Detalhe |
| ---------- | ------- |
| **Proxmox VE** | 8.4+ (shell root no host) |
| **Rede** | Internet no host (download dos releases) e no LXC |
| **Self-host** | Repo publicado (GitHub/Gitea) **ou** HTTP local apontando para este clone |

---

## Instalação (self-host)

### 1. Configure a URL base do fork

Substitua `<seu-org>` pelo owner/remote real (GitHub, Gitea, etc.):

```bash
export COMMUNITY_SCRIPTS_URL="https://raw.githubusercontent.com/<seu-org>/Infra-Monitor/main"
```

**Alternativa local:** clone este repositório no host Proxmox e sirva via HTTP:

```bash
cd /opt/Infra-Monitor
python3 -m http.server 8080 --bind 0.0.0.0
# Em outro shell:
export COMMUNITY_SCRIPTS_URL="http://<IP-DO-HOST>:8080"
```

### 2. Rode o instalador (one-liner no shell do Proxmox)

Substitua `<seu-org>` pelo owner do seu repositório no GitHub (o repo precisa estar público ou o raw acessível).

**Debian (equivalente ao comando oficial do RustDesk):**

```bash
var_os='debian' COMMUNITY_SCRIPTS_URL='https://raw.githubusercontent.com/<seu-org>/Infra-Monitor/main' bash -c "$(curl -fsSL https://raw.githubusercontent.com/<seu-org>/Infra-Monitor/main/ct/infra-monitor.sh)"
```

**Alpine (footprint menor):**

```bash
var_os='alpine' COMMUNITY_SCRIPTS_URL='https://raw.githubusercontent.com/<seu-org>/Infra-Monitor/main' bash -c "$(curl -fsSL https://raw.githubusercontent.com/<seu-org>/Infra-Monitor/main/ct/infra-monitor.sh)"
```

**A partir de um clone no host (sem curl remoto do script):**

```bash
cd /opt/Infra-Monitor
export COMMUNITY_SCRIPTS_URL="https://raw.githubusercontent.com/<seu-org>/Infra-Monitor/main"
var_os='debian' bash ct/infra-monitor.sh
```

Siga o modo **Default** ou **Advanced** e aguarde o fim da instalação.

### 3. Acesso

Após concluir:

```text
http://<IP-DO-LXC>:21114
```

Credenciais (Alpine): arquivo `~/rustdesk.creds` dentro do container (“Infra-Monitor WebUI (RustDesk API)”).

---

## Arquivos principais

| Caminho | Função |
| ------- | ------ |
| [`ct/infra-monitor.sh`](ct/infra-monitor.sh) | Entry point no host Proxmox |
| [`install/infra-monitor-install.sh`](install/infra-monitor-install.sh) | Install dentro do LXC |
| [`ct/headers/infra-monitor`](ct/headers/infra-monitor) | ASCII art no terminal |
| [`misc/images/LOGO1.png`](misc/images/LOGO1.png) | Logo principal (NETWORK) |
| [`misc/images/IdentidadeVisual.png`](misc/images/IdentidadeVisual.png) | Referência de identidade |

O instalador original `ct/rustdeskserver.sh` permanece no repositório como legado.

---

## Variável `COMMUNITY_SCRIPTS_URL`

Usada por `misc/build.func`, `core.func`, `install.func` e `alpine-install.func` para baixar:

- scripts `install/` e `ct/headers/`
- helpers em `misc/`
- logo no MOTD/descrição do LXC

Default placeholder: `https://raw.githubusercontent.com/seu-org/Infra-Monitor/main` — **obrigatório** sobrescrever com o seu remote ou HTTP local.

Com clone local, `COMMUNITY_SCRIPTS_ROOT` é detectado automaticamente e os arquivos do host são lidos do disco quando possível.

---

## Atribuição

- Instalador LXC baseado em [Proxmox VE Helper-Scripts / community-scripts](https://github.com/community-scripts/ProxmoxVE) (MIT)
- Pacotes: [RustDesk Server](https://github.com/rustdesk/rustdesk-server) / [lejianwen/rustdesk-server](https://github.com/lejianwen/rustdesk-server) e [lejianwen/rustdesk-api](https://github.com/lejianwen/rustdesk-api)
- Identidade visual: NETWORK Informática

---

## Licença

MIT — ver [LICENSE](LICENSE).
