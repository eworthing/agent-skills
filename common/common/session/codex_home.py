"""codex_home.py — Per-run CODEX_HOME isolation for concurrent Codex reviews.

The Codex adapter recovers a session id by diffing ``$CODEX_HOME/sessions/``
before/after ``codex exec`` and filtering by cwd. When two reviews run against
the same repo at once (two peer-plan-review agents side by side, or quorum's
parallel panel fan-out), each run sees the other's new session file and the
cwd filter can't tell them apart — capture is skipped and resume breaks.

Giving every run its own ``CODEX_HOME`` makes the diff unambiguous, mirroring
the per-run isolation already used for Gemini (``GEMINI_CONFIG_DIR``) and agy
(per-run ``--log-file``). Auth/config are copied in from the real home; the
isolated ``sessions/`` is what concurrency needs separated.

Lifecycle, keyed off the caller-supplied ``session.json`` + a review-scoped
manifest:

- ``setup_codex_home`` mints a randomized 0700 dir, **records it in the manifest
  before any credential is written and before Codex launches** (so a
  timeout/signal/crash can't hide a credential-bearing dir from cleanup), then
  copies the allowlisted files. Any failure rolls the dir back and fails closed.
- ``reuse_codex_home`` validates a home recorded in a prior round so resume (and
  repeat non-resume verifier calls sharing a session file) reuse it.
- ``cleanup_review_homes`` is the single safe terminal reclaim: union of the
  manifest and the review's session files, validated and torn down, manifest
  kept (with survivors) on partial failure for retry. It also age-gate-sweeps
  the global fallback manifest (``default_manifest(None)``'s target) for
  orphans no per-review cleanup would otherwise ever reach.

Stdlib-only; POSIX + Windows (ownership checks are platform-gated).
"""

import contextlib
import glob
import json
import os
import shutil
import signal
import stat
import sys
import tempfile
import time
from pathlib import Path

# Marker prefix on every per-run home. Validation refuses to touch a path that
# lacks it, so cleanup/teardown can never be tricked into removing an arbitrary
# directory recorded (or injected) into a manifest or session file.
_HOME_PREFIX = "ppr-codex-home-"

# Minimal set `codex exec` needs to authenticate and run. Copying only these
# avoids snapshotting mutable runtime state (history, logs, indexes) that a
# blanket top-level copy would capture mid-write.
_ALLOWLIST = ("auth.json", "config.toml")

# Name of the fallback manifest `default_manifest(None)` writes to when a
# caller has no review-scoped manifest to pass. Entries recorded there carry
# no review id, so `cleanup_review_homes` treats it as a shared orphan pool
# rather than something scoped to one review (see `_reclaim_stale_global_homes`).
_GLOBAL_MANIFEST_NAME = "ppr-codex-homes.list"

# Age guard for reclaiming entries from the global fallback manifest: a home
# must be idle at least this long before any review's cleanup call may
# reclaim it, so a concurrent live run's home (freshly created/touched) is
# never pulled out from under it.
_STALE_HOME_AGE_SECONDS = 24 * 60 * 60

_POSIX = os.name == "posix"
_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)


def _real_codex_home(real_home=None):
    if real_home:
        return Path(real_home)
    return Path(os.environ.get("CODEX_HOME", str(Path("~/.codex").expanduser())))


def _temp_root():
    return os.path.realpath(tempfile.gettempdir())


def _owned_real_dir(path):
    """True iff ``path`` is an existing real directory (not a symlink/reparse
    point) owned by us, located under the temp root with the home prefix.

    The gauntlet every reuse/teardown candidate must pass so a planted symlink
    or a foreign/injected path is never followed or removed.
    """
    p = Path(path)
    try:
        if p.is_symlink():
            return False
        st = p.lstat()
        if not stat.S_ISDIR(st.st_mode):
            return False
        rp = os.path.realpath(p)
        root = _temp_root()
        if rp != root and not rp.startswith(root + os.sep):
            return False
        if not Path(rp).name.startswith(_HOME_PREFIX):
            return False
        if _POSIX:
            if st.st_uid != os.getuid():
                return False
        elif getattr(st, "st_file_attributes", 0) & _REPARSE:
            return False
        return True
    except OSError:
        return False


