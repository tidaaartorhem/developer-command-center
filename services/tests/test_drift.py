"""Tests for drift-status logic, gap formatting, and PR staleness."""

from datetime import datetime, timezone

from services import (
    STATUS_LIVE,
    STATUS_STALE,
    STATUS_UNKNOWN,
    drift_status,
    fmt_gap,
    is_stale_pr,
)


def test_stale_when_commit_newer_than_deploy():
    status, gap, evidence = drift_status("2026-10-06T12:59:30Z", "2026-10-06T12:58:54Z")
    assert status == STATUS_STALE
    assert gap == 36.0
    assert "12:59:30" in evidence and "12:58:54" in evidence


def test_live_when_deploy_covers_commit():
    status, gap, evidence = drift_status("2026-10-04T12:42:48Z", "2026-10-04T12:43:05Z")
    assert status == STATUS_LIVE
    assert gap == -17.0


def test_live_when_same_instant():
    status, gap, _ = drift_status("2026-10-04T12:43:05Z", "2026-10-04T12:43:05Z")
    assert status == STATUS_LIVE
    assert gap == 0.0


def test_unknown_when_no_stamp():
    status, gap, evidence = drift_status("2026-10-04T12:43:05Z", None)
    assert status == STATUS_UNKNOWN
    assert gap is None
    assert "report_stamp" in evidence


def test_unknown_when_no_commits():
    status, gap, _ = drift_status(None, "2026-10-04T12:43:05Z")
    assert status == STATUS_UNKNOWN
    assert gap is None


def test_unknown_when_both_missing():
    status, gap, _ = drift_status(None, None)
    assert status == STATUS_UNKNOWN
    assert gap is None


def test_fmt_gap_units():
    assert fmt_gap(43) == "43s"
    assert fmt_gap(90) == "1m 30s"
    assert fmt_gap(3600) == "1h"
    assert fmt_gap(5400) == "1h 30m"
    assert fmt_gap(90000) == "1d 1h"
    assert fmt_gap(172800) == "2d"


def test_is_stale_pr_threshold():
    now = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    assert is_stale_pr("2026-09-10T00:00:00Z", now=now) is True  # 27 days
    assert is_stale_pr("2026-10-06T12:00:00Z", now=now) is False  # 1 day
    assert is_stale_pr("2026-09-23T12:00:00Z", now=now) is False  # exactly 14d -> not over
    assert is_stale_pr("2026-09-23T11:59:00Z", now=now) is True  # 14d + 1m -> over
