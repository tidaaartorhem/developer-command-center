"""developer-command-center build/fetch CLI.

  python3 services/main.py sync
      Fetch real GitHub state (commits, Actions runs, PRs, Dependabot,
      deployments) for every repo in fleet.yaml into data/github.json.

  python3 services/main.py build
      Read fleet.yaml + data/github.json + data/live-stamps.json, run the
      push-vs-live drift analysis, and write web/public/{fleet,drift,
      alerts}.json plus the build stamp web/public/stamp.json.

  python3 services/main.py stamps
      Print the current live stamps table.

Exits non-zero on ANY failure. Never fabricates data: UNKNOWN is a real
status, not a gap to fill in.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow `python3 services/main.py build` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from services import (  # noqa: E402
    ROOT,
    STATUS_LIVE,
    STATUS_STALE,
    STATUS_UNKNOWN,
    drift_status,
    fmt_gap,
    is_stale_pr,
    iso_z,
    parse_iso8601,
    utcnow,
)
from services import github_client as gh_mod  # noqa: E402
from services import stamp as stamp_mod  # noqa: E402

DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "web" / "public"
GITHUB_PATH = DATA_DIR / "github.json"
STAMPS_PATH = DATA_DIR / "live-stamps.json"

SOURCE_LABELS = {
    "firebase-hosting-release": "Firebase Hosting release",
    "apphosting-rollout": "App Hosting rollout",
    "manual-report": "Operator report",
}

TARGET_LABELS = {
    "firebase-hosting": "Firebase Hosting",
    "app-hosting": "App Hosting",
}


def load_fleet() -> dict:
    return yaml.safe_load((ROOT / "fleet.yaml").read_text(encoding="utf-8"))


def cmd_sync() -> int:
    fleet = load_fleet()
    client = gh_mod.FleetGitHub(fleet["owner"])
    repos = {}
    for entry in fleet["repos"]:
        name = entry["name"]
        print(f"[sync] fetching {name} ...", flush=True)
        repos[name] = client.fetch_repo(name)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GITHUB_PATH.write_text(
        json.dumps({"syncedAt": iso_z(utcnow()), "repos": repos}, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"[sync] wrote {GITHUB_PATH} ({len(repos)} repos)")
    return 0


def load_inputs() -> tuple[dict, dict, dict]:
    fleet = load_fleet()
    if not GITHUB_PATH.exists():
        raise SystemExit("data/github.json missing — run `python3 services/main.py sync` first.")
    github = json.loads(GITHUB_PATH.read_text(encoding="utf-8"))
    stamps = json.loads(STAMPS_PATH.read_text(encoding="utf-8")) if STAMPS_PATH.exists() else {"stamps": {}}
    return fleet, github, stamps.get("stamps", {})


def build_repo_view(entry: dict, gh: dict, stamp: dict | None) -> dict:
    commits = gh.get("commits", []) or []
    latest = commits[0] if commits else None
    runs = gh.get("actionsRuns", []) or []
    latest_run = runs[0] if runs else None
    stale_days = 14
    stale_prs = []
    for p in gh.get("openPulls", []) or []:
        if p.get("updatedAt") and is_stale_pr(p["updatedAt"], days=stale_days):
            days_stale = int((utcnow() - parse_iso8601(p["updatedAt"])).total_seconds() // 86400)
            stale_prs.append({**p, "daysStale": days_stale})
    stale_prs.sort(key=lambda p: p["daysStale"], reverse=True)

    committed_at = (latest or {}).get("committedAt")
    deployed_at = (stamp or {}).get("deployedAt")
    status, gap, evidence = drift_status(committed_at, deployed_at)
    gap_text = None
    if gap is not None:
        if gap > 0:
            gap_text = f"pushed {fmt_gap(gap)} after last deploy"
        elif gap < 0:
            gap_text = f"deployed {fmt_gap(-gap)} after last push"
        else:
            gap_text = "deployed at the same time as the last push"

    deployments = gh.get("deployments", []) or []
    target_kind = entry.get("target_kind", "firebase-hosting")
    return {
        "repo": entry["name"],
        "githubUrl": f"https://github.com/tidaaartorhem/{entry['name']}",
        "liveUrl": entry["live_url"],
        "targetKind": target_kind,
        "targetLabel": TARGET_LABELS.get(target_kind, target_kind),
        "drift": {"status": status, "gapText": gap_text, "evidence": evidence},
        "latestCommit": latest,
        "commitHistory": commits[:10],
        "actions": latest_run,
        "actionsHistory": runs[:5],
        "prs": {"open": len(gh.get("openPulls", []) or []), "stale": stale_prs},
        "dependabot": gh.get("dependabot", {"total": 0, "bySeverity": {}}),
        "githubDeployments": len(deployments),
        "githubDeploymentsNote": (
            "GitHub records no deployments for this fleet — deploys go out via "
            "Firebase CLI / App Hosting, which is why live stamps are tracked here."
            if not deployments
            else f"{len(deployments)} deployment record(s) on GitHub."
        ),
        "stamp": (
            {
                "deployedAt": stamp.get("deployedAt"),
                "source": stamp.get("source"),
                "sourceLabel": SOURCE_LABELS.get(stamp.get("source"), stamp.get("source")),
                "sha": stamp.get("sha"),
                "reportedAt": stamp.get("reportedAt"),
                "note": stamp.get("note"),
            }
            if stamp
            else None
        ),
    }


def build_alerts(views: list[dict]) -> list[dict]:
    alerts: list[dict] = []
    for v in views:
        repo, gurl = v["repo"], v["githubUrl"]
        if v["drift"]["status"] == STATUS_STALE:
            alerts.append({
                "severity": "high", "kind": "drift", "repo": repo,
                "title": f"{repo}: pushed but not live",
                "detail": v["drift"]["evidence"], "url": v["liveUrl"],
            })
        if v["drift"]["status"] == STATUS_UNKNOWN:
            alerts.append({
                "severity": "medium", "kind": "drift", "repo": repo,
                "title": f"{repo}: no live stamp recorded",
                "detail": v["drift"]["evidence"], "url": v["liveUrl"],
            })
        run = v.get("actions")
        if run and run.get("conclusion") == "failure":
            alerts.append({
                "severity": "high", "kind": "actions-failure", "repo": repo,
                "title": f"{repo}: latest Actions run failed",
                "detail": f"Workflow '{run.get('name')}' concluded with failure at {run.get('startedAt')}.",
                "url": run.get("url") or gurl,
            })
        for p in v["prs"]["stale"]:
            alerts.append({
                "severity": "low", "kind": "stale-pr", "repo": repo,
                "title": f"{repo}: PR #{p['number']} stale ({p['daysStale']}d)",
                "detail": f"\"{p['title']}\" by {p['author']} — no update since {p['updatedAt']}.",
                "url": p["url"],
            })
        dep = v.get("dependabot", {})
        sev = (dep.get("bySeverity") or {})
        if dep.get("total"):
            alerts.append({
                "severity": "high" if sev.get("critical") else "medium",
                "kind": "dependabot", "repo": repo,
                "title": f"{repo}: {dep['total']} open Dependabot alert(s)",
                "detail": "By severity: " + ", ".join(f"{k}={sev.get(k, 0)}" for k in ("critical", "high", "moderate", "low")),
                "url": f"{gurl}/security/dependabot",
            })
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(alerts, key=lambda a: (order[a["severity"]], a["repo"], a["title"]))


def _write(name: str, payload: dict) -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DIR / name).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


def cmd_build() -> int:
    fleet, github, stamps = load_inputs()
    computed_at = iso_z(utcnow())
    views = []
    for entry in fleet["repos"]:
        name = entry["name"]
        gh = (github.get("repos") or {}).get(name)
        if gh is None:
            raise SystemExit(f"No GitHub data for '{name}' — re-run sync.")
        views.append(build_repo_view(entry, gh, stamps.get(name)))

    def summary(v: dict) -> dict:
        return {
            "repo": v["repo"], "liveUrl": v["liveUrl"], "githubUrl": v["githubUrl"],
            "status": v["drift"]["status"], "gapText": v["drift"]["gapText"],
            "evidence": v["drift"]["evidence"],
            "committedAt": (v["latestCommit"] or {}).get("committedAt"),
            "deployedAt": (v["stamp"] or {}).get("deployedAt"),
            "message": (v["latestCommit"] or {}).get("message"),
        }

    stale = [summary(v) for v in views if v["drift"]["status"] == STATUS_STALE]
    live = [summary(v) for v in views if v["drift"]["status"] == STATUS_LIVE]
    unknown = [summary(v) for v in views if v["drift"]["status"] == STATUS_UNKNOWN]

    _write("fleet.json", {"computedAt": computed_at, "repos": views})
    _write("drift.json", {"computedAt": computed_at, "stale": stale, "live": live, "unknown": unknown})
    _write("alerts.json", {"computedAt": computed_at, "alerts": build_alerts(views)})
    stamp = stamp_mod.write_stamp()
    print(f"[build] fleet={len(views)} stale={len(stale)} live={len(live)} unknown={len(unknown)} "
          f"alerts={len(json.loads((PUBLIC_DIR/'alerts.json').read_text())['alerts'])}")
    print(f"[build] stamp: {stamp['repo']}@{stamp['sha']} -> {stamp['target']}")
    return 0


def cmd_stamps() -> int:
    _, _, stamps = load_inputs()
    for repo, s in sorted(stamps.items()):
        print(f"{repo:28s} {s.get('deployedAt')}  [{s.get('source')}]")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = (argv if argv is not None else sys.argv[1:])
    if not args or args[0] not in ("sync", "build", "stamps"):
        print(__doc__)
        return 2
    return {"sync": cmd_sync, "build": cmd_build, "stamps": cmd_stamps}[args[0]]()


if __name__ == "__main__":
    raise SystemExit(main())
