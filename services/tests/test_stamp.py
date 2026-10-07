"""Tests for the build-stamp injector round-trip."""

import json

from services import stamp as stamp_mod


def test_write_and_read_stamp_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(stamp_mod, "PUBLIC_DIR", tmp_path)
    monkeypatch.setattr(stamp_mod, "STAMP_PATH", tmp_path / "stamp.json")
    written = stamp_mod.write_stamp(repo="developer-command-center", target="developer-command-center.web.app")
    assert written["repo"] == "developer-command-center"
    assert written["target"] == "developer-command-center.web.app"
    assert written["builtAt"].endswith("Z")
    raw = json.loads((tmp_path / "stamp.json").read_text(encoding="utf-8"))
    assert raw == written
    assert stamp_mod.read_stamp() == written


def test_read_stamp_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(stamp_mod, "STAMP_PATH", tmp_path / "stamp.json")
    assert stamp_mod.read_stamp() is None


def test_current_sha_degrades_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(stamp_mod, "ROOT", tmp_path)  # not a git worktree
    # current_sha must not raise outside a git worktree
    assert stamp_mod.current_sha() == "unknown"
