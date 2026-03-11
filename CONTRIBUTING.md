# Contributing

Thanks for your interest in contributing to npm-sync.

## Development setup

1. Create a virtual environment.
2. Install the project in editable mode.

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## Running locally

```bash
cp .env.example .env
cp config/hosts.example.yml config/hosts.yml
python -m npm_sync --config config/hosts.yml
```

## Running with Docker

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build --detach
```

## Pull requests

- Keep changes focused and well-scoped.
- Update documentation for behavior changes.
- Avoid breaking existing YAML structures without documenting migrations.
