"""GitHub REST client for the fleet sync.

Public repos read fine with zero auth (60 req/hr); a token raises the
ceiling to 5,000 req/hr and is REQUIRED for Dependabot alerts. Token
resolution order: GITHUB_TOKEN env, then the gh CLI's stored token
(the operator's own CLI auth — same account that pushes these repos).
Nothing is ever printed; tokens stay in memory.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

from services import GITHUB_API, GITHUB_RETRIES, GITHUB_TIMEOUT_S, GITHUB_UA, iso_z, utcnow


def _gh_cli_token() -> str | None:
    """Read the operator's own gh CLI token without printing it."""
    hosts = Path.home() / ".config" / "gh" / "hosts.yml"
    try:
        for line in hosts.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("oauth_token:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def resolve_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or _gh_cli_token()


def _get(path: str, token: str | None, params: dict | None = None) -> object:
    url = GITHUB_API + path
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url += "?" + qs
    headers = {"User-Agent": GITHUB_UA, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_err: Exception | None = None
    for attempt in range(GITHUB_RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=GITHUB_TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # network blip or rate limit; retry with backoff
            last_err = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"GitHub GET {path} failed after {GITHUB_RETRIES} tries: {last_err}")


class FleetGitHub:
    """Fetches per-repo state for every repo in fleet.yaml."""

    def __init__(self, owner: str, token: str | None = None):
        self.owner = owner
        self.token = token if token is not None else resolve_token()

    def fetch_repo(self, name: str) -> dict:
        base = f"/repos/{self.owner}/{name}"
        repo = _get(base, self.token)
        commits = _get(f"{base}/commits", self.token, {"per_page": 10, "sha": repo.get("default_branch", "main")})
        runs = _get(f"{base}/actions/runs", self.token, {"per_page": 5})
        pulls = _get(f"{base}/pulls", self.token, {"state": "open", "per_page": 30})
        deployments = _get(f"{base}/deployments", self.token, {"per_page": 5})
        alerts: list = []
        try:
            # Dependabot alerts need auth; unauthenticated callers get 404 here.
            alerts = _get(f"{base}/dependabot/alerts", self.token, {"state": "open", "per_page": 50})
            if not isinstance(alerts, list):
                alerts = []
        except RuntimeError:
            alerts = []

        def commit_row(c: dict) -> dict:
            inner = c.get("commit", {})
            committer = inner.get("committer", {}) or {}
            author = inner.get("author", {}) or {}
            return {
                "sha": (c.get("sha") or "")[:7],
                "fullSha": c.get("sha"),
                "message": (inner.get("message") or "").split("\n")[0],
                "committedAt": committer.get("date"),
                "author": (author.get("name") or c.get("author", {}).get("login") or "unknown"),
            }

        def run_row(r: dict) -> dict:
            return {
                "name": r.get("name"),
                "conclusion": r.get("conclusion"),
                "status": r.get("status"),
                "startedAt": r.get("run_started_at") or r.get("created_at"),
                "headSha": (r.get("head_sha") or "")[:7],
                "url": r.get("html_url"),
            }

        by_severity = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
        for a in alerts:
            sev = ((a.get("security_advisory") or {}).get("severity") or "low").lower()
            if sev in by_severity:
                by_severity[sev] += 1

        return {
            "repo": name,
            "defaultBranch": repo.get("default_branch"),
            "pushedAt": repo.get("pushed_at"),
            "commits": [commit_row(c) for c in (commits if isinstance(commits, list) else [])],
            "actionsRuns": [run_row(r) for r in (runs.get("workflow_runs", []) if isinstance(runs, dict) else [])],
            "openPulls": [
                {
                    "number": p.get("number"),
                    "title": p.get("title"),
                    "updatedAt": p.get("updated_at"),
                    "url": p.get("html_url"),
                    "author": (p.get("user") or {}).get("login"),
                }
                for p in (pulls if isinstance(pulls, list) else [])
            ],
            "deployments": deployments if isinstance(deployments, list) else [],
            "dependabot": {"total": len(alerts), "bySeverity": by_severity},
            "fetchedAt": iso_z(utcnow()),
        }
