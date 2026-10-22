"""Tests for the fleet build: repo views and alert assembly."""

from datetime import timedelta

from services import iso_z, utcnow
from services.main import build_alerts, build_repo_view


def _entry(name="f1-race-weekend-os", kind="firebase-hosting"):
    return {
        "name": name,
        "live_url": f"https://{name}.web.app",
        "target_kind": kind,
        "notes": "",
    }


def _gh(**over):
    base = {
        "commits": [
            {"sha": "a6f0840", "fullSha": "a6f0840" + "0" * 33, "message": "refresh computedAt",
             "committedAt": "2026-10-06T12:59:30Z", "author": "Aadit Mehrotra"},
        ],
        "actionsRuns": [
            {"name": "CI", "conclusion": "success", "status": "completed",
             "startedAt": "2026-10-06T12:59:40Z", "headSha": "a6f0840", "url": "https://example.com/run"},
        ],
        "openPulls": [],
        "deployments": [],
        "dependabot": {"total": 0, "bySeverity": {"critical": 0, "high": 0, "moderate": 0, "low": 0}},
    }
    base.update(over)
    return base


def _stamp(**over):
    base = {"deployedAt": "2026-10-06T12:58:54Z", "source": "firebase-hosting-release",
            "sha": None, "reportedAt": "2026-10-07T12:00:00Z", "note": "real release history"}
    base.update(over)
    return base


def test_view_stale_when_push_after_deploy():
    v = build_repo_view(_entry(), _gh(), _stamp())
    assert v["drift"]["status"] == "STALE"
    assert v["drift"]["gapText"] == "pushed 36s after last deploy"
    assert v["stamp"]["sourceLabel"] == "Firebase Hosting release"
    assert v["targetLabel"] == "Firebase Hosting"


def test_view_live_when_deploy_covers_push():
    v = build_repo_view(_entry(), _gh(), _stamp(deployedAt="2026-10-06T13:00:00Z"))
    assert v["drift"]["status"] == "LIVE"
    assert "after last push" in v["drift"]["gapText"]


def test_view_unknown_without_stamp():
    v = build_repo_view(_entry(), _gh(), None)
    assert v["drift"]["status"] == "UNKNOWN"
    assert v["stamp"] is None


def test_view_marks_stale_prs():
    # The "fresh" PR is anchored 3 days before the actual run time so it stays
    # non-stale forever; the hard-coded 2026-10-06 fixture below became stale
    # on 2026-10-20 and made this test a time bomb.
    fresh_at = iso_z(utcnow() - timedelta(days=3))
    gh = _gh(openPulls=[
        {"number": 3, "title": "Bump deps", "updatedAt": "2026-09-01T00:00:00Z",
         "url": "https://example.com/pr/3", "author": "dependabot"},
        {"number": 4, "title": "Fresh PR", "updatedAt": fresh_at,
         "url": "https://example.com/pr/4", "author": "aadit"},
    ])
    v = build_repo_view(_entry(), gh, _stamp())
    assert v["prs"]["open"] == 2
    assert [p["number"] for p in v["prs"]["stale"]] == [3]
    assert v["prs"]["stale"][0]["daysStale"] >= 14


def test_view_notes_empty_github_deployments():
    v = build_repo_view(_entry(), _gh(), _stamp())
    assert v["githubDeployments"] == 0
    assert "no deployments" in v["githubDeploymentsNote"]


def test_alerts_cover_drift_pr_dependabot_and_failed_actions():
    gh = _gh(
        actionsRuns=[{"name": "CI", "conclusion": "failure", "status": "completed",
                      "startedAt": "2026-10-06T12:59:40Z", "headSha": "a6f0840",
                      "url": "https://example.com/run"}],
        openPulls=[{"number": 3, "title": "Bump deps", "updatedAt": "2026-09-01T00:00:00Z",
                    "url": "https://example.com/pr/3", "author": "dependabot"}],
        dependabot={"total": 2, "bySeverity": {"critical": 1, "high": 1, "moderate": 0, "low": 0}},
    )
    v = build_repo_view(_entry(), gh, _stamp())  # commit 12:59:30 > deploy 12:58:54 -> STALE
    alerts = build_alerts([v])
    kinds = {a["kind"] for a in alerts}
    assert {"drift", "actions-failure", "stale-pr", "dependabot"} <= kinds
    assert alerts[0]["severity"] == "high"  # sorted: high first
    drift = next(a for a in alerts if a["kind"] == "drift")
    assert drift["severity"] == "high"


def test_alerts_empty_for_healthy_repo():
    v = build_repo_view(_entry(), _gh(), _stamp(deployedAt="2026-10-06T13:00:00Z"))
    assert build_alerts([v]) == []