def _block_signals():
    """Block SIGTERM/SIGINT across the brief create→record window so an
    interruption can't leave a credential-bearing home off the manifest.
    Returns the prior mask to restore, or None where unsupported (Windows)."""
    if not _POSIX or not hasattr(signal, "pthread_sigmask"):
        return None
    with contextlib.suppress(ValueError, OSError):
        return signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
    return None


def _restore_signals(previous):
    if previous is None:
        return
    with contextlib.suppress(ValueError, OSError):
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def default_manifest(session_file):
    """Fallback manifest path derived from a session file when the caller does
    not pass one. Callers should prefer an explicit review-scoped manifest so
    every subprocess in a review shares one list (crash-safe reclamation)."""
    if not session_file:
        return str(Path(tempfile.gettempdir()) / "ppr-codex-homes.list")
    p = Path(session_file)
    name = p.name
    suffix = "-session.json"
    if name.endswith(suffix):
        name = name[: -len(suffix)]
    return str(p.with_name(name + "-codex-homes.list"))


def record_codex_home(manifest, home):
    """Securely append ``home`` as one line to ``manifest``. Raises on failure
    so the caller rolls the home back.

    Uses O_NOFOLLOW + an fstat ownership/type check so a symlink or foreign file
    planted at the predictable manifest path in a shared temp dir can't be
    followed or corrupted.
    """
    flags = os.O_CREAT | os.O_WRONLY | os.O_APPEND
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(manifest, flags, 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise OSError(f"manifest is not a regular file: {manifest}")
        if _POSIX and st.st_uid != os.getuid():
            raise OSError(f"manifest not owned by current user: {manifest}")
        if not _POSIX and getattr(st, "st_file_attributes", 0) & _REPARSE:
            raise OSError(f"manifest is a reparse point: {manifest}")
        # Single write of one newline-terminated line — atomic for the concurrent
        # sibling appends quorum's thread pool produces.
        os.write(fd, (str(home) + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def setup_codex_home(manifest, real_home=None):
    """Create an isolated CODEX_HOME and return ``(home, True)``, or
    ``(None, False)`` on any failure (rolling back a partial home).

    Transaction order so an interruption/failure can never leave an untracked
    credential-bearing home: mask signals → mkdtemp → record in manifest →
    unmask → copy allowlisted credentials/config.
    """
    blocked = _block_signals()
    home = None
    try:
        home = tempfile.mkdtemp(prefix=_HOME_PREFIX)
        Path(home).chmod(0o700)
        record_codex_home(manifest, home)
    except OSError as e:
        if home:
            shutil.rmtree(home, ignore_errors=True)
        print(f"Warning: Codex home setup failed (record): {e}", file=sys.stderr)
        return (None, False)
    finally:
        _restore_signals(blocked)

    # Home is now manifest-recorded; a failure past here is still discoverable,
    # but roll back anyway to avoid leaking a half-populated credential dir.
    try:
        (Path(home) / "sessions").mkdir(mode=0o700, exist_ok=True)
        src = _real_codex_home(real_home)
        for name in _ALLOWLIST:
            s, d = src / name, Path(home) / name
            if s.is_file() and not d.exists():
                shutil.copy2(s, d)
                if name == "auth.json":
                    with contextlib.suppress(OSError):
                        d.chmod(0o600)
        return (home, True)
    except OSError as e:
        shutil.rmtree(home, ignore_errors=True)
        print(f"Warning: Codex home setup failed (populate): {e}", file=sys.stderr)
        return (None, False)


def reuse_codex_home(path):
    """True iff a home recorded in a prior round may be reused this round."""
    return bool(path) and _owned_real_dir(path) and (Path(path) / "sessions").is_dir()


def teardown_codex_home(path):
    """Remove a per-run home. Returns True if it is gone (removed or already
    absent — idempotent), False if it could not be validated or removed."""
    if not path:
        return True
    p = Path(path)
    if not p.exists() and not p.is_symlink():
        return True  # already cleaned — success
    if not _owned_real_dir(p):
        print(f"Warning: refusing to remove unrecognized Codex home: {path}", file=sys.stderr)
        return False
    try:
        shutil.rmtree(p)
        return True
    except OSError as e:
        print(f"Warning: could not remove Codex home {path}: {e}", file=sys.stderr)
        return False


def _read_manifest(manifest):
    """Read manifest lines, refusing a symlinked/foreign file (O_NOFOLLOW +
    ownership check). Returns [] if absent or rejected."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(manifest, flags)
    except OSError:
        return []
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return []
        if _POSIX and st.st_uid != os.getuid():
            return []
        chunks = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
    except OSError:
        return []
    finally:
        os.close(fd)
    text = b"".join(chunks).decode("utf-8", "replace")
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _is_stale(path, now=None):
    """True iff ``path``'s mtime is older than ``_STALE_HOME_AGE_SECONDS``.
    False (never stale) on any stat failure, so an unreadable/vanished path
    is left for the normal validity checks rather than assumed reclaimable."""
    now = time.time() if now is None else now
    try:
        return (now - Path(path).stat().st_mtime) > _STALE_HOME_AGE_SECONDS
    except OSError:
        return False


def _rewrite_manifest(manifest, entries):
    tmp = Path(str(manifest) + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(e + "\n")
        tmp.replace(manifest)
    except OSError as e:
        print(f"Warning: could not rewrite manifest {manifest}: {e}", file=sys.stderr)
        with contextlib.suppress(OSError):
            tmp.unlink()


def _reclaim_stale_global_homes(global_manifest, already_seen):
    """Sweep the global fallback manifest (entries with no review id) for
    homes idle longer than ``_STALE_HOME_AGE_SECONDS``, tearing those down.
    Entries already accounted for by the caller's own review (``already_seen``)
    are dropped from this manifest without being touched again. Younger or
    otherwise-untouched entries are left in place for a later sweep.

    Returns the list of stale homes that failed teardown (kept in the
    rewritten manifest so a later cleanup call can retry them).
    """
    keep, stale = [], []
    for h in _read_manifest(global_manifest):
        h = h.strip()
        if not h or h in already_seen:
            continue
        if _owned_real_dir(h) and _is_stale(h):
            stale.append(h)
        else:
            keep.append(h)

    stale_failed = [h for h in stale if not teardown_codex_home(h)]
    survivors = keep + stale_failed
    if survivors:
        _rewrite_manifest(global_manifest, survivors)
    else:
        with contextlib.suppress(OSError):
            global_manifest.unlink()
    return stale_failed


def cleanup_review_homes(tmpdir, id_prefix):
    """Reclaim every per-run Codex home for a review. Returns the count that
    could NOT be removed (0 = fully clean; idempotent on re-run).

    Sources the **union** of (a) the authoritative manifest and (b) homes
    recorded in this review's session files, enumerated with a **literal**
    id (``glob.escape``) and delimiter-bounded patterns so ``qr-demo`` never
    matches ``qr-demo2-*``. Removes the manifest only if every teardown
    succeeded; on partial failure rewrites it with the survivors for retry.

    Also sweeps the global fallback manifest (``ppr-codex-homes.list``, what
    ``default_manifest(None)`` points callers at when they have no
    review-scoped manifest of their own) for orphaned homes — those entries
    carry no review id, so any review's cleanup call may reclaim them, gated
    by an mtime age guard so a concurrent live run's home is never pulled out
    from under it. Homes that fail that sweep are folded into the returned
    count alongside this review's own failures.
    """
    base = Path(tmpdir)
    manifest = base / f"{id_prefix}-codex-homes.list"

    homes, seen = [], set()

    def _add(h):
        h = (h or "").strip()
        if h and h not in seen:
            seen.add(h)
            homes.append(h)

    for h in _read_manifest(manifest):
        _add(h)

    esc = glob.escape(id_prefix)
    for pattern in (
        f"{esc}-session.json",
        f"{esc}-r*-session.json",
        f"{esc}-verify-*-session.json",
    ):
        for sf in base.glob(pattern):
            with contextlib.suppress(OSError, ValueError):
                _add(json.loads(sf.read_text(encoding="utf-8")).get("codex_home"))

    failed = [h for h in homes if not teardown_codex_home(h)]
    if failed:
        _rewrite_manifest(manifest, failed)
    else:
        with contextlib.suppress(OSError):
            manifest.unlink()

    global_manifest = base / _GLOBAL_MANIFEST_NAME
    if global_manifest != manifest:
        failed.extend(_reclaim_stale_global_homes(global_manifest, seen))

    return len(failed)
