import os
from dotenv import load_dotenv

load_dotenv()

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

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
