import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request

from npm_sync.config import Settings
from npm_sync.npm_client import NPMClient
from npm_sync.syncer import Syncer, load_inventory, InventoryValidationError

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
    raw = os.getenv("HISTORY_PATH", "/app/data/history.json")
    path = Path(raw)
    if not path.is_absolute():
        path = Path("/app/data") / path
    return path


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
    if not Settings.npm_base_url:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "error": "NPM_BASE_URL is required",
        }

    if not Settings.npm_token and not (Settings.npm_identity and Settings.npm_secret):
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "error": "Provide NPM_TOKEN or both NPM_IDENTITY and NPM_SECRET",
        }

    start = time.monotonic()
    Settings.dry_run = dry_run
    client = NPMClient(
        base_url=Settings.npm_base_url,
        verify_ssl=Settings.npm_verify_ssl,
        token=Settings.npm_token,
        identity=Settings.npm_identity,
        secret=Settings.npm_secret,
    )
    client.authenticate()
    inventory = load_inventory(config_path)
    try:
        syncer = Syncer(client, Settings, inventory)
    except InventoryValidationError as exc:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "error": str(exc),
        }
    results = syncer.sync()
    payload = [result.__dict__ for result in results]
    summary = _build_summary(payload)
    duration_ms = int((time.monotonic() - start) * 1000)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "duration_ms": duration_ms,
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
    :root {
      --bg: #0e1116;
      --panel: #141a25;
      --panel-2: #1a2231;
      --text: #e6e9ef;
      --muted: #aab2c0;
      --accent: #6ad6a7;
      --green: #6ad6a7;
      --yellow: #f2c14e;
      --red: #ff7b7b;
      --blue: #63a5ff;
      --border: #2a3245;
    }
    * { box-sizing: border-box; }
    body { font-family: \"Segoe UI\", system-ui, sans-serif; margin: 0; background: var(--bg); color: var(--text); }
    header { padding: 20px 28px; border-bottom: 1px solid var(--border); background: var(--panel); position: sticky; top: 0; }
    h1 { margin: 0; font-size: 22px; }
    .muted { color: var(--muted); }
    .wrap { padding: 24px 28px; }
    .tabs { display: inline-flex; gap: 6px; margin-bottom: 12px; background: var(--panel); border: 1px solid var(--border); padding: 4px; border-radius: 999px; }
    .tab { padding: 8px 14px; border: none; background: transparent; color: var(--muted); cursor: pointer; border-radius: 999px; font-weight: 600; }
    .tab.active { background: var(--panel-2); color: var(--text); }
    .actions { display: flex; gap: 10px; margin: 8px 0 16px; }
    button { padding: 10px 16px; border-radius: 10px; border: none; cursor: pointer; color: #0b0d12; font-weight: 700; }
    .btn-dry { background: var(--yellow); }
    .btn-apply { background: var(--green); }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 12px; }
    .card { background: var(--panel); border: 1px solid var(--border); padding: 12px; border-radius: 10px; }
    .card .label { font-size: 12px; color: var(--muted); }
    .card .value { font-size: 20px; font-weight: 600; margin-top: 6px; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
    th { background: var(--panel-2); font-weight: 600; }
    tr:hover td { background: #1a2030; }
    .badge { padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; display: inline-block; }
    .b-create { background: rgba(67, 209, 158, 0.2); color: var(--green); }
    .b-update { background: rgba(75, 179, 253, 0.2); color: var(--blue); }
    .b-delete { background: rgba(255, 107, 107, 0.2); color: var(--red); }
    .b-unchanged { background: rgba(170, 178, 192, 0.2); color: var(--muted); }
    .b-skip { background: rgba(246, 195, 68, 0.2); color: var(--yellow); }
    pre { white-space: pre-wrap; margin: 0; color: var(--muted); }
    .hidden { display: none; }
    .history-list { display: grid; gap: 10px; }
    .history-item { padding: 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--panel); cursor: pointer; }
    .history-item.active { border-color: var(--accent); background: var(--panel-2); }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 900px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>npm-sync</h1>
    <div class=\"muted\">Manage Nginx Proxy Manager with a declarative inventory.</div>
  </header>
  <div class=\"wrap\">
    <div class=\"tabs\">
      <button class=\"tab active\" data-tab=\"runs\" onclick=\"switchTab('runs')\">Runs</button>
      <button class=\"tab\" data-tab=\"history\" onclick=\"switchTab('history')\">History</button>
    </div>

    <div id=\"tab-runs\">
      <div class=\"actions\">
        <button class=\"btn-dry\" onclick=\"runSync(true)\">Dry Run</button>
        <button class=\"btn-apply\" onclick=\"runSync(false)\">Apply</button>
      </div>

      <div id=\"summary\"></div>

      <div style=\"margin-top: 12px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center;\">
        <input id=\"search\" placeholder=\"Search domain\" style=\"min-width:220px;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--panel);color:var(--text);\" />
        <select id=\"action-filter\" style=\"padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--panel);color:var(--text);\">
          <option value=\"all\">Action: All</option>
          <option value=\"changes\">Action: Changes only</option>
          <option value=\"would-create\">would-create</option>
          <option value=\"would-update\">would-update</option>
          <option value=\"would-delete\">would-delete</option>
          <option value=\"created\">created</option>
          <option value=\"updated\">updated</option>
          <option value=\"deleted\">deleted</option>
          <option value=\"unchanged\">unchanged</option>
          <option value=\"skipped-disabled\">skipped-disabled</option>
        </select>
      </div>

      <table id=\"results\" class=\"hidden\">
        <thead>
          <tr>
            <th>Domain</th>
            <th>Action</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>

    <div id=\"tab-history\" class=\"hidden\">
      <div class=\"row\">
        <div>
          <div class=\"muted\">Recent runs</div>
          <div id=\"history-list\" class=\"history-list\" style=\"margin-top: 12px;\"></div>
        </div>
        <div>
          <div class=\"muted\">Selected run</div>
          <div id=\"history-detail\" style=\"margin-top: 12px;\"></div>
        </div>
      </div>
    </div>
  </div>
  <script>
    let cachedHistory = [];
    let currentEntry = null;

    async function fetchHistory() {
      const res = await fetch('/api/history');
      if (!res.ok) return;
      const history = await res.json();
      cachedHistory = history || [];
      if (cachedHistory.length) {
        render(cachedHistory[0]);
      }
      renderHistoryList();
    }

    function render(entry) {
      currentEntry = entry;
      const summary = document.getElementById('summary');
      const summaryItems = Object.entries(entry.summary || {}).filter(([, value]) => value !== 0);
      const cards = summaryItems.map(([key, value]) => {
        return `<div class=\"card\"><div class=\"label\">${key}</div><div class=\"value\">${value}</div></div>`;
      }).join('');

      const duration = entry.duration_ms ? `${entry.duration_ms} ms` : 'n/a';
      summary.innerHTML = `
        <div class=\"card\">
          <div class=\"label\">Last run</div>
          <div class=\"value\">${entry.timestamp || 'n/a'}</div>
          <div class=\"muted\">Dry run: ${entry.dry_run ? 'true' : 'false'} · Duration: ${duration}</div>
        </div>
        <div class=\"cards\">${cards || ''}</div>
      `;

      renderResults();
    }

    function renderResults() {
      const resultsTable = document.getElementById('results');
      const tbody = resultsTable.querySelector('tbody');
      tbody.innerHTML = '';

      if (!currentEntry || !currentEntry.results) {
        resultsTable.classList.add('hidden');
        return;
      }

      const search = document.getElementById('search').value.toLowerCase();
      const actionFilter = document.getElementById('action-filter').value;

      let rows = currentEntry.results.filter(row => {
        const action = row.action || '';
        if (search && !(row.domain || '').toLowerCase().includes(search)) return false;
        if (actionFilter === 'changes') {
          if (!row.details || Object.keys(row.details).length === 0) return false;
        } else if (actionFilter !== 'all' && action !== actionFilter) {
          return false;
        }
        return true;
      });

      rows.sort((a, b) => (a.domain || '').localeCompare(b.domain || ''));

      if (rows.length) {
        resultsTable.classList.remove('hidden');
        for (const row of rows) {
          const tr = document.createElement('tr');
          const details = row.details ? JSON.stringify(row.details, null, 2) : '';
          const badge = actionBadge(row.action || '');
          tr.innerHTML = `<td>${row.domain || ''}</td><td>${badge}</td><td><pre>${details}</pre></td>`;
          tbody.appendChild(tr);
        }
      } else {
        resultsTable.classList.add('hidden');
      }
    }

    function actionBadge(action) {
      const map = {
        'would-create': 'b-create',
        'created': 'b-create',
        'would-update': 'b-update',
        'updated': 'b-update',
        'would-delete': 'b-delete',
        'deleted': 'b-delete',
        'unchanged': 'b-unchanged',
        'skipped-disabled': 'b-skip'
      };
      const cls = map[action] || 'b-unchanged';
      return `<span class=\"badge ${cls}\">${action}</span>`;
    }

    function renderHistoryList() {
      const list = document.getElementById('history-list');
      list.innerHTML = '';
      if (!cachedHistory.length) {
        list.innerHTML = '<div class=\"muted\">No history yet.</div>';
        return;
      }
      cachedHistory.forEach((item, idx) => {
        const div = document.createElement('div');
        div.className = 'history-item' + (idx === 0 ? ' active' : '');
        div.onclick = () => selectHistory(idx);
        const summary = Object.entries(item.summary || {}).map(([k, v]) => `${k}: ${v}`).join(' | ');
        div.innerHTML = `<div><strong>${item.timestamp || 'n/a'}</strong></div><div class=\"muted\">Dry run: ${item.dry_run ? 'true' : 'false'}</div><div class=\"muted\">${summary}</div>`;
        list.appendChild(div);
      });
      selectHistory(0);
    }

    function selectHistory(index) {
      const list = document.getElementById('history-list');
      Array.from(list.children).forEach((el, i) => {
        el.classList.toggle('active', i === index);
      });
      const entry = cachedHistory[index];
      const detail = document.getElementById('history-detail');
      if (!entry) {
        detail.innerHTML = '<div class=\"muted\">Select a run.</div>';
        return;
      }
      const summary = Object.entries(entry.summary || {}).map(([k, v]) => `${k}: ${v}`).join(' | ');
      detail.innerHTML = `
        <div class=\"card\">
          <div class=\"label\">Run</div>
          <div class=\"value\">${entry.timestamp || 'n/a'}</div>
          <div class=\"muted\">Dry run: ${entry.dry_run ? 'true' : 'false'}</div>
          <div class=\"muted\">${summary}</div>
        </div>
        <div style=\"margin-top: 10px;\">
          <label class=\"muted\" style=\"display:flex;align-items:center;gap:6px;\">\n            <input id=\"history-changes-only\" type=\"checkbox\" onchange=\"renderHistoryDetail(${index})\" /> Show changes only\n          </label>\n        </div>
        <div id=\"history-table\" style=\"margin-top: 12px;\"></div>
      `;
      renderHistoryDetail(index);
    }

    function renderHistoryDetail(index) {
      const entry = cachedHistory[index];
      const changesOnly = document.getElementById('history-changes-only')?.checked;
      const rows = (entry.results || []).filter(row => {
        if (!changesOnly) return true;
        return row.details && Object.keys(row.details).length > 0;
      });
      const table = `
        <table>
          <thead><tr><th>Domain</th><th>Action</th><th>Details</th></tr></thead>
          <tbody>
            ${rows.map(row => {
              const details = row.details ? JSON.stringify(row.details, null, 2) : '';
              return `<tr><td>${row.domain || ''}</td><td>${actionBadge(row.action || '')}</td><td><pre>${details}</pre></td></tr>`;
            }).join('')}
          </tbody>
        </table>
      `;
      document.getElementById('history-table').innerHTML = table;
    }

    function switchTab(name) {
      document.querySelectorAll('.tab[data-tab]').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === name);
      });
      document.getElementById('tab-runs').classList.toggle('hidden', name !== 'runs');
      document.getElementById('tab-history').classList.toggle('hidden', name !== 'history');
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
      cachedHistory = [data, ...cachedHistory];
      renderHistoryList();
      render(data);
    }

    document.getElementById('search').addEventListener('input', renderResults);
    document.getElementById('action-filter').addEventListener('change', renderResults);

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
    if "error" in entry:
        return jsonify(entry), 400
    return jsonify(entry)


def main():
    logging.basicConfig(
        level=getattr(logging, Settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not _load_users():
        raise SystemExit("UI_USERS must be set for basic auth")

    bind = os.getenv("UI_BIND", "0.0.0.0")
    port = int(os.getenv("UI_PORT", "8080"))
    app.run(host=bind, port=port)


if __name__ == "__main__":
    main()
