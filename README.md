# npm-sync

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)

npm-sync keeps Nginx Proxy Manager in sync with a declarative `hosts.yml` file. It creates, updates, and (optionally) deletes managed proxy hosts so your NPM configuration stays reproducible and version-controlled.

Why use it:

- Avoid manual clicks in the NPM UI
- Keep proxy hosts consistent across environments
- Track changes in Git

## Web UI

The built-in web UI lets you trigger Dry Run / Apply and review results with a clean table, filters, and a history view.

![npm-sync UI preview](docs/ui-demo.gif)

## Install with Docker Compose (public image)

```bash
git clone https://github.com/BavariaAnde/npm-sync.git
cd npm-sync
cp .env.example .env
cp config/hosts.example.yml config/hosts.yml

docker compose pull
docker compose up --detach
```

The default `docker-compose.yml` uses `ghcr.io/BavariaAnde/npm-sync:latest`.

The web UI is available on `http://localhost:8080` (or your `UI_PORT`) and is protected by basic auth.

## Local development build

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build --detach
```

## Configuration (.env)

NPM API:

- `NPM_BASE_URL` URL to your NPM instance
- `NPM_TOKEN` token auth (fast, but tokens can expire)
- `NPM_IDENTITY` identity email (used when token is empty)
- `NPM_SECRET` secret/password (used when token is empty)
- `NPM_VERIFY_SSL` verify TLS (`true` or `false`)

Note: If you use `NPM_TOKEN` and runs start failing with `jwt expired`, either generate a new token in NPM or switch to `NPM_IDENTITY` + `NPM_SECRET` so npm-sync can request a fresh token automatically.

Defaults used only when creating new hosts:

- `DEFAULT_SCHEME` (`http` or `https`)
- `DEFAULT_ACCESS_LIST` access list name
- `DEFAULT_CERT_STRATEGY` (`wildcard`)
- `DEFAULT_CERT_NAME` (for example `*.example.com`)
- `DEFAULT_BLOCK_COMMON_EXPLOITS` (`true` or `false`)
- `DEFAULT_WEBSOCKET_SUPPORT` (`true` or `false`)
- `DEFAULT_CACHING_ENABLED` (`true` or `false`)
- `DEFAULT_HTTP2_SUPPORT` (`true` or `false`)
- `DEFAULT_HSTS_ENABLED` (`true` or `false`)
- `DEFAULT_FORCE_SSL` (`true` or `false`)

Runtime:

- `DRY_RUN` (`true` or `false`)
- `LOG_LEVEL` (`INFO`, `DEBUG`, and so on)

UI:

- `UI_USERS` basic auth users (`user:password`, comma-separated)
- `UI_BIND` bind address (default `0.0.0.0`)
- `UI_PORT` listen port (default `8080`)
- `HISTORY_PATH` JSON history file path (default `/app/data/history.json`)
- `HISTORY_MAX` max stored runs (default `200`)

History is stored in the Docker volume `npm_sync_history` so it survives container recreation.

Deletion safety:

- `DELETE_ENABLED` (`true` or `false`)
- `ALLOW_EMPTY_SOURCE` (`true` or `false`)
- `MAX_DELETE_COUNT` (integer, 0 disables)
- `MAX_DELETE_PERCENT` (0 to 100, 0 disables)
- `FORCE_DELETE` (`true` or `false`)

## Inventory (hosts.yml)

Minimal example:

```yaml
hosts:
  - domain: app.example.com
    forward_host: app
    forward_port: 8080
```

Optional fields:

- `scheme`, `access_list`, `certificate_strategy`, `certificate_name`
- `block_common_exploits`, `websocket_support`, `caching_enabled`
- `http2_support`, `hsts_enabled`, `force_ssl`
- `advanced_config`, `description`, `enabled`

Certificate examples:

```yaml
# Certificates must already exist in NPM (wildcard or specific).
# Use a specific certificate by name
- domain: app.example.com
  forward_host: app
  forward_port: 8080
  certificate_strategy: custom
  certificate_name: "app.example.com"

# Disable certificate / SSL
- domain: internal.example.com
  forward_host: internal
  forward_port: 8080
  certificate_strategy: none
```

## How to use

- Run once with `DRY_RUN=true` to review planned changes
- Set `DRY_RUN=false` to apply creates and updates
- Set `DELETE_ENABLED=true` if you want missing managed hosts removed

## License

MIT License. See `LICENSE`.
