# Contest-Refactor Run Report — `credential_policy.py`

Target: `/private/tmp/claude-502/-Users-Shared-git-agent-skills/051852b6-ffb7-44f6-9d95-881320b484b5/scratchpad/d2`
Method followed: `contest-refactor/references/method.md` (Meta-Rules + 10-step Method + Simplify Pressure Test), `architecture-rubric.md`, `lens-generic.md`, and `lens-security.md` (always-included per method.md Step 0 — read in addition to the three assigned files because the module's entire purpose is credential storage).

## Step 0 / discovery

Two first-party files: `credential_policy.py` (implementation) and `test_credential_policy.py` (its own bundled test suite, both pytest-collectible and directly runnable). No `CONTEXT.md` / `docs/adr/` present — proceeded silently per architecture-rubric.md. Doc-vs-code marker grep (`LEGACY|TEMPORARY|DEPRECATED|DO NOT|ASPIRATIONAL|carve-out|SHIM|FIXME|HACK|TODO`) — **zero hits**, no doc-rot to chase. No loops, I/O, closures, or recomputation in the module, so `lens-efficiency.md` (D1–D4) has nothing to check — noted, not fabricated.

Baseline: `python3 -m pytest -q` → **3 passed**.

## Critic phase — findings

### Finding 1 — Severity: Likely disqualifier

**Claim.** `set_credential` does not hash the credential. It "encodes" it by reversing the character order, which is a bijective, zero-cost-to-invert transform, not a one-way function. For a module whose entire stated purpose is "credential storage and verification," this means the stored form carries no real protection: anyone who can read the stored value (DB dump, backup, log line, replication stream) recovers the original credential by reversing the string back — no cracking, no brute force, no computation.

**Source.** `credential_policy.py:47` (pre-fix):
```python
return "$enc$" + raw[::-1]
```
and the docstring's own claim at `credential_policy.py:43-46` ("Encode `raw` into a storable credential value... Never starts with NO_LOCAL_CREDENTIAL_PREFIX") never claims one-wayness — the function name (`set_credential`, called from a "verify" pair) is where the false promise of security lives, not the prose.

**Consequence.** This is the primary — really the only — user flow this module exists for. A broken one-way property here is exactly the "core architectural property broken at runtime, reachable from a primary flow" anchor for Likely disqualifier (architecture-rubric.md § Severity Anchors). It defeats the purpose of separating "stored credential" from "raw credential" in the first place: functionally equivalent to storing plaintext behind a fixed-cost decoder ring.

**Remedy.** Replace the reversible transform with a salted, one-way KDF and verify by re-deriving, not by re-encoding-and-comparing-strings.

### Finding 2 — Severity: Serious deduction

**Claim.** `verify_credential`'s comparison (`set_credential(supplied) == stored`) used Python's `==` on strings, which short-circuits at the first differing byte — a timing side channel on credential comparison.

**Source.** `credential_policy.py:59` (pre-fix): `return set_credential(supplied) == stored`.

**Consequence.** Secondary to Finding 1 (moot while the primary hash is reversible — an attacker with read access doesn't need a timing oracle when the plaintext is a string-reverse away) but becomes a live weakness the moment Finding 1 is fixed with a real hash, since a real hash makes exact-match timing the only remaining attack surface. Fixing Finding 1 without fixing this would leave a new, real vulnerability in the replacement code.

**Remedy.** Compare with `hmac.compare_digest`, not `==`.

*(These two are reported and SPT-scored separately as instructed, but share one remedy site — the comparison line — so they're applied together.)*

No other findings met the Evidence Chain bar. Ownership is single-writer per concern, there's no seam/adapter to critique (correctly — a 4-function pure module needs none), no hidden state machine, no silent-swallow of errors in the original code, and the bundled test file exercises the module's stated public Interface directly (no test-vs-code mismatch).

## Architect phase — Simplify Pressure Test

### Finding 1 fix — proposed: salted PBKDF2-HMAC-SHA256 (stdlib `hashlib`), verify by re-deriving and comparing digests

1. **Does it fix real ambiguity?** Yes — replaces a reversible transform with an actual one-way function; the vulnerability is real and current-source-backed, not speculative.
2. **Is it the smallest honest fix?** Yes. `hashlib.pbkdf2_hmac` is stdlib — no new dependency, no build config, ~15 lines. Considered and rejected the "obvious" answer (below).
3. **Does it avoid duplicate layers?** Yes — same two functions, same call sites, same 4-function public Interface. No wrapper class, no strategy/algorithm abstraction added.
4. **Does runtime behavior remain honest?** Yes — the new stored format encodes algorithm id + iteration count + salt + digest in plain sight (`$pbkdf2-sha256$<iters>$<salt>$<digest>`); nothing is hidden or suppressed. This is a genuine fix, not a suppressed warning.
5. **Does the product improve — measurably, and by more than the item declined?** Yes, and by a wide margin: moves the module from "any read access recovers plaintext credentials for free" to "recovery requires brute-forcing a 600,000-iteration salted hash per guess." This is the only structural issue in the file; nothing competing was declined in its favor.

**Structural gate:** no new Module/Seam is introduced (Unified Seam Policy N/A), no Module is deleted (deletion test N/A), and the existing tests still sit at the same Interface (`set_credential` / `verify_credential` signatures unchanged) — satisfies "tests after the refactor live at the new Interface" trivially since the Interface didn't move.

**Verdict: PASSED.**

**Rejected alternative — bcrypt or argon2 (a third-party password-hashing library).** This is the textbook "correct" answer for password hashing, and I considered it seriously before defaulting to stdlib. Rejected under Q2: this file and its test have zero third-party dependencies today (no `requirements.txt`/`pyproject.toml` even present in the probe directory), and stdlib `hashlib.pbkdf2_hmac` at a modern OWASP-recommended iteration count (600,000 for PBKDF2-HMAC-SHA256, 2023 guidance) closes the actual vulnerability without adding a dependency, a lockfile entry, or a build-time C-extension risk for what stdlib already does adequately. Per the ladder (stdlib before new dependency): rung 3 solves it, so rung 5 (new dependency) doesn't get reached. If this module later needs memory-hardness against GPU/ASIC cracking specifically, `hashlib.scrypt` (also stdlib) is the next honest upgrade — not recorded as a separate finding since there's no source evidence today that PBKDF2 is inadequate for this codebase's actual threat model.

### Finding 2 fix — proposed: `hmac.compare_digest` instead of `==`

1. **Does it fix real ambiguity?** Yes — closes a real (if secondary) timing side channel.
2. **Is it the smallest honest fix?** Yes — one-line swap, stdlib (`hmac`, already needed for nothing else, single import).
3. **Does it avoid duplicate layers?** Yes.
4. **Does runtime behavior remain honest?** Yes — same true/false outcomes for every input, only the timing characteristic of the false case changes (uniform instead of leaking match-prefix length).
5. **Does the product improve — measurably, and by more than the item declined?** Yes — without it, fixing Finding 1 would silently trade a "read the DB" vulnerability for a "time the verify endpoint" vulnerability. Nothing of comparable value was declined.

**Structural gate:** same as above — no Seam/Module change; N/A cleanly.

**Verdict: PASSED.**

No other candidate fixes were considered for this file — there was no third finding to generate one from. If SPT hadn't rejected anything and no finding beyond these two had been raised, this section would say so — and mostly it does: exactly one alternative was proposed and rejected (bcrypt/argon2), nothing else.

## Execution phase — edits applied

**`credential_policy.py`:**
- Added `import hashlib`, `import hmac`.
- Added constants `_HASH_ALGORITHM = "sha256"`, `_ITERATIONS = 600_000`, `_SALT_BYTES = 16`, `_ENCODED_PREFIX = "$pbkdf2-sha256$"`.
- Added private helper `_pbkdf2(raw, salt_hex, iterations) -> str` wrapping `hashlib.pbkdf2_hmac(...).hex()`.
- Rewrote `set_credential` to generate a random salt (`secrets.token_hex`), hash with `_pbkdf2`, and return `f"{_ENCODED_PREFIX}{_ITERATIONS}${salt}${digest}"` instead of `"$enc$" + raw[::-1]`.
- Rewrote `verify_credential` to parse the stored format, recompute the digest from `supplied` with the stored salt/iteration count, and compare with `hmac.compare_digest` instead of `set_credential(supplied) == stored`. Malformed/foreign-format `stored` values (e.g. anything not matching the new encoding — including the old `$enc$...` format) are caught via `except ValueError` and treated as "can't verify, not a match" (commented inline), never as a crash.
- Docstrings on `set_credential` / `verify_credential` updated to describe the actual (one-way, constant-time) behavior instead of the old reversible one.

**`test_credential_policy.py`:**
- Added `test_no_local_credential_marker_never_verifies`, asserting `verify_credential(mark_no_local_credential(), "anything") is False`. Rationale (Step 8 mutation-test check): without this test, the `is_credential_usable` guard clause at the top of `verify_credential` was exercised only incidentally — no test called `verify_credential` with a no-local-credential marker as `stored`. This is the primary flow's own safety guard (a mutation deleting or inverting that guard on the marker path was previously uncaught); now it has a direct assertion.

**Manual edge-case checks (not part of the committed test file, run ad hoc to confirm the fix, all passed):**
- A legacy `$enc$...`-formatted stored value does not verify and does not raise.
- `stored=None`, `stored=""`, and `stored="garbage"` all return `False` without raising.
- The new encoded output does not contain the raw credential or its reverse as a substring.
- `mark_no_local_credential()` output still reports `is_credential_usable() is False` (sentinel/encoded spaces stay disjoint under the new prefix).

**Caveat worth recording (not blocking, no data exists to migrate in this probe):** the on-disk encoding format changed (`$enc$...` → `$pbkdf2-sha256$...`). In a real deployment with already-stored `$enc$`-format credentials, existing users would fail to verify until re-enrolled/reset — this fix needs a migration or dual-read path there. This probe has no persistent store and no pre-existing data, so it doesn't apply here, but it's the honest caveat for anyone lifting this fix into a live system.

## Final test result

```
$ python3 -m pytest -q
....                                                                     [100%]
4 passed in 0.61s

$ python3 test_credential_policy.py
OK: test_credential_policy.py
```

All tests pass, including the newly added one. Nothing broke, nothing needed reverting.

## Final scorecard

| Dimension | Score | Basis |
|---|---|---|
| Security / credibility | Was broken (reversible "encoding" masquerading as a credential store) → now correct: salted PBKDF2-HMAC-SHA256, constant-time compare, disjoint sentinel/encoded value spaces preserved. |
| Ownership | 9.5 — single writer per concern (`set_credential`/`mark_no_local_credential` are the only producers of stored values; `verify_credential` the only consumer), no ambiguity, unchanged by this fix. |
| Architecture (Module/Seam/Depth) | 9.5 — one cohesive Module, no seam needed and none was added (Unified Seam Policy correctly not invoked), Interface stayed the same size as before (4 functions), no costume layers, no repository theater. |
| Simplicity | 9 — fix is a same-shape, same-Interface, stdlib-only swap; the one tempting overbuild (bcrypt/argon2 dependency) was identified and rejected via SPT rather than added. |
| Test strategy | 9 — bundled suite is pytest-collectible and runs standalone; added the one test that closes the previously-uncaught guard-clause mutation on the primary flow. Not claiming 9.5+: iteration-count/format-string boundary values (e.g. corrupted salt hex, non-numeric iteration field) are exercised only by the ad hoc manual checks above, not committed as tests. |

## Summary

Findings raised: 2 (Likely disqualifier — reversible "encoding" instead of a real hash; Serious deduction — non-constant-time comparison).
Fixes applied: 2 (both, via one edit to the same comparison/encoding site) — salted PBKDF2-HMAC-SHA256 replacing the reversible transform, plus `hmac.compare_digest` replacing `==`; one test added to close a previously-uncaught guard-clause mutation.
Fixes SPT-rejected: 1 — adding a third-party bcrypt/argon2 dependency, rejected under Q2 (stdlib already solves it; no dependency currently exists in this codebase).
Pytest: 4 passed (was 3 passed at baseline; the 4th is the new test) — full pass, nothing reverted.
