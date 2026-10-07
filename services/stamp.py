"""Build-stamp injector.

Called during the web build (via web/scripts/prepare-public.cjs) so every
deployed bundle carries a stamp of exactly what was built:
web/public/stamp.json -> {repo, sha, builtAt, target}.

The sha comes from the git worktree being built; when git is unavailable
(e.g. a tarball build) it degrades to "unknown" instead of failing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from services import ROOT, iso_z, utcnow

PUBLIC_DIR = ROOT / "web" / "public"
STAMP_PATH = PUBLIC_DIR / "stamp.json"


def current_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        sha = out.stdout.strip()
        return sha or "unknown"
    except Exception:
        return "unknown"


def write_stamp(repo: str = "developer-command-center",
                target: str = "developer-command-center.web.app") -> dict:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    stamp = {
        "repo": repo,
        "sha": current_sha(),
        "builtAt": iso_z(utcnow()),
        "target": target,
    }
    STAMP_PATH.write_text(json.dumps(stamp, indent=1) + "\n", encoding="utf-8")
    return stamp


def read_stamp() -> dict | None:
    if not STAMP_PATH.exists():
        return None
    return json.loads(STAMP_PATH.read_text(encoding="utf-8"))
