from dataclasses import dataclass, field
from typing import Any

@dataclass
class HostEntry:
    domain: str
    forward_host: str
    forward_port: int
    scheme: str = "http"
    access_list: str = "lan"
    certificate_strategy: str = "wildcard"
    certificate_name: str = "*.example.com"
    block_common_exploits: bool = True
    websocket_support: bool = True
    caching_enabled: bool = False
    http2_support: bool = True
    hsts_enabled: bool = False
    force_ssl: bool = True
    enabled: bool = True
    advanced_config: str = ""
    description: str = ""

@dataclass
class SyncResult:
    domain: str
    action: str
    details: dict[str, Any] = field(default_factory=dict)
