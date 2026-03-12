import os
from dotenv import load_dotenv

load_dotenv()

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default

def env_float(name: str, default: float = 0.0) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default

class Settings:
    npm_base_url = os.getenv("NPM_BASE_URL", "").rstrip("/")
    npm_identity = os.getenv("NPM_IDENTITY", "")
    npm_secret = os.getenv("NPM_SECRET", "")
    npm_token = os.getenv("NPM_TOKEN", "")
    npm_verify_ssl = env_bool("NPM_VERIFY_SSL", True)

    default_scheme = os.getenv("DEFAULT_SCHEME", "http")
    default_access_list = os.getenv("DEFAULT_ACCESS_LIST", "lan")
    default_cert_strategy = os.getenv("DEFAULT_CERT_STRATEGY", "wildcard")
    default_cert_name = os.getenv("DEFAULT_CERT_NAME", "*.example.com")

    default_block_common_exploits = env_bool("DEFAULT_BLOCK_COMMON_EXPLOITS", True)
    default_websocket_support = env_bool("DEFAULT_WEBSOCKET_SUPPORT", True)
    default_caching_enabled = env_bool("DEFAULT_CACHING_ENABLED", False)
    default_http2_support = env_bool("DEFAULT_HTTP2_SUPPORT", True)
    default_hsts_enabled = env_bool("DEFAULT_HSTS_ENABLED", False)
    default_force_ssl = env_bool("DEFAULT_FORCE_SSL", True)

    dry_run = env_bool("DRY_RUN", False)
    log_level = os.getenv("LOG_LEVEL", "INFO")

    delete_enabled = env_bool("DELETE_ENABLED", False)
    allow_empty_source = env_bool("ALLOW_EMPTY_SOURCE", False)
    max_delete_count = env_int("MAX_DELETE_COUNT", 0)
    max_delete_percent = env_float("MAX_DELETE_PERCENT", 0.0)
    force_delete = env_bool("FORCE_DELETE", False)

    cert_email = os.getenv("CERT_EMAIL", "")
    cert_agree_tos = env_bool("CERT_AGREE_TOS", False)
    cert_dns_challenge = env_bool("CERT_DNS_CHALLENGE", True)
    cert_dns_provider = os.getenv("CERT_DNS_PROVIDER", "")
    cert_dns_credentials = os.getenv("CERT_DNS_PROVIDER_CREDENTIALS", "")
    cert_dns_propagation_seconds = env_int("CERT_DNS_PROPAGATION_SECONDS", 30)
