"""Post-deploy CLI: report a live stamp back into the fleet.

Workflow: deploy a repo's site, then run

    python3 services/report_stamp.py <repo-name> [--at 2026-10-07T12:00:00Z] [--sha abc1234]

It appends {"deployedAt", "source": "manual-report", ...} to
data/live-stamps.json, which the next `build` folds into the drift board.
Without --at it stamps "now". Exits non-zero on unknown repo names.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import ROOT, iso_z, parse_iso8601, utcnow  # noqa: E402

DATA_DIR = ROOT / "data"
STAMPS_PATH = DATA_DIR / "live-stamps.json"


def load_fleet_names() -> list[str]:
    import yaml  # type: ignore

    fleet = yaml.safe_load((ROOT / "fleet.yaml").read_text(encoding="utf-8"))
    return [r["name"] for r in fleet["repos"]]


def load_stamps() -> dict:
    if STAMPS_PATH.exists():
        return json.loads(STAMPS_PATH.read_text(encoding="utf-8"))
    return {"stamps": {}}


def report(repo: str, deployed_at: str | None = None, sha: str | None = None) -> dict:
    names = load_fleet_names()
    if repo not in names:
        raise SystemExit(f"Unknown repo '{repo}'. Fleet repos: {', '.join(names)}")
    stamp = {
        "deployedAt": iso_z(parse_iso8601(deployed_at)) if deployed_at else iso_z(utcnow()),
        "source": "manual-report",
        "sha": sha,
        "reportedAt": iso_z(utcnow()),
        "note": "Reported by the operator after a manual deploy.",
    }
    data = load_stamps()
    data.setdefault("stamps", {})[repo] = stamp
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STAMPS_PATH.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    return stamp


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Report a live deploy stamp for a fleet repo.")
    ap.add_argument("repo", help="Repo name as listed in fleet.yaml")
    ap.add_argument("--at", dest="at", default=None, help="Deploy time (ISO-8601); defaults to now")
    ap.add_argument("--sha", default=None, help="Deployed commit SHA (short or full)")
    args = ap.parse_args(argv)
    stamp = report(args.repo, args.at, args.sha)
    print(json.dumps({args.repo: stamp}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
