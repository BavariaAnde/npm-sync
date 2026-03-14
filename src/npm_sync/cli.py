import argparse
import json
import logging
from pathlib import Path

from npm_sync import __version__
from npm_sync.config import Settings
from npm_sync.npm_client import NPMClient
from npm_sync.syncer import Syncer, load_inventory, InventoryValidationError


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize declarative proxy hosts into Nginx Proxy Manager"
    )
    parser.add_argument(
        "-c",
        "--config",
        default="/config/hosts.yml",
        help="Path to hosts inventory YAML file",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, Settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not Settings.npm_base_url:
        raise SystemExit("NPM_BASE_URL is required")

    if not Settings.npm_token and not (Settings.npm_identity and Settings.npm_secret):
        raise SystemExit("Provide NPM_TOKEN or both NPM_IDENTITY and NPM_SECRET")

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")

    if Settings.dry_run:
        logging.info("DRY_RUN enabled. No changes will be applied.")

    client = NPMClient(
        base_url=Settings.npm_base_url,
        verify_ssl=Settings.npm_verify_ssl,
        token=Settings.npm_token,
        identity=Settings.npm_identity,
        secret=Settings.npm_secret,
    )
    client.authenticate()

    inventory = load_inventory(str(config_path))
    try:
        syncer = Syncer(client, Settings, inventory)
    except InventoryValidationError as exc:
        raise SystemExit(str(exc)) from None
    results = syncer.sync()

    print(json.dumps([result.__dict__ for result in results], indent=2))
