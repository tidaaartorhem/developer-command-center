"""developer-command-center services package.

Shared constants and small helpers. Pure functions only — importing this
module never exits, never touches the network, and never reads secrets.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- GitHub ----------------------------------------------------------------------
GITHUB_API = "https://api.github.com"
GITHUB_TIMEOUT_S = 25
GITHUB_RETRIES = 3
GITHUB_UA = "developer-command-center/1.0 (+https://github.com/tidaaartorhem/developer-command-center)"

# --- Drift -----------------------------------------------------------------------
# PRs untouched for longer than this count as stale.
STALE_PR_DAYS = 14

# Drift statuses.
STATUS_LIVE = "LIVE"  # last known live stamp covers the latest main commit
STATUS_STALE = "STALE"  # main was pushed after the last known live stamp
STATUS_UNKNOWN = "UNKNOWN"  # no live stamp recorded yet for this target


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def utcnow() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def iso_z(dt: datetime) -> str:
    """Format an aware datetime as ISO-8601 with a trailing Z."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_gap(seconds: float) -> str:
    """Human gap copy: 43 -> '43s', 90 -> '1m 30s', 5400 -> '1h 30m', 90000 -> '1d 1h'."""
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m {total % 60:02d}s".rstrip("0").rstrip() if total % 60 else f"{total // 60}m"
    if total < 86400:
        h, rem = divmod(total, 3600)
        return f"{h}h {rem // 60:02d}m".rstrip("0").rstrip() if rem // 60 else f"{h}h"
    d, rem = divmod(total, 86400)
    return f"{d}d {rem // 3600}h" if rem // 3600 else f"{d}d"


def drift_status(committed_at: str | None, deployed_at: str | None) -> tuple[str, float | None, str]:
    """Push-vs-live drift for one repo.

    Returns (status, gap_seconds, evidence). gap_seconds is
    committed_at - deployed_at when both are known. Strict comparison:
    ANY main commit newer than the last known live stamp is STALE — the
    gap text lets the operator judge whether it matters.
    """
    if not committed_at:
        return STATUS_UNKNOWN, None, "No commits found on the default branch."
    if not deployed_at:
        return STATUS_UNKNOWN, None, (
            "No live stamp recorded for this deploy target yet. Deploy, then run "
            "`python3 services/report_stamp.py <repo>` to record one."
        )
    commit_dt = parse_iso8601(committed_at)
    deploy_dt = parse_iso8601(deployed_at)
    gap = (commit_dt - deploy_dt).total_seconds()
    if gap > 0:
        return (
            STATUS_STALE,
            gap,
            f"Latest main commit ({committed_at}) is newer than the last known live "
            f"stamp ({deployed_at}) — pushed {fmt_gap(gap)} after the last deploy finished.",
        )
    return (
        STATUS_LIVE,
        gap,
        f"Last known live stamp ({deployed_at}) covers the latest main commit ({committed_at}).",
    )


def is_stale_pr(updated_at: str, now: datetime | None = None, days: int = STALE_PR_DAYS) -> bool:
    """True when a PR's updated_at is older than the staleness threshold."""
    now = now or utcnow()
    return (now - parse_iso8601(updated_at)).total_seconds() > days * 86400
