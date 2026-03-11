# Contributing

Thanks for your interest in contributing!

## Development Setup

1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
````

### Running Locally

```bash
cp .env.example .env
cp config/hosts.example.yml config/hosts.yml
python -m npm_sync --config config/hosts.yml
```

## Pull Requests

* Keep changes focused.
* Add or update documentation.
* Avoid breaking existing YAML structures without documenting migrations.