from __future__ import annotations

import logging
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
        self._cert_cache: dict[str, int] = {}

    def _get_access_list_id(self, name: str) -> int:
        for item in self.client.get_access_lists():
            if item.get("name", "").lower() == name.lower():
                return item["id"]
        return 0

    def _get_certificate_id(self, certificate_name: str, allow_wildcard: bool = True) -> int | None:
        target = certificate_name.strip().lower()
        if not target:
            return None
        if target in self._cert_cache:
            return self._cert_cache[target]
        for item in self.client.get_certificates():
            nice_name = (item.get("nice_name") or "").strip().lower()
            domain_names = [str(name).strip().lower() for name in item.get("domain_names", [])]
            if nice_name and nice_name == target:
                self._cert_cache[target] = item["id"]
                return item["id"]
            if target in domain_names:
                self._cert_cache[target] = item["id"]
                return item["id"]
            if allow_wildcard:
                for domain in domain_names:
                    if domain.startswith("*.") and target.endswith(domain[1:]):
                        self._cert_cache[target] = item["id"]
                        return item["id"]
        return None

    def _ensure_certificate(self, cert_name: str, domain_names: list[str]) -> int | None:
        if not self.settings.cert_email or not self.settings.cert_agree_tos:
            logging.getLogger(__name__).warning(
                "CERT_EMAIL and CERT_AGREE_TOS must be set to request certificates."
            )
            return None
        if self.settings.cert_dns_challenge and not self.settings.cert_dns_provider:
            logging.getLogger(__name__).warning(
                "CERT_DNS_PROVIDER must be set for DNS challenge."
            )
            return None
        if self.settings.cert_dns_challenge and not self.settings.cert_dns_credentials:
            logging.getLogger(__name__).warning(
                "CERT_DNS_PROVIDER_CREDENTIALS must be a non-empty string for DNS challenge."
            )
            return None

        meta = {
            "letsencrypt_email": self.settings.cert_email,
            "letsencrypt_agree": self.settings.cert_agree_tos,
        }
        if self.settings.cert_dns_challenge:
            credentials = self.settings.cert_dns_credentials.strip()
            provider = self.settings.cert_dns_provider.strip().lower()
            if provider == "cloudflare" and credentials and "dns_cloudflare_api_token=" not in credentials:
                if "=" not in credentials:
                    credentials = f"dns_cloudflare_api_token={credentials}"
            if "," in credentials and "\n" not in credentials:
                credentials = "\n".join(part.strip() for part in credentials.split(",") if part.strip())
            meta["dns_challenge"] = True
            meta["dns_provider"] = self.settings.cert_dns_provider
            meta["dns_provider_credentials"] = credentials
            meta["propagation_seconds"] = self.settings.cert_dns_propagation_seconds

        payload = {
            "provider": "letsencrypt",
            "domain_names": domain_names,
            "nice_name": cert_name,
            "meta": meta,
        }
        try:
            self.client.create_certificate(payload)
        except Exception as exc:
            logging.getLogger(__name__).warning("Certificate request failed: %s", exc)
            return None
        return self._get_certificate_id(cert_name, allow_wildcard=False)

    def _resolve_bool(self, host: dict, key: str, default: bool) -> bool:
        return host[key] if key in host else default

    def _build_payload(self, host: dict) -> dict:
        access_list_name = host.get("access_list", self.defaults.get("access_list", self.settings.default_access_list))
        access_list_id = self._get_access_list_id(access_list_name)

        cert_strategy = host.get("certificate_strategy", self.defaults.get("certificate_strategy", self.settings.default_cert_strategy))
        cert_name = host.get("certificate_name", self.defaults.get("certificate_name", self.settings.default_cert_name))

        certificate_id = 0
        if cert_strategy == "none":
            certificate_id = 0
        elif cert_strategy == "letsencrypt" and cert_name:
            found = self._get_certificate_id(cert_name, allow_wildcard=False)
            if not found:
                found = self._ensure_certificate(cert_name, [host["domain"]])
            if found:
                certificate_id = found
            else:
                logging.getLogger(__name__).warning(
                    "Certificate '%s' not found in NPM. Using certificate_id=0.",
                    cert_name,
                )
        elif cert_name:
            found = self._get_certificate_id(cert_name)
            if found:
                certificate_id = found
            else:
                logging.getLogger(__name__).warning(
                    "Certificate '%s' not found in NPM. Using certificate_id=0.",
                    cert_name,
                )

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

    def _normalize_bool(self, value, default: bool = False) -> bool:
        if value is None:
            return default
        return bool(value)

    def _normalize_int(self, value, default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _normalize_scheme(self, value) -> str | None:
        if value is None:
            return None
        return str(value).lower()

    def _normalize_domains(self, domain_names) -> list[str]:
        if not domain_names:
            return []
        return sorted({str(domain).lower() for domain in domain_names if domain})

    def _normalize_payload(self, payload: dict) -> dict:
        domain_names = payload.get("domain_names")
        if domain_names is None and "domain" in payload:
            domain_names = [payload.get("domain")]
        return {
            "domain_names": self._normalize_domains(domain_names),
            "forward_host": payload.get("forward_host"),
            "forward_port": self._normalize_int(payload.get("forward_port"), default=None),
            "scheme": self._normalize_scheme(payload.get("forward_scheme") or payload.get("scheme")),
            "access_list_id": self._normalize_int(payload.get("access_list_id")),
            "certificate_id": self._normalize_int(payload.get("certificate_id")),
            "force_ssl": self._normalize_bool(payload.get("ssl_forced") if "ssl_forced" in payload else payload.get("force_ssl")),
            "http2_support": self._normalize_bool(payload.get("http2_support")),
            "hsts_enabled": self._normalize_bool(payload.get("hsts_enabled")),
            "hsts_subdomains": self._normalize_bool(payload.get("hsts_subdomains")),
            "websocket_support": self._normalize_bool(
                payload.get("allow_websocket_upgrade") if "allow_websocket_upgrade" in payload else payload.get("websocket_support")
            ),
            "block_common_exploits": self._normalize_bool(
                payload.get("block_exploits") if "block_exploits" in payload else payload.get("block_common_exploits")
            ),
            "caching_enabled": self._normalize_bool(payload.get("caching_enabled")),
            "advanced_config": payload.get("advanced_config") or "",
            "enabled": self._normalize_bool(payload.get("enabled"), default=True),
        }

    def _diff_payloads(self, current: dict, desired: dict) -> dict:
        current_norm = self._normalize_payload(current)
        desired_norm = self._normalize_payload(desired)
        changes: dict = {}
        for key, current_value in current_norm.items():
            desired_value = desired_norm.get(key)
            if current_value != desired_value:
                changes[key] = {"from": current_value, "to": desired_value}
        return changes

    def _create_details(self, host: dict, payload: dict) -> dict:
        details = self._normalize_payload(payload)
        return {key: value for key, value in details.items() if value is not None}

    def _is_managed_host(self, host: dict) -> bool:
        meta = host.get("meta") or {}
        return bool(meta.get("npm_sync_managed"))

    def _managed_missing_hosts(self, managed_hosts: list[dict], desired_domains: set[str]) -> list[dict]:
        missing: list[dict] = []
        for host in managed_hosts:
            host_domains = self._normalize_domains(host.get("domain_names", []))
            if not any(domain in desired_domains for domain in host_domains):
                missing.append(host)
        return missing

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
        meta = dict(payload.get("meta") or {})
        meta["npm_sync_managed"] = True
        if "description" in host:
            meta["description"] = host.get("description", "")
        payload["meta"] = meta
        if "certificate_strategy" in host or "certificate_name" in host:
            cert_strategy = host.get("certificate_strategy")
            cert_name = host.get("certificate_name")
            if cert_strategy == "none":
                payload["certificate_id"] = 0
            elif cert_strategy == "letsencrypt" and cert_name:
                found = self._get_certificate_id(cert_name, allow_wildcard=False)
                if not found:
                    found = self._ensure_certificate(cert_name, [host["domain"]])
                payload["certificate_id"] = found or 0
                if not found:
                    logging.getLogger(__name__).warning(
                        "Certificate '%s' not found in NPM. Using certificate_id=0.",
                        cert_name,
                    )
            elif cert_name:
                found = self._get_certificate_id(cert_name)
                payload["certificate_id"] = found or 0
                if not found:
                    logging.getLogger(__name__).warning(
                        "Certificate '%s' not found in NPM. Using certificate_id=0.",
                        cert_name,
                    )

        return payload

    def sync(self) -> list[SyncResult]:
        logger = logging.getLogger(__name__)
        desired_hosts = self.inventory.get("hosts", [])
        existing_hosts = self.client.get_proxy_hosts()

        logger.info("Loaded %d desired hosts from inventory", len(desired_hosts))
        logger.info("Loaded %d current NPM hosts", len(existing_hosts))

        existing_by_domain: dict[str, dict] = {}
        for item in existing_hosts:
            for domain in item.get("domain_names", []):
                if domain:
                    existing_by_domain[domain.lower()] = item

        desired_domains = {host["domain"].lower() for host in desired_hosts if host.get("domain")}
        results: list[SyncResult] = []
        counts = {
            "would-create": 0,
            "would-update": 0,
            "would-delete": 0,
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "unchanged": 0,
            "skipped-disabled": 0,
        }

        for host in desired_hosts:
            if not host.get("domain"):
                continue

            key = host["domain"].lower()
            existing = existing_by_domain.get(key)
            enabled = host.get("enabled", True)

            if not enabled:
                if existing:
                    payload = self._build_update_payload(host, existing)
                    details = self._diff_payloads(existing, payload)
                    if not details:
                        results.append(SyncResult(domain=host["domain"], action="unchanged"))
                        counts["unchanged"] += 1
                    elif self.settings.dry_run:
                        results.append(SyncResult(domain=host["domain"], action="would-update", details=details))
                        counts["would-update"] += 1
                    else:
                        self.client.update_proxy_host(existing["id"], payload)
                        results.append(SyncResult(domain=host["domain"], action="updated", details=details))
                        counts["updated"] += 1
                else:
                    results.append(SyncResult(domain=host["domain"], action="skipped-disabled"))
                    counts["skipped-disabled"] += 1
                continue

            if existing:
                payload = self._build_update_payload(host, existing)
                details = self._diff_payloads(existing, payload)
                if not details:
                    results.append(SyncResult(domain=host["domain"], action="unchanged"))
                    counts["unchanged"] += 1
                elif self.settings.dry_run:
                    results.append(SyncResult(domain=host["domain"], action="would-update", details=details))
                    counts["would-update"] += 1
                else:
                    self.client.update_proxy_host(existing["id"], payload)
                    results.append(SyncResult(domain=host["domain"], action="updated", details=details))
                    counts["updated"] += 1
            else:
                payload = self._build_payload(host)
                details = self._create_details(host, payload)
                if self.settings.dry_run:
                    results.append(SyncResult(domain=host["domain"], action="would-create", details=details))
                    counts["would-create"] += 1
                else:
                    self.client.create_proxy_host(payload)
                    results.append(SyncResult(domain=host["domain"], action="created", details=details))
                    counts["created"] += 1

        managed_hosts = [host for host in existing_hosts if self._is_managed_host(host)]
        logger.info("Managed NPM hosts: %d", len(managed_hosts))

        delete_candidates: list[dict] = []
        if not desired_domains and not self.settings.allow_empty_source:
            logger.warning("Desired host set is empty; delete reconciliation skipped (ALLOW_EMPTY_SOURCE=false).")
        else:
            delete_candidates = self._managed_missing_hosts(managed_hosts, desired_domains)

        planned_deletes = len(delete_candidates)
        if planned_deletes:
            if not self.settings.force_delete:
                if self.settings.max_delete_count > 0 and planned_deletes > self.settings.max_delete_count:
                    raise SystemExit(
                        f"Planned deletions ({planned_deletes}) exceed MAX_DELETE_COUNT ({self.settings.max_delete_count})."
                    )
                if self.settings.max_delete_percent > 0 and managed_hosts:
                    percent = (planned_deletes / len(managed_hosts)) * 100
                    if percent > self.settings.max_delete_percent:
                        raise SystemExit(
                            f"Planned deletions ({percent:.1f}%) exceed MAX_DELETE_PERCENT ({self.settings.max_delete_percent}%)."
                        )
            if not self.settings.delete_enabled and not self.settings.dry_run:
                logger.warning("Delete reconciliation planned but DELETE_ENABLED=false; no deletions will be executed.")

        for host in delete_candidates:
            domain_names = host.get("domain_names", [])
            domain = domain_names[0] if domain_names else ""
            details = {
                "id": host.get("id"),
                "domain": domain,
                "reason": "managed host missing from hosts.yml",
            }
            if self.settings.dry_run or not self.settings.delete_enabled:
                results.append(SyncResult(domain=domain, action="would-delete", details=details))
                counts["would-delete"] += 1
            else:
                self.client.delete_proxy_host(host["id"])
                results.append(SyncResult(domain=domain, action="deleted", details=details))
                counts["deleted"] += 1

        planned_creates = counts["would-create"] + counts["created"]
        planned_updates = counts["would-update"] + counts["updated"]
        planned_deletes = counts["would-delete"] + counts["deleted"]
        logger.info("Planned creates: %d, updates: %d, deletes: %d", planned_creates, planned_updates, planned_deletes)
        logger.info("Unchanged: %d, skipped-disabled: %d", counts["unchanged"], counts["skipped-disabled"])

        return results
