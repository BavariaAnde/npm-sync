# npm-sync

Declarative synchronization for Nginx Proxy Manager.

`npm-sync` reads a YAML inventory of proxy hosts and creates or updates them in Nginx Proxy Manager using its API. It is designed for homelabs, self-hosted services, and Git-based infrastructure workflows.

## Features

- Create and update proxy hosts from YAML
- Reuse an existing wildcard certificate
- Apply a default access list such as `lan`
- Enable common options:
  - Block common exploits
  - Websocket support
  - Force SSL
  - HTTP/2
- Works with:
  - Docker service names on the same network
  - IP + port for remote services
- Dry-run mode for safe testing

## Use cases

- Deploy a new Docker stack and have its proxy host created automatically
- Use domain-driven naming like `immich.example.com`
- Store reverse proxy configuration in Git
- Apply the same defaults for most services

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
````

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/YOURUSER/npm-sync.git
cd npm-sync
```

### 2. Create your local environment file

```bash
cp .env.example .env
```

Edit `.env` and set:

* `NPM_BASE_URL`
* `NPM_IDENTITY`
* `NPM_SECRET`
* `DEFAULT_ACCESS_LIST`
* `DEFAULT_CERT_NAME`

### 3. Create your inventory

```bash
cp config/hosts.example.yml config/hosts.yml
```

Edit `config/hosts.yml`.

### 4. Run a dry run

```bash
docker compose up --build
```

### 5. Apply changes

Set `DRY_RUN=false` in `.env`, then run:

```bash
docker compose up --build
```

## Docker image

You can build locally:

```bash
docker build -t npm-sync:latest .
```

Or run directly:

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/config:/config:ro \
  npm-sync:latest
```

## Notes

* `access_list` must already exist in Nginx Proxy Manager
* `certificate_name` must already exist in Nginx Proxy Manager when using wildcard mode
* This project currently manages create and update operations, not deletion

## Roadmap

* Certificate auto-request support
* Delete mode / prune mode
* Labels-to-inventory generator
* Better diff output
* GitHub Container Registry publishing
