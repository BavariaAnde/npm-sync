import argparse
import json
import logging

from npm_sync.config import Settings
from npm_sync.npm_client import NPMClient
from npm_sync.syncer import Syncer, load_yaml

def main():
    parser = argparse.ArgumentParser(description="Synchronize declarative proxy hosts into Nginx Proxy Manager")
    parser.add_argument("-c", "--config", default="/config/hosts.yml", help="Path to hosts inventory YAML file")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, Settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s"
    )

    if not Settings.npm_base_url:
        raise SystemExit("NPM_BASE_URL is required")

    client = NPMClient(
        base_url=Settings.npm_base_url,
        verify_ssl=Settings.npm_verify_ssl,
        token=Settings.npm_token,
        identity=Settings.npm_identity,
        secret=Settings.npm_secret,
    )
    client.authenticate()

    inventory = load_yaml(args.config)
    syncer = Syncer(client, Settings, inventory)
    results = syncer.sync()

    print(json.dumps([result.__dict__ for result in results], indent=2))
