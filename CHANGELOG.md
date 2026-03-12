# Changelog

## Unreleased

- Added minimal CI workflow
- Documented release process and forked image guidance
- Added web UI with run history and action overview
- Added history persistence via Docker volume
- Improved UI styling and readability
- Simplified UI controls and filtering
- Added per-host certificate selection (non-wildcard)
- Added Let's Encrypt DNS challenge certificate requests via env configuration
- Fixed DNS provider credentials format for NPM certificate API
- Removed unsupported propagation_seconds from certificate payload

## 0.1.0 - 2026-03-11

- Initial public release
- YAML-based host inventory
- Create and update proxy hosts
- Wildcard certificate reuse
- Docker support and GHCR workflow
- Documented public GHCR image usage and local build workflow
- Added open-source release docs and examples
