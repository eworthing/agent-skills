#!/usr/bin/env python3
"""Hidden oracle battery for swiftnio-registration-id-representation.
Grader-only: never shown to a candidate (listed in provenance.json's
grader_only_files).

Same probe pattern as this corpus's other Swift packs: `oracle_probe.swift`
(grader-only) is copied to a scratch file literally named `main.swift`
(swiftc only allows top-level statements in a file with that exact name)
and compiled against each variant's own `command_word.swift` PLUS that
variant's own grader-only `probe_adapter.swift`, never against that
variant's own `main.swift`. The adapter exists because encoding is NOT
uniform across variants on purpose -- the raw-shaped variants build a word
from three bare integers, the typed variants build one from a
RoutingAssignment -- and reconciling that into one call shape belongs in a
grader-only file, not in the candidate-visible module (an earlier draft of
this pack put a raw-integer encode wrapper directly in the typed variants'
own module for this reason, and that wrapper was itself a hole in the
pack's central claim: see provenance.json's expected_judgment). The
resulting probe binary takes three integers (ticket, lane, tier), packs
them via that variant's own probe_adapter.swift, and reads them back out
via that variant's own candidate-visible ticketNumber/laneNumber/tierLevel
-- see oracle_probe.swift's header.

Two of this pack's four checks need no compiled probe at all:
`distinct_field_types_not_interchangeable` compiles a tiny grader-only
snippet against a variant's own command_word.swift (no adapter involved)
with `swiftc -typecheck` and reads the exit code, and
`packing_confined_to_one_site` is pure static text analysis over each
variant's own command_word.swift.

Runs four checks:

    distinct_field_types_not_interchangeable -- Swift type errors are
                                 compile-time, so this is observed by
                                 attempting to compile a tiny snippet that
                                 swaps two field arguments in a
                                 construction call. inline-shift-mask-
                                 per-site and near-miss-generic-bit-
                                 packing-helper expose only a raw-UInt64
                                 makeCommandWord(ticket:lane:tier:); the
                                 swap snippet passes the lane value where
                                 ticket is expected and vice versa, and
                                 since both parameters are UInt64 this
                                 compiles without complaint -- the type
                                 system catches nothing. typed-fields-
                                 single-conversion and mutant-narrow-lane-
                                 mask define TicketID and BeltLane as
                                 distinct named types with no raw-integer
                                 encode path in their candidate-visible
                                 module at all, so the swap snippet builds
                                 a RoutingAssignment directly and fails to
                                 compile -- there is no back door here to
                                 reason around.
    packing_confined_to_one_site -- counts, per variant, how many places
                                 in command_word.swift know a bit
                                 shift/width for this word's layout: (a)
                                 top-level struct/enum/class/func
                                 declarations whose body contains a `<<`
                                 or `>>` operator, plus (b) call sites
                                 elsewhere that pass a literal shift/width
                                 to a generic packer (matched as
                                 `shift: <digits>`, which only appears at
                                 a call site -- the generic packer's own
                                 parameter declaration reads `shift: Int`,
                                 not a digit). inline-shift-mask-per-site
                                 has no generic packer at all: its four
                                 functions each shift/mask by hand, four
                                 sites. near-miss-generic-bit-packing-
                                 helper's PackingKit is exactly one
                                 declaration with shift operators, but
                                 every one of its four callers passes a
                                 literal shift and width, adding six more
                                 sites (three in makeCommandWord's three
                                 packField calls, one each in the three
                                 single-field getters) -- one helper,
                                 many call sites, which is the honest
                                 distinction this corpus's build brief
                                 asked this oracle to measure. typed-
                                 fields-single-conversion and mutant-
                                 narrow-lane-mask each have exactly one
                                 declaration with shift operators
                                 (ConveyorCommandWord) and zero literal-
                                 shift call sites anywhere else, because
                                 every other function talks about
                                 TicketID/BeltLane/HandlingTier, never
                                 about bit ranges.
    roundtrip_preserved_at_field_maxima -- THE DISCRIMINATOR between the
                                 accepted variant and the mutant, which
                                 are structurally identical everywhere
                                 else: pack then unpack a matrix of
                                 values including each field's maximum
                                 and maximum-minus-one. True for every
                                 variant except mutant-narrow-lane-mask,
                                 whose belt-lane unpack mask is one bit
                                 too narrow (0x7FFF instead of 0xFFFF),
                                 silently dropping the lane field's top
                                 bit whenever it is set -- which both a
                                 lane value's maximum (65535) and
                                 maximum-minus-one (65534) have.
    ordinary_value_midrange_roundtrips -- CONTROL: an ordinary, well-
                                 within-range value (ticket 12345, lane
                                 42, tier 3) round-trips in every variant,
                                 including the mutant, whose lane-mask bug
                                 only shows up when the lane value's top
                                 bit is set. Holds everywhere in this
                                 pack's correct design -- a baseline that
                                 would fail if this fixture itself were
                                 broken in a way that made the other three
                                 oracles' results meaningless.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
MODULE_FILENAME = "command_word.swift"
ADAPTER_FILENAME = "probe_adapter.swift"

VARIANTS = [
    "inline-shift-mask-per-site",
    "typed-fields-single-conversion",
    "near-miss-generic-bit-packing-helper",
    "mutant-narrow-lane-mask",
]

# The two variants whose external construction API is raw UInt64
# everywhere (no domain types at all) versus the two whose internal
# construction API is domain-typed. distinct_field_types_not_interchangeable
# needs a different swap snippet for each shape -- see that function.
RAW_API_VARIANTS = {"inline-shift-mask-per-site", "near-miss-generic-bit-packing-helper"}
DOMAIN_API_VARIANTS = {"typed-fields-single-conversion", "mutant-narrow-lane-mask"}

TICKET_MAX = (1 << 40) - 1
LANE_MAX = (1 << 16) - 1
TIER_MAX = (1 << 8) - 1

MAXIMA_MATRIX = [
    (TICKET_MAX, 100, 5),
    (TICKET_MAX - 1, 100, 5),
    (100, LANE_MAX, 5),
    (100, LANE_MAX - 1, 5),
    (100, 200, TIER_MAX),
    (100, 200, TIER_MAX - 1),
]

RAW_SWAP_SNIPPET = """\
// Grader-only compile-fail probe (raw-integer shape). Swaps the ticket
// and lane arguments in a call to makeCommandWord. Both parameters are
// plain UInt64, so nothing in the type system can catch a caller who
// mixes them up -- this snippet is EXPECTED TO COMPILE.
let ticketValue: UInt64 = 7
let laneValue: UInt64 = 9
_ = makeCommandWord(ticket: laneValue, lane: ticketValue, tier: 1)
"""

DOMAIN_SWAP_SNIPPET = """\
// Grader-only compile-fail probe (domain-typed shape). Swaps the ticket
// and lane arguments in a call to RoutingAssignment's own initializer.
// Ticket and lane are distinct named types, so passing one where the
// other is expected must NOT type-check -- this snippet is EXPECTED TO
// FAIL TO COMPILE.
let ticketValue = TicketID(rawValue: 7)!
let laneValue = BeltLane(rawValue: 9)
_ = RoutingAssignment(ticket: laneValue, lane: ticketValue, tier: HandlingTier(rawValue: 1))
"""

_TOP_LEVEL_DECL_RE = re.compile(r"^(struct|enum|class|func)\s+(\w+)")
_SHIFT_OP_RE = re.compile(r"<<|>>")
_LITERAL_SHIFT_CALL_RE = re.compile(r"\bshift:\s*\d")


def _swiftc(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)


def _swiftc_or_raise(*args: str) -> None:
    result = _swiftc(*args)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s command_word.swift and its own grader-only
    probe_adapter.swift against the grader-only probe (copied to scratch
    as main.swift). The adapter supplies probeMakeWord, the uniform
    encode entry point this probe calls -- see oracle_probe.swift's
    header for why encoding isn't uniform across variants on its own."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc_or_raise(
        str(PACK_DIR / variant / MODULE_FILENAME),
        str(PACK_DIR / variant / ADAPTER_FILENAME),
        str(main_path),
        "-o",
        str(binary_path),
    )
    return binary_path


def run_probe(binary: Path, ticket: int, lane: int, tier: int) -> tuple[int, int, int, int]:
    result = subprocess.run(
        [str(binary), str(ticket), str(lane), str(tier)],
        capture_output=True,
        text=True,
        check=True,
    )
    fields = dict(part.split(":", 1) for part in result.stdout.strip().split())
    return (
        int(fields["word"]),
        int(fields["ticket"]),
        int(fields["lane"]),
        int(fields["tier"]),
    )


def _top_level_blocks(source: str) -> list[tuple[str, str, str]]:
    """Split `source` into (keyword, name, body_text) for each top-level
    struct/enum/class/func declaration, by brace-depth tracking.

    Assumes consistent formatting: every top-level declaration in this
    pack's own command_word.swift files starts at column 0 and its
    closing brace is also at column 0. True by construction for every
    module file in this pack; not a general Swift parser."""
    lines = source.splitlines()
    blocks: list[tuple[str, str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = _TOP_LEVEL_DECL_RE.match(line)
        if not match:
            i += 1
            continue
        keyword, name = match.group(1), match.group(2)
        depth = line.count("{") - line.count("}")
        body_lines = [line]
        i += 1
        while depth > 0 and i < len(lines):
            body_lines.append(lines[i])
            depth += lines[i].count("{") - lines[i].count("}")
            i += 1
        blocks.append((keyword, name, "\n".join(body_lines)))
    return blocks


def distinct_field_types_not_interchangeable(dirs: dict[str, Path]) -> dict[str, bool]:
    results = {}
    with tempfile.TemporaryDirectory(prefix="swiftnio-repr-swap-") as tmp:
        scratch_dir = Path(tmp)
        for variant, variant_dir in dirs.items():
            module_path = variant_dir / MODULE_FILENAME
            snippet = RAW_SWAP_SNIPPET if variant in RAW_API_VARIANTS else DOMAIN_SWAP_SNIPPET
            main_path = scratch_dir / f"{variant}_main.swift"
            main_path.write_text(snippet, encoding="utf-8")
            # Each variant's swap probe must be compiled alone against
            # that variant's own module -- swiftc only allows top-level
            # statements in a file named main.swift, so copy per variant.
            scratch_main = scratch_dir / "main.swift"
            shutil.copyfile(main_path, scratch_main)
            compiled = _swiftc("-typecheck", str(module_path), str(scratch_main)).returncode == 0
            results[variant] = not compiled
    return results


def packing_confined_to_one_site(dirs: dict[str, Path]) -> dict[str, int]:
    results = {}
    for variant, variant_dir in dirs.items():
        source = (variant_dir / MODULE_FILENAME).read_text(encoding="utf-8")
        blocks = _top_level_blocks(source)
        sites = sum(1 for _keyword, _name, body in blocks if _SHIFT_OP_RE.search(body))
        sites += len(_LITERAL_SHIFT_CALL_RE.findall(source))
        results[variant] = sites
    return results


def roundtrip_preserved_at_field_maxima(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        ok = True
        for ticket, lane, tier in MAXIMA_MATRIX:
            _word, rt_ticket, rt_lane, rt_tier = run_probe(binary, ticket, lane, tier)
            ok = ok and (rt_ticket, rt_lane, rt_tier) == (ticket, lane, tier)
        results[variant] = ok
    return results


def ordinary_value_midrange_roundtrips(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        _word, rt_ticket, rt_lane, rt_tier = run_probe(binary, 12345, 42, 3)
        results[variant] = (rt_ticket, rt_lane, rt_tier) == (12345, 42, 3)
    return results


def main() -> int:
    dirs = {variant: PACK_DIR / variant for variant in VARIANTS}

    with tempfile.TemporaryDirectory(prefix="swiftnio-repr-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        distinct_results = distinct_field_types_not_interchangeable(dirs)
        site_counts = packing_confined_to_one_site(dirs)
        maxima_results = roundtrip_preserved_at_field_maxima(binaries)
        control_results = ordinary_value_midrange_roundtrips(binaries)

    print("=== distinct_field_types_not_interchangeable ===")
    for name, ok in distinct_results.items():
        print(
            f"  {name}: {'distinct (swap rejected)' if ok else 'INTERCHANGEABLE (swap compiled)'}"
        )
    print("=== packing_confined_to_one_site ===")
    for name, count in site_counts.items():
        print(f"  {name}: {count} site(s){' (confined)' if count == 1 else ' (SCATTERED)'}")
    print("=== roundtrip_preserved_at_field_maxima ===")
    for name, ok in maxima_results.items():
        print(f"  {name}: {'preserved' if ok else 'LOST AT MAXIMUM'}")
    print("=== ordinary_value_midrange_roundtrips (control) ===")
    for name, ok in control_results.items():
        print(f"  {name}: {'preserved' if ok else 'LOST'}")

    failures: list[str] = []

    expected_distinct = {
        "inline-shift-mask-per-site": False,
        "near-miss-generic-bit-packing-helper": False,
        "typed-fields-single-conversion": True,
        "mutant-narrow-lane-mask": True,
    }
    for name, expected in expected_distinct.items():
        if distinct_results.get(name) != expected:
            failures.append(
                f"{name}: expected distinct_field_types_not_interchangeable={expected}, "
                f"got {distinct_results.get(name)}"
            )

    expected_confined = {
        "inline-shift-mask-per-site": False,
        "near-miss-generic-bit-packing-helper": False,
        "typed-fields-single-conversion": True,
        "mutant-narrow-lane-mask": True,
    }
    for name, expected_confined_flag in expected_confined.items():
        confined = site_counts.get(name) == 1
        if confined != expected_confined_flag:
            failures.append(
                f"{name}: expected packing_confined_to_one_site (count==1)={expected_confined_flag}, "
                f"got count={site_counts.get(name)}"
            )

    expected_maxima = {
        "inline-shift-mask-per-site": True,
        "typed-fields-single-conversion": True,
        "near-miss-generic-bit-packing-helper": True,
        "mutant-narrow-lane-mask": False,
    }
    for name, expected in expected_maxima.items():
        if maxima_results.get(name) != expected:
            failures.append(
                f"{name}: expected roundtrip_preserved_at_field_maxima={expected}, "
                f"got {maxima_results.get(name)}"
            )

    for name in VARIANTS:
        if control_results.get(name) is not True:
            failures.append(
                f"{name}: ordinary_value_midrange_roundtrips must hold, got {control_results.get(name)}"
            )

    if failures:
        print("\nFAIL:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nOK: observed matrix matches declared expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
