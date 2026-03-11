# npm-sync

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)

Declarative synchronization for Nginx Proxy Manager.

`npm-sync` reads a YAML inventory of proxy hosts and creates or updates them in Nginx Proxy Manager using its API. It is designed for homelabs, self-hosted services, and Git-based infrastructure workflows.

## Features

- Declarative inventory-based proxy host management
- Create and update Nginx Proxy Manager proxy hosts from YAML
- Wildcard certificate reuse support
- Default access list enforcement (for example `lan`)
- Block common exploits, force SSL, websocket support
- Dry-run mode via environment variable
- Docker-ready with public GHCR image

## Quick Start

1. Clone repository.
2. Create `.env` and inventory.

```bash
git clone https://github.com/BavariaAnde/npm-sync.git
cd npm-sync
cp .env.example .env
cp config/hosts.example.yml config/hosts.yml
```

3. Edit `.env` and `config/hosts.yml` for your environment.
4. Start with the public image.

```bash
docker compose up --detach
```

## Docker Compose

The default `docker-compose.yml` uses the public image:

- `ghcr.io/BavariaAnde/npm-sync:latest`

This image is public and can be pulled without login.

### Public image usage

```bash
docker compose pull
docker compose up --detach
```

### Local development build

Use the build compose file for local image builds:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build --detach
```

### Forks and custom images

If you fork this repo and publish your own image, update the image reference to:

- `ghcr.io/BavariaAnde/npm-sync:latest`

## Configuration

### .env variables

- `NPM_BASE_URL` (for example `https://npm.example.com`)
- `NPM_TOKEN` (preferred if you use token auth)
- `NPM_IDENTITY` (used when `NPM_TOKEN` is empty)
- `NPM_SECRET` (used when `NPM_TOKEN` is empty)
- `NPM_VERIFY_SSL` (`true` or `false`)
- `DEFAULT_SCHEME` (`http` or `https`)
- `DEFAULT_ACCESS_LIST` (for example `lan`)
- `DEFAULT_CERT_STRATEGY` (`wildcard`)
- `DEFAULT_CERT_NAME` (for example `*.example.com`)
- `DEFAULT_BLOCK_COMMON_EXPLOITS` (`true` or `false`)
- `DEFAULT_WEBSOCKET_SUPPORT` (`true` or `false`)
- `DEFAULT_CACHING_ENABLED` (`true` or `false`)
- `DEFAULT_HTTP2_SUPPORT` (`true` or `false`)
- `DEFAULT_HSTS_ENABLED` (`true` or `false`)
- `DEFAULT_FORCE_SSL` (`true` or `false`)
- `DRY_RUN` (`true` or `false`)
- `LOG_LEVEL` (`INFO`, `DEBUG`, and so on)

### CLI options

- `--config /config/hosts.yml` (default path)

Dry-run is controlled via env: `DRY_RUN=true`.

## Inventory schema

Top-level keys:

- `defaults` for default values applied to each host
- `hosts` list of proxy host entries

Host entry fields:

- `domain` (required)
- `forward_host` (required)
- `forward_port` (required)
- `scheme`, `access_list`, `certificate_strategy`, `certificate_name`
- `block_common_exploits`, `websocket_support`, `caching_enabled`
- `http2_support`, `hsts_enabled`, `force_ssl`
- `advanced_config`, `description`, `enabled`

## Example inventory

```yaml
defaults:
  scheme: http
  access_list: lan
  certificate_strategy: wildcard
  certificate_name: "*.example.com"
  block_common_exploits: true
  websocket_support: true
  caching_enabled: false
  http2_support: true
  hsts_enabled: false
  force_ssl: true

hosts:
  - domain: immich.example.com
    forward_host: immich
    forward_port: 2283
    description: Immich on same Docker network

  - domain: paperless.example.com
    forward_host: 192.168.1.10
    forward_port: 8000
    description: Paperless on another host
```

## My own homelab example

This section shows a complete example with LAN access list defaults, wildcard certificate reuse, and a mix of Docker service names and host IPs.

`.env` example:

```dotenv
NPM_BASE_URL=https://npm.example.com
NPM_IDENTITY=admin@example.com
NPM_SECRET=your-secret
NPM_VERIFY_SSL=true

DEFAULT_SCHEME=http
DEFAULT_ACCESS_LIST=lan
DEFAULT_CERT_STRATEGY=wildcard
DEFAULT_CERT_NAME=*.example.com
DEFAULT_BLOCK_COMMON_EXPLOITS=true
DEFAULT_WEBSOCKET_SUPPORT=true
DEFAULT_FORCE_SSL=true

DRY_RUN=true
LOG_LEVEL=INFO
```

`config/hosts.yml` example:

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
  - domain: app1.example.com
    forward_host: app1
    forward_port: 80
    description: Docker service name

  - domain: app2.example.com
    forward_host: 192.168.2.20
    forward_port: 8080
    description: Host on LAN IP
```

Start in dry-run to verify:

```bash
docker compose up --detach
```

Set `DRY_RUN=false` and restart when ready.

## Publishing (GHCR)

This project is designed to publish via GitHub Container Registry (GHCR).

1. Update `.github/workflows/docker-image.yml` to replace `BavariaAnde` with your GitHub username.
2. Push to `main` or create a tag like `v0.1.0` to trigger the workflow.
3. After the first push, open the package settings in GitHub and set visibility to Public.
4. The image tag becomes `ghcr.io/BavariaAnde/npm-sync:latest`.

## GitHub Actions

Workflow: `.github/workflows/docker-image.yml`

- Builds and pushes images on `main` and tag pushes
- Uses `docker/login-action` and `docker/build-push-action`

## Contributing

See `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.

## License

MIT License. See `LICENSE`.
