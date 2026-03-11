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

    def _build_update_payload(self, host: dict, existing: dict) -> dict:
        payload = {
            "domain_names": existing.get("domain_names", []),
            "forward_scheme": existing.get("forward_scheme"),
            "forward_host": existing.get("forward_host"),
            "forward_port": existing.get("forward_port"),
            "access_list_id": existing.get("access_list_id", 0),
            "certificate_id": existing.get("certificate_id", 0),
            "ssl_forced": existing.get("ssl_forced", False),
            "http2_support": existing.get("http2_support", False),
            "hsts_enabled": existing.get("hsts_enabled", False),
            "hsts_subdomains": existing.get("hsts_subdomains", False),
            "block_exploits": existing.get("block_exploits", False),
            "allow_websocket_upgrade": existing.get("allow_websocket_upgrade", False),
            "caching_enabled": existing.get("caching_enabled", False),
            "advanced_config": existing.get("advanced_config", ""),
            "locations": existing.get("locations", []),
            "enabled": existing.get("enabled", True),
            "meta": existing.get("meta", {}),
        }

        if "domain" in host:
            payload["domain_names"] = [host["domain"]]
        if "scheme" in host:
            payload["forward_scheme"] = host["scheme"]
        if "forward_host" in host:
            payload["forward_host"] = host["forward_host"]
        if "forward_port" in host:
            payload["forward_port"] = int(host["forward_port"])
        if "access_list" in host:
            payload["access_list_id"] = self._get_access_list_id(host["access_list"])
        if "force_ssl" in host:
            payload["ssl_forced"] = host["force_ssl"]
        if "http2_support" in host:
            payload["http2_support"] = host["http2_support"]
        if "hsts_enabled" in host:
            payload["hsts_enabled"] = host["hsts_enabled"]
        if "block_common_exploits" in host:
            payload["block_exploits"] = host["block_common_exploits"]
        if "websocket_support" in host:
            payload["allow_websocket_upgrade"] = host["websocket_support"]
        if "caching_enabled" in host:
            payload["caching_enabled"] = host["caching_enabled"]
        if "advanced_config" in host:
            payload["advanced_config"] = host["advanced_config"]
        if "enabled" in host:
            payload["enabled"] = host["enabled"]
        if "description" in host:
            meta = dict(payload.get("meta") or {})
            meta["npm_sync_managed"] = True
            meta["description"] = host.get("description", "")
            payload["meta"] = meta
        if "certificate_strategy" in host or "certificate_name" in host:
            cert_strategy = host.get("certificate_strategy")
            cert_name = host.get("certificate_name")
            if cert_strategy == "wildcard" or (cert_strategy is None and cert_name):
                if cert_name:
                    found = self._get_certificate_id(cert_name)
                    payload["certificate_id"] = found or 0
            elif cert_strategy:
                payload["certificate_id"] = 0

        return payload

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
                existing = existing_by_domain[key]
                payload = self._build_update_payload(host, existing)
                if self.settings.dry_run:
                    results.append(SyncResult(domain=host["domain"], action="would-update"))
                else:
                    self.client.update_proxy_host(host_id, payload)
                    results.append(SyncResult(domain=host["domain"], action="updated"))
            else:
                payload = self._build_payload(host)
                if self.settings.dry_run:
                    results.append(SyncResult(domain=host["domain"], action="would-create"))
                else:
                    self.client.create_proxy_host(payload)
                    results.append(SyncResult(domain=host["domain"], action="created"))

        return results
