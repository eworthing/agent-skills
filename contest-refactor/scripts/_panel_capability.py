"""panel_certification capability manifest lookup + partial-panel resume
router (plans/rec1-panel-certification.md § Version transition, enablement,
and delivery sequence).

Two independent decisions, both default-deny / fail-closed:

- emit_check(): may main CREATE a v5 panel for this provider+model, under
  the currently executable protocol?
- resume_route(): given a persisted PARTIAL v5 panel checkpoint, what does
  main do with it -- independent of whether new panels are authorized
  (authorization to create is separate from handling one that already
  exists; see the plan section above).

Both read canon/panel-certification.toml (load_manifest) and call
_panel_gate_adapter.compute_protocol_digest() -- the ONE shared digest
function that also backs the gate evidence file, so runtime lookup and gate
evidence cannot drift independently.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

import _panel_gate_adapter

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent


def load_manifest(root: Path | None = None) -> dict:
    """Parse canon/panel-certification.toml. Raises on a missing/malformed
    file -- that is a repository-integrity fault, not a routing decision."""
    path = (root or _DEFAULT_ROOT) / "canon" / "panel-certification.toml"
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return {
        "schema_version": data.get("schema_version"),
        "entries": data.get("entries", []),
        "unsupported_digests": data.get("unsupported_digests", []),
    }


def emit_check(
    provider: str,
    model: str,
    root: Path | None = None,
    manifest: dict | None = None,
) -> dict:
    """v5 vs v4 emit decision for one provider+model. Decision order, first
    match wins: unknown provider -> unmeasurable; no exact (provider, model)
    entry -> unmeasured (also covers model overrides); entry's recorded
    digest on the rollback list -> disabled; entry's digest stale against
    the live protocol -> stale; else exact match -> v5."""
    if manifest is None:
        manifest = load_manifest(root)
    digest = _panel_gate_adapter.compute_protocol_digest(root)

    if provider == "unknown":
        return {"emit": "v4", "reason": "unknown_provider", "protocol_digest": digest}

    entry = next(
        (
            e
            for e in manifest["entries"]
            if e.get("provider") == provider and e.get("model") == model
        ),
        None,
    )
    if entry is None:
        return {"emit": "v4", "reason": "no_entry", "protocol_digest": digest}

    entry_digest = entry.get("protocol_digest")
    if entry_digest in manifest["unsupported_digests"]:
        return {"emit": "v4", "reason": "unsupported_digest", "protocol_digest": digest}
    if entry_digest != digest:
        return {"emit": "v4", "reason": "stale_digest", "protocol_digest": digest}
    return {"emit": "v5", "reason": "match", "protocol_digest": digest}


def _blocked(reason: str) -> dict:
    return {"route": "fail_closed_verification_blocked", "reason": reason}


def resume_route(
    checkpoint: dict,
    current_source_rev: str,
    current_candidate_fingerprint: str,
    root: Path | None = None,
    manifest: dict | None = None,
) -> dict:
    """Route for a persisted partial v5 panel checkpoint (LOOP_STATE.json's
    panel phase, created at panel spawn). Routes, decided top-down, first
    match wins -- see module docstring cross-reference for the full
    rationale of each row."""
    if manifest is None:
        manifest = load_manifest(root)

    panel_state = checkpoint.get("panel_state") if isinstance(checkpoint, dict) else None
    if not isinstance(panel_state, dict):
        return _blocked("malformed checkpoint: missing panel_state")

    stored_digest = panel_state.get("protocol_digest")
    if not stored_digest:
        return _blocked("malformed checkpoint: missing panel_state.protocol_digest")

    if stored_digest in manifest["unsupported_digests"]:
        return _blocked("stored protocol_digest is on the unsupported_digests rollback list")

    try:
        current_digest = _panel_gate_adapter.compute_protocol_digest(root)
    except OSError as exc:
        return _blocked(f"current protocol digest could not be computed: {exc}")

    if stored_digest != current_digest:
        return _blocked(
            f"stored protocol_digest is stale (stored={stored_digest!r}, current={current_digest!r})"
        )

    binding = panel_state.get("candidate_binding")
    if not isinstance(binding, dict):
        return _blocked("malformed checkpoint: missing panel_state.candidate_binding")

    if current_source_rev != binding.get(
        "source_rev"
    ) or current_candidate_fingerprint != binding.get("candidate_fingerprint"):
        return {
            "route": "drift_fresh_critic",
            "reason": "current source_rev/candidate_fingerprint no longer matches candidate_binding",
        }

    if panel_state.get("sub_phase") == "normalization":
        return {
            "route": "complete_normalization",
            "reason": "sub_phase=normalization; finish the normalization transaction, launch nothing",
        }

    members = panel_state.get("members")
    if not isinstance(members, list):
        return _blocked("malformed checkpoint: missing panel_state.members")

    if not members:
        # Checkpoint is created at member-1 launch, so an interrupt before
        # member 1 delivers leaves zero durable records -- a legitimate
        # state, not a fault. The unresolved staged work IS member 1.
        return {
            "route": "resume_stage1",
            "reason": "no member records; member 1 unresolved; relaunch member 1",
        }

    if any(isinstance(m, dict) and m.get("outcome") == "broke" for m in members):
        return {
            "route": "route_decisive_break",
            "reason": "a member record outcome=='broke'; decisive, not unresolved partial work",
        }

    member1 = members[0] if members else None
    member1_outcome = member1.get("outcome") if isinstance(member1, dict) else None

    if member1_outcome == "unavailable":
        return {
            "route": "route_verification_blocked",
            "reason": "member 1 unavailable; staged rule never resumes into stage 2",
        }

    if len(members) == 3:
        if any(isinstance(m, dict) and m.get("outcome") == "unavailable" for m in members):
            return {
                "route": "route_verification_blocked",
                "reason": "a stage-2 member record outcome=='unavailable'",
            }
        if all(isinstance(m, dict) and m.get("outcome") == "held" for m in members):
            return {
                "route": "complete_panel",
                "reason": "all 3 members held; apply precedence routing / promotion, launch nothing",
            }
        return _blocked(
            "malformed checkpoint: 3 member records with an unrecognized outcome combination"
        )

    if member1_outcome == "held" and len(members) < 3:
        return {
            "route": "resume_stage2",
            "reason": "member 1 held; reuse durable records verbatim, launch only missing stage-2 members",
        }

    return _blocked("malformed checkpoint: unrecognized panel_state.members shape")


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        manifest = load_manifest(args.root)
        result = emit_check(args.provider, args.model, root=args.root, manifest=manifest)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    print(json.dumps(result))
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    try:
        checkpoint = json.loads(Path(args.checkpoint).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: cannot read checkpoint {args.checkpoint}: {exc}\n")
        return 2
    try:
        manifest = load_manifest(args.root)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    result = resume_route(
        checkpoint,
        args.source_rev,
        args.candidate_fingerprint,
        root=args.root,
        manifest=manifest,
    )
    print(json.dumps(result))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="panel_certification capability lookup + partial-panel resume router"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="v5/v4 emit decision for a provider+model")
    p_check.add_argument("--provider", required=True)
    p_check.add_argument("--model", required=True)
    p_check.add_argument("--root")
    p_check.set_defaults(func=_cmd_check)

    p_resume = sub.add_parser("resume", help="resume route for a persisted partial v5 panel")
    p_resume.add_argument(
        "--checkpoint", required=True, help="path to the LOOP_STATE.json checkpoint"
    )
    p_resume.add_argument("--source-rev", required=True)
    p_resume.add_argument("--candidate-fingerprint", required=True)
    p_resume.add_argument("--root")
    p_resume.set_defaults(func=_cmd_resume)

    args = parser.parse_args()
    args.root = Path(args.root) if args.root else None
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
