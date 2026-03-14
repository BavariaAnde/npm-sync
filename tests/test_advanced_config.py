import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("src"))

from npm_sync.syncer import (  # noqa: E402
    InventoryValidationError,
    load_inventory,
    validate_inventory,
)


class AdvancedConfigProfileTests(unittest.TestCase):
    def test_raw_advanced_config_still_works(self):
        raw = "proxy_set_header X-Test test-value;"
        inventory = {
            "hosts": [
                {
                    "domain": "app.example.com",
                    "forward_host": "app",
                    "forward_port": 8080,
                    "advanced_config": raw,
                }
            ]
        }
        validated = validate_inventory(inventory)
        self.assertEqual(validated["hosts"][0]["advanced_config"], raw)

    def test_profile_resolution_works(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            profile_path = base_dir / "authelia_proxy.conf"
            profile_body = "proxy_set_header X-Test authelia;"
            profile_path.write_text(profile_body, encoding="utf-8")

            hosts_path = base_dir / "hosts.yml"
            hosts_path.write_text(
                "\n".join(
                    [
                        "hosts:",
                        "  - domain: app.example.com",
                        "    forward_host: app",
                        "    forward_port: 8080",
                        "    advanced_config: authelia_proxy",
                    ]
                ),
                encoding="utf-8",
            )

            validated = load_inventory(str(hosts_path))
            self.assertEqual(validated["hosts"][0]["advanced_config"], profile_body)

    def test_unknown_profile_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hosts_path = Path(tmpdir) / "hosts.yml"
            hosts_path.write_text(
                "\n".join(
                    [
                        "hosts:",
                        "  - domain: app.example.com",
                        "    forward_host: app",
                        "    forward_port: 8080",
                        "    advanced_config: unknown_profile",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(InventoryValidationError):
                load_inventory(str(hosts_path))

    def test_auth_portal_loop_protection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "authelia_proxy.conf").write_text("proxy_set_header X-Test authelia;", encoding="utf-8")
            hosts_path = base_dir / "hosts.yml"
            hosts_path.write_text(
                "\n".join(
                    [
                        "hosts:",
                        "  - domain: auth.andreas-goettl.de",
                        "    forward_host: authelia",
                        "    forward_port: 9091",
                        "    advanced_config: authelia_proxy",
                    ]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(InventoryValidationError):
                load_inventory(str(hosts_path))


if __name__ == "__main__":
    unittest.main()
