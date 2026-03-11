import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request

from npm_sync.config import Settings
from npm_sync.npm_client import NPMClient
from npm_sync.syncer import Syncer, load_yaml

app = Flask(__name__)
RUN_LOCK = threading.Lock()
LAST_RUN: dict[str, Any] | None = None


def _load_users() -> dict[str, str]:
    users_raw = os.getenv("UI_USERS", "")
    users: dict[str, str] = {}
    for entry in users_raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        user, sep, pwd = entry.partition(":")
        if not sep:
            continue
        users[user] = pwd
    return users


def _auth_failed() -> Response:
    return Response(
        "Authentication required",
        status=401,
        headers={"WWW-Authenticate": 'Basic realm="npm-sync"'},
    )


def _require_auth() -> bool:
    users = _load_users()
    if not users:
        return False
    auth = request.authorization
    if not auth or auth.username not in users:
        return False
    return users[auth.username] == auth.password


def _history_path() -> Path:
    path = os.getenv("HISTORY_PATH", "/data/history.json")
    return Path(path)


def _read_history() -> list[dict[str, Any]]:
    path = _history_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _write_history(history: list[dict[str, Any]]) -> None:
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")


def _append_history(entry: dict[str, Any]) -> None:
    history = _read_history()
    history.insert(0, entry)
    max_items = int(os.getenv("HISTORY_MAX", "200") or "200")
    history = history[:max_items]
    _write_history(history)


def _build_summary(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in results:
        action = item.get("action", "unknown")
        counts[action] = counts.get(action, 0) + 1
    return counts


def _run_sync(dry_run: bool, config_path: str) -> dict[str, Any]:
    Settings.dry_run = dry_run
    client = NPMClient(
        base_url=Settings.npm_base_url,
        verify_ssl=Settings.npm_verify_ssl,
        token=Settings.npm_token,
        identity=Settings.npm_identity,
        secret=Settings.npm_secret,
    )
    client.authenticate()
    inventory = load_yaml(config_path)
    syncer = Syncer(client, Settings, inventory)
    results = syncer.sync()
    payload = [result.__dict__ for result in results]
    summary = _build_summary(payload)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "summary": summary,
        "results": payload,
    }
    global LAST_RUN
    LAST_RUN = entry
    _append_history(entry)
    return entry


@app.before_request
def _check_auth():
    if request.path.startswith("/api") or request.path == "/":
        if not _require_auth():
            return _auth_failed()
    return None


@app.get("/")
def index():
    return Response(
        """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>npm-sync</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #1a1a1a; }
    h1 { margin-bottom: 8px; }
    button { margin-right: 8px; padding: 8px 14px; }
    .summary { margin-top: 16px; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background: #f5f5f5; }
    .muted { color: #666; }
  </style>
</head>
<body>
  <h1>npm-sync</h1>
  <div class=\"muted\">Trigger a dry-run or apply changes and review results.</div>
  <div style=\"margin-top: 12px;\">
    <button onclick=\"runSync(true)\">Dry Run</button>
    <button onclick=\"runSync(false)\">Apply</button>
  </div>
  <div class=\"summary\" id=\"summary\"></div>
  <table id=\"results\" style=\"display:none;\">
    <thead>
      <tr>
        <th>Domain</th>
        <th>Action</th>
        <th>Details</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
  <script>
    async function fetchHistory() {
      const res = await fetch('/api/history');
      if (!res.ok) return;
      const history = await res.json();
      if (!history.length) return;
      render(history[0]);
    }

    function render(entry) {
      const summary = document.getElementById('summary');
      const resultsTable = document.getElementById('results');
      const tbody = resultsTable.querySelector('tbody');
      tbody.innerHTML = '';

      const summaryItems = Object.entries(entry.summary || {})
        .map(([key, value]) => `<strong>${key}</strong>: ${value}`)
        .join(' | ');

      summary.innerHTML = `<div><strong>Last run:</strong> ${entry.timestamp}</div>`
        + `<div><strong>Dry run:</strong> ${entry.dry_run}</div>`
        + `<div>${summaryItems || 'No results yet.'}</div>`;

      if (entry.results && entry.results.length) {
        resultsTable.style.display = '';
        for (const row of entry.results) {
          const tr = document.createElement('tr');
          const details = row.details ? JSON.stringify(row.details) : '';
          tr.innerHTML = `<td>${row.domain || ''}</td><td>${row.action || ''}</td><td><pre>${details}</pre></td>`;
          tbody.appendChild(tr);
        }
      } else {
        resultsTable.style.display = 'none';
      }
    }

    async function runSync(dryRun) {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: dryRun })
      });
      if (!res.ok) {
        alert('Run failed. Check logs.');
        return;
      }
      const data = await res.json();
      render(data);
    }

    fetchHistory();
  </script>
</body>
</html>
        """,
        mimetype="text/html",
    )


@app.get("/api/history")
def history():
    return jsonify(_read_history())


@app.post("/api/run")
def run():
    if RUN_LOCK.locked():
        return jsonify({"error": "Run already in progress"}), 409

    payload = request.get_json(silent=True) or {}
    dry_run = bool(payload.get("dry_run", True))
    config_path = payload.get("config_path", "/config/hosts.yml")

    with RUN_LOCK:
        entry = _run_sync(dry_run=dry_run, config_path=config_path)
    return jsonify(entry)


def main():
    logging.basicConfig(
        level=getattr(logging, Settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not Settings.npm_base_url:
        raise SystemExit("NPM_BASE_URL is required")

    if not Settings.npm_token and not (Settings.npm_identity and Settings.npm_secret):
        raise SystemExit("Provide NPM_TOKEN or both NPM_IDENTITY and NPM_SECRET")

    if not _load_users():
        raise SystemExit("UI_USERS must be set for basic auth")

    bind = os.getenv("UI_BIND", "0.0.0.0")
    port = int(os.getenv("UI_PORT", "8080"))
    app.run(host=bind, port=port)


if __name__ == "__main__":
    main()
