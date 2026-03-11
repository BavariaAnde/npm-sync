from __future__ import annotations

import yaml
from npm_sync.models import SyncResult

def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}

class Syncer:
    def __init__(self, client, settings, inventory: dict):
        self.client = client
        self.settings = settings
        self.inventory = inventory
        self.defaults = inventory.get("defaults", {})

    def _get_access_list_id(self, name: str) -> int:
        for item in self.client.get_access_lists():
            if item.get("name", "").lower() == name.lower():
                return item["id"]
        return 0

    def _get_certificate_id(self, certificate_name: str) -> int | None:
        for item in self.client.get_certificates():
            if item.get("nice_name") == certificate_name:
                return item["id"]
            if certificate_name in item.get("domain_names", []):
                return item["id"]
        return None

    def _resolve_bool(self, host: dict, key: str, default: bool) -> bool:
        return host[key] if key in host else default

    def _build_payload(self, host: dict) -> dict:
        access_list_name = host.get("access_list", self.defaults.get("access_list", self.settings.default_access_list))
        access_list_id = self._get_access_list_id(access_list_name)

        cert_strategy = host.get("certificate_strategy", self.defaults.get("certificate_strategy", self.settings.default_cert_strategy))
        cert_name = host.get("certificate_name", self.defaults.get("certificate_name", self.settings.default_cert_name))

        certificate_id = 0
        if cert_strategy == "wildcard":
            found = self._get_certificate_id(cert_name)
            if found:
                certificate_id = found

        return {
            "domain_names": [host["domain"]],
            "forward_scheme": host.get("scheme", self.defaults.get("scheme", self.settings.default_scheme)),
            "forward_host": host["forward_host"],
            "forward_port": int(host["forward_port"]),
            "access_list_id": access_list_id,
            "certificate_id": certificate_id,
            "ssl_forced": self._resolve_bool(host, "force_ssl", self.settings.default_force_ssl),
            "http2_support": self._resolve_bool(host, "http2_support", self.settings.default_http2_support),
            "hsts_enabled": self._resolve_bool(host, "hsts_enabled", self.settings.default_hsts_enabled),
            "hsts_subdomains": False,
            "block_exploits": self._resolve_bool(host, "block_common_exploits", self.settings.default_block_common_exploits),
            "allow_websocket_upgrade": self._resolve_bool(host, "websocket_support", self.settings.default_websocket_support),
            "caching_enabled": self._resolve_bool(host, "caching_enabled", self.settings.default_caching_enabled),
            "advanced_config": host.get("advanced_config", ""),
            "locations": [],
            "enabled": host.get("enabled", True),
            "meta": {
                "npm_sync_managed": True,
                "description": host.get("description", "")
            }
        }

    def sync(self) -> list[SyncResult]:
        existing_hosts = self.client.get_proxy_hosts()
        existing_by_domain = {}

        for item in existing_hosts:
            for domain in item.get("domain_names", []):
                existing_by_domain[domain.lower()] = item

        results: list[SyncResult] = []

        for host in self.inventory.get("hosts", []):
            if not host.get("enabled", True):
                results.append(SyncResult(domain=host["domain"], action="skipped-disabled"))
                continue

            payload = self._build_payload(host)
            key = host["domain"].lower()

            if key in existing_by_domain:
                host_id = existing_by_domain[key]["id"]
                if self.settings.dry_run:
                    results.append(SyncResult(domain=host["domain"], action="would-update"))
                else:
                    self.client.update_proxy_host(host_id, payload)
                    results.append(SyncResult(domain=host["domain"], action="updated"))
            else:
                if self.settings.dry_run:
                    results.append(SyncResult(domain=host["domain"], action="would-create"))
                else:
                    self.client.create_proxy_host(payload)
                    results.append(SyncResult(domain=host["domain"], action="created"))

        return results
