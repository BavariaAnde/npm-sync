# npm-sync

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![Docker](https://img.shields.io/badge/docker-supported-blue)](https://www.docker.com)

Declarative synchronization for Nginx Proxy Manager.

`npm-sync` reads a YAML inventory of proxy hosts and creates or updates them in Nginx Proxy Manager using its API. It is designed for homelabs, self-hosted services, and Git-based infrastructure workflows.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Example Inventory](#example-inventory)
- [Docker Usage](#docker-usage)
- [Notes](#notes)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

## Features

- Create and update proxy hosts from YAML
- Reuse an existing wildcard certificate
- Apply a default access list such as `lan`
- Enable common options:
  - Block common exploits
  - Websocket support
  - Force SSL
  - HTTP/2
- Supports services by docker container name on same network or remote IP + port
- Dry-run mode for safe testing

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/BavariaAnde/npm-sync.git
cd npm-sync
```

### 2. Environment configuration

```bash
cp .env.example .env
```

Edit `.env` and set required values:

- `NPM_BASE_URL` (Nginx Proxy Manager API base URL)
- `NPM_IDENTITY` (API identity)
- `NPM_SECRET` (API secret)
- `DEFAULT_ACCESS_LIST` (e.g. `lan`)
- `DEFAULT_CERT_NAME` (e.g. `*.example.com`)
- `DRY_RUN=true|false` (default: `true`)

### 3. Inventory configuration

```bash
cp config/hosts.example.yml config/hosts.yml
```

Edit `config/hosts.yml` according to your services.

### 4. Dry-run (safe test)

```bash
docker compose up --build
```

### 5. Apply changes

Set `DRY_RUN=false` in `.env` and rerun:

```bash
docker compose up --build
```

## Configuration

- `config/hosts.yml`: list of hosts to create/update in Nginx Proxy Manager
- `defaults`: default settings for all hosts
- `hosts`: array of host entries with `domain`, `forward_host`, `forward_port`, etc.

### Required existing resources in Nginx Proxy Manager

- Access list from `DEFAULT_ACCESS_LIST`
- Certificate in wildcard mode from `DEFAULT_CERT_NAME`

## Example inventory

```yaml
defaults:
  scheme: http
  access_list: lan
  certificate_strategy: wildcard
  certificate_name: "*.example.com"
  block_common_exploits: true
  websocket_support: true
  force_ssl: true

hosts:
  - domain: immich.example.com
    forward_host: immich-server
    forward_port: 2283

  - domain: dev.service.example.com
    forward_host: dev-service
    forward_port: 3000
```

## Docker Usage

Build locally:

```bash
docker build -t npm-sync:latest .
```

Run directly:

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/config:/config:ro \
  npm-sync:latest
```

## Notes

- Only create and update operations are supported (not deletion).
- `access_list` must already exist in Nginx Proxy Manager.
- `certificate_name` must already exist in Nginx Proxy Manager when using wildcard mode.

## Roadmap

- Certificate auto-request support
- Delete/prune mode
- Labels-to-inventory generator
- Better diff output
- GitHub Container Registry publishing

## Contributing

Thank you for your interest in contributing!

- Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Open issues for bugs or feature requests.
- Use branch names like `feature/<name>` or `bugfix/<name>`.
- Create PRs with tests and clear descriptions.

## Security

Report security issues via repository issue tracker or email as outlined in `SECURITY.md` (if present).

## License

MIT License. See [LICENSE](LICENSE).
