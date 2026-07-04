#!/usr/bin/env python3
"""Compatibility shim — implementation lives in the quorum/ package.

Re-exports the public surface that test_run_quorum.py and downstream
callers depend on. See tests/shim-contract.txt for the full list (AST-
verified by common/scripts/check_shim_contract.py).

Importing this module is identical to importing the union of:
    quorum.cli, quorum.orchestrator, quorum.ledger, quorum.parsing,
    quorum.merge, quorum.verification, quorum.prompts

Test suites that ``patch.object(run_quorum, "run_single_reviewer", ...)``
work because ``quorum.orchestrator.main`` resolves ``run_single_reviewer``
via this shim at call time (see the late ``import run_quorum`` inside
``main``).
"""

# Re-exports — every name in tests/shim-contract.txt must appear here.

from quorum.cli import (
    MAX_ROUNDS_LIMIT,
    MIN_QUORUM_SIZE,
    VERIFIER_CANDIDATE_SPECS,
    parse_args,
    parse_reviewer_spec,
    resolve_verifier,
    validate_panel,
)
from quorum.ledger import (
    _make_issue,
    _sync_issue_aliases,
    load_ledger,
    save_ledger,
)
from quorum.merge import (
    apply_merge_pipeline,
    classify_merge_candidate,
    generate_merge_candidates,
)
from quorum.orchestrator import (
    EXIT_APPROVED,
    EXIT_INDETERMINATE,
    EXIT_REVISE,
    _is_unanimous,
    _resolve_run_review,
    build_issue_ledger,
    compile_compressed_context,
    compile_deliberation,
    derive_verdict,
    format_issue_consensus,
    main,
    run_single_reviewer,
    should_exit_early,
    tally_verdicts,
)
from quorum.parsing import (
    _extract_section,
    parse_cross_critique,
    parse_structured_review,
    parse_verdict,
)
from quorum.prompts import (
    CROSS_CRITIQUE_INSTRUCTIONS,
    REVIEW_CONTRACT_V2,
    _role_for_mode,
    format_ledger_summary,
    load_review_md,
    write_cross_critique_prompt,
    write_deliberation_prompt,
    write_initial_prompt,
)
from quorum.verification import (
    _sync_verification_state,
    generate_verification_prompts,
    parse_verification_response,
)

if __name__ == "__main__":
    main()
