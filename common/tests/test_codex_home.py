"""Tests for common.session.codex_home — per-run CODEX_HOME isolation.

Covers the concurrency-safety contract that fixes side-by-side Codex reviews
stepping over each other: isolated session dirs, a crash-safe manifest with
secure (symlink-proof) appends, validated reuse, and a delimiter-bounded
terminal cleanup that never touches a neighboring review's homes.
"""

import json
import os
import stat
import tempfile
import threading
import time
from pathlib import Path

import pytest

from common.metadata.extractors import _codex_session_files
from common.session import (
    cleanup_review_homes,
    default_manifest,
    record_codex_home,
    reuse_codex_home,
    setup_codex_home,
    teardown_codex_home,
)
from common.session import codex_home as ch


@pytest.fixture
def tmp_root(tmp_path, monkeypatch):
    """Point tempfile at tmp_path so mkdtemp() homes and the containment check
    (_temp_root) agree, keeping every test hermetic."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return tmp_path


@pytest.fixture
def real_home(tmp_path):
    """A fake real ~/.codex with the allowlisted files plus mutable state that
    must NOT be copied into the per-run home."""
    src = tmp_path / "real-codex"
    src.mkdir()
    (src / "auth.json").write_text('{"token": "secret"}')
    (src / "config.toml").write_text('model = "gpt-5.5"')
    (src / "history.jsonl").write_text("mutable runtime state")
    (src / "sessions").mkdir()
    return src


def _manifest(tmp_root, prefix="ppr-t"):
    return str(tmp_root / f"{prefix}-codex-homes.list")


class TestSetup:
    def test_isolated_home_allowlist_and_perms(self, tmp_root, real_home):
        manifest = _manifest(tmp_root)
        home, ok = setup_codex_home(manifest, real_home=str(real_home))
        assert ok and home
        assert os.path.isdir(os.path.join(home, "sessions"))
        assert os.path.exists(os.path.join(home, "auth.json"))
        assert os.path.exists(os.path.join(home, "config.toml"))
        # mutable runtime state is never snapshotted
        assert not os.path.exists(os.path.join(home, "history.jsonl"))
        assert stat.S_IMODE(os.stat(home).st_mode) == 0o700
        assert stat.S_IMODE(os.stat(os.path.join(home, "auth.json")).st_mode) == 0o600
        # recorded in the manifest (before credentials were populated)
        assert home in open(manifest).read()

    def test_missing_real_files_still_succeeds(self, tmp_root, tmp_path):
        empty = tmp_path / "empty-real"
        empty.mkdir()
        home, ok = setup_codex_home(_manifest(tmp_root), real_home=str(empty))
        assert ok and os.path.isdir(os.path.join(home, "sessions"))

    def test_populate_failure_rolls_back(self, tmp_root, real_home, monkeypatch):
        import shutil

        # Home + manifest record succeed; the credential copy fails.
        def boom(*a, **k):
            raise OSError("disk full")

        monkeypatch.setattr(shutil, "copy2", boom)
        home, ok = setup_codex_home(_manifest(tmp_root), real_home=str(real_home))
        assert (home, ok) == (None, False)
        # no half-populated credential dir is left behind
        leftovers = list(tmp_root.glob(ch._HOME_PREFIX + "*"))
        assert leftovers == []

    def test_record_failure_rolls_back(self, tmp_root, real_home, monkeypatch):
        def boom(*a, **k):
            raise OSError("manifest unwritable")

        monkeypatch.setattr(ch, "record_codex_home", boom)
        home, ok = setup_codex_home(_manifest(tmp_root), real_home=str(real_home))
        assert (home, ok) == (None, False)
        assert list(tmp_root.glob(ch._HOME_PREFIX + "*")) == []


class TestReuse:
    def test_valid_home_reused(self, tmp_root, real_home):
        home, _ = setup_codex_home(_manifest(tmp_root), real_home=str(real_home))
        assert reuse_codex_home(home) is True

    def test_missing_rejected(self, tmp_root):
        assert reuse_codex_home(str(tmp_root / "ppr-codex-home-gone")) is False

    def test_symlink_rejected(self, tmp_root, real_home):
        home, _ = setup_codex_home(_manifest(tmp_root), real_home=str(real_home))
        link = tmp_root / "ppr-codex-home-link"
        link.symlink_to(home)
        assert reuse_codex_home(str(link)) is False

    def test_foreign_prefix_rejected(self, tmp_root):
        d = tmp_root / "not-a-codex-home"
        d.mkdir()
        (d / "sessions").mkdir()
        assert reuse_codex_home(str(d)) is False

    def test_outside_tmp_rejected(self, tmp_path, monkeypatch):
        # A prefixed dir that lives outside the temp root must not validate.
        # Point the temp root at a subdir so a sibling dir is genuinely outside
        # it (pytest's tmp_path is itself under the system temp dir on macOS).
        temp_sub = tmp_path / "tmproot"
        temp_sub.mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(temp_sub))
        outside = tmp_path / "outside" / "ppr-codex-home-x"
        outside.mkdir(parents=True)
        (outside / "sessions").mkdir()
        assert reuse_codex_home(str(outside)) is False


class TestSessionScoping:
    def test_session_files_scoped_to_home(self, tmp_root, real_home):
        a, _ = setup_codex_home(_manifest(tmp_root, "ppr-a"), real_home=str(real_home))
        b, _ = setup_codex_home(_manifest(tmp_root, "ppr-b"), real_home=str(real_home))
        (Path(a) / "sessions" / "rollout-a.jsonl").write_text("{}")
        (Path(b) / "sessions" / "rollout-b.jsonl").write_text("{}")
        files_a = _codex_session_files(a)
        assert any("rollout-a" in f for f in files_a)
        assert not any("rollout-b" in f for f in files_a)


class TestManifestSecurity:
    def test_record_rejects_symlinked_manifest(self, tmp_root, tmp_path):
        target = tmp_path / "victim.txt"
        target.write_text("original")
        manifest = tmp_root / "ppr-evil-codex-homes.list"
        manifest.symlink_to(target)
        with pytest.raises(OSError):
            record_codex_home(str(manifest), "/some/home")
        # the symlink target was not followed / corrupted
        assert target.read_text() == "original"

    def test_read_rejects_symlinked_manifest(self, tmp_root, tmp_path):
        target = tmp_path / "data.txt"
        target.write_text("/tmp/ppr-codex-home-injected\n")
        manifest = tmp_root / "ppr-evil2-codex-homes.list"
        manifest.symlink_to(target)
        assert ch._read_manifest(str(manifest)) == []

    def test_concurrent_appends_are_intact(self, tmp_root):
        manifest = _manifest(tmp_root, "ppr-conc")
        lines = [f"/tmp/ppr-codex-home-{i:04d}" for i in range(200)]

        def worker(line):
            record_codex_home(manifest, line)

        threads = [threading.Thread(target=worker, args=(ln,)) for ln in lines]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        got = [ln.strip() for ln in open(manifest) if ln.strip()]
        assert sorted(got) == sorted(lines)  # no torn/interleaved lines


class TestCleanup:
    def test_union_manifest_and_sessions_removed(self, tmp_root, real_home):
        manifest = _manifest(tmp_root, "ppr-rev")
        h1, _ = setup_codex_home(manifest, real_home=str(real_home))
        h2, _ = setup_codex_home(manifest, real_home=str(real_home))
        # h1 referenced only by a session file (not directly re-derivable)
        (tmp_root / "ppr-rev-session.json").write_text(json.dumps({"codex_home": h1}))
        (tmp_root / "ppr-rev-verify-B1-session.json").write_text(json.dumps({"codex_home": h2}))
        assert cleanup_review_homes(str(tmp_root), "ppr-rev") == 0
        assert not os.path.exists(h1) and not os.path.exists(h2)
        assert not os.path.exists(manifest)

    def test_idempotent(self, tmp_root, real_home):
        manifest = _manifest(tmp_root, "ppr-idem")
        h, _ = setup_codex_home(manifest, real_home=str(real_home))
        (tmp_root / "ppr-idem-session.json").write_text(json.dumps({"codex_home": h}))
        assert cleanup_review_homes(str(tmp_root), "ppr-idem") == 0
        assert cleanup_review_homes(str(tmp_root), "ppr-idem") == 0  # no error second time

    def test_overlapping_id_isolation(self, tmp_root, real_home):
        m1 = _manifest(tmp_root, "qr-demo")
        m2 = _manifest(tmp_root, "qr-demo2")
        keep, _ = setup_codex_home(m2, real_home=str(real_home))
        (tmp_root / "qr-demo2-r1-session.json").write_text(json.dumps({"codex_home": keep}))
        go, _ = setup_codex_home(m1, real_home=str(real_home))
        (tmp_root / "qr-demo-r1-session.json").write_text(json.dumps({"codex_home": go}))
        assert cleanup_review_homes(str(tmp_root), "qr-demo") == 0
        assert not os.path.exists(go)
        assert os.path.exists(keep)  # qr-demo2 untouched by qr-demo cleanup

    def test_partial_failure_keeps_survivors(self, tmp_root):
        # A real but unowned-prefix dir in the manifest cannot be torn down →
        # cleanup must retain it (rewritten manifest) and return nonzero.
        manifest = tmp_root / "ppr-part-codex-homes.list"
        foreign = tmp_root / "foreign-dir"
        foreign.mkdir()
        manifest.write_text(str(foreign) + "\n")
        remaining = cleanup_review_homes(str(tmp_root), "ppr-part")
        assert remaining == 1
        assert manifest.exists()
        assert str(foreign) in manifest.read_text()
        assert foreign.exists()  # refused, not removed


class TestGlobalManifestSweep:
    """Homes recorded via ``default_manifest(None)`` (no explicit review-scoped
    manifest) carry no review id, so no single review's ``cleanup_review_homes``
    call would ever reach them without the age-gated global sweep."""

    def test_stale_global_entry_reclaimed(self, tmp_root, real_home):
        manifest = default_manifest(None)
        home, ok = setup_codex_home(manifest, real_home=str(real_home))
        assert ok
        stale_time = time.time() - ch._STALE_HOME_AGE_SECONDS - 3600
        os.utime(home, (stale_time, stale_time))

        # A cleanup call for an unrelated review still sweeps the orphan.
        remaining = cleanup_review_homes(str(tmp_root), "ppr-unrelated")
        assert remaining == 0
        assert not os.path.exists(home)
        global_manifest = tmp_root / ch._GLOBAL_MANIFEST_NAME
        assert not global_manifest.exists()

    def test_fresh_global_entry_left_alone(self, tmp_root, real_home):
        manifest = default_manifest(None)
        home, ok = setup_codex_home(manifest, real_home=str(real_home))
        assert ok

        # Freshly created — must survive an unrelated review's cleanup call.
        remaining = cleanup_review_homes(str(tmp_root), "ppr-unrelated")
        assert remaining == 0
        assert os.path.exists(home)
        global_manifest = tmp_root / ch._GLOBAL_MANIFEST_NAME
        assert global_manifest.exists()
        assert home in global_manifest.read_text()

    def test_stale_entry_owned_by_same_review_not_double_processed(self, tmp_root, real_home):
        # A home already reclaimed via the per-review manifest/session files
        # must be dropped from the global manifest without a second teardown
        # attempt (which would otherwise be a silent no-op, but exercises the
        # already_seen skip path explicitly).
        manifest = _manifest(tmp_root, "ppr-dup")
        home, ok = setup_codex_home(manifest, real_home=str(real_home))
        assert ok
        global_manifest = tmp_root / ch._GLOBAL_MANIFEST_NAME
        global_manifest.write_text(home + "\n")
        (tmp_root / "ppr-dup-session.json").write_text(json.dumps({"codex_home": home}))

        remaining = cleanup_review_homes(str(tmp_root), "ppr-dup")
        assert remaining == 0
        assert not os.path.exists(home)
        assert not global_manifest.exists()


class TestTeardownAndDefaults:
    def test_teardown_missing_is_success(self, tmp_root):
        assert teardown_codex_home(str(tmp_root / "ppr-codex-home-gone")) is True

    def test_teardown_refuses_foreign(self, tmp_root):
        d = tmp_root / "random-dir"
        d.mkdir()
        assert teardown_codex_home(str(d)) is False
        assert d.exists()

    def test_default_manifest_derivation(self):
        assert default_manifest("/tmp/ppr-abc123-session.json") == "/tmp/ppr-abc123-codex-homes.list"
        assert default_manifest("/t/qr-Q1-r2-session.json") == "/t/qr-Q1-r2-codex-homes.list"
