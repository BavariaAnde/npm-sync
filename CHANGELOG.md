# Changelog

## Unreleased

## 0.1.2 - 2026-03-14

- Add file-based advanced_config profiles loaded from the hosts.yml directory
- Keep raw advanced_config snippets supported with validation for missing profiles
- Block profile usage on auth.andreas-goettl.de to prevent auth loops
- Add tests for profile resolution, raw snippets, and validation errors

## 0.1.1 - 2026-03-12

- Added minimal CI workflow
- Documented release process and forked image guidance
- Added web UI with run history and action overview
- Added history persistence via Docker volume
- Improved UI styling and readability
- Simplified UI controls and filtering
- Added per-host certificate selection (non-wildcard)
- Reverted automated Let's Encrypt DNS challenge certificate requests; only existing certificates are supported

## 0.1.0 - 2026-03-11

- Initial public release
- YAML-based host inventory
- Create and update proxy hosts
- Wildcard certificate reuse
- Docker support and GHCR workflow
- Documented public GHCR image usage and local build workflow
- Added open-source release docs and examples
