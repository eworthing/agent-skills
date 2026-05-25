# Adoption-Signal Tracking Gap — meta-level concern

Source: landscape research § 5 "Star / Adoption Analysis" + § 8 "Watchlist". No code competitor to inspect — this is a META concern about HOW contest-refactor's landscape analysis treats adoption signals (stars, freshness, installs, marketplace listings) vs quality.

Different in kind from the other 13 gap docs. Not about contest-refactor's mechanics; about contest-refactor's POSITIONING discipline and ongoing competitive monitoring.

## The signal-vs-noise problem

Landscape research observed:

> **Notable inversions:** `hamelsmu/claude-review-loop` and `levnikolaevich/claude-code-skills` are the most underrated quality-vs-adoption ratios in the field. `VoltAgent` (19k stars) suffers from prose-heavy role-prompts; the GitHub issue thread on its own `code-reviewer.md` flags it fails to question suspicious configuration changes.

And as caveat:

> Several aggregator pages (skills.sh, ClaudePluginHub) report inflated or out-of-date star counts (e.g., 203,293 for superpowers vs the GitHub-direct 203k); cross-check github.com directly before quoting numbers in any public-facing artifact.

Contest-refactor's competitive analysis must NOT conflate these signals:

| Signal | What it measures | What it does NOT measure |
|---|---|---|
| GitHub stars | Awareness + click intent | Actual usage, retention, install success rate |
| Last-commit date | Recent maintainer activity | Whether the skill works at all |
| Marketplace listings | Listing presence | Listing quality, install volume |
| Aggregator-reported counts | Self-reported by aggregator | Often stale or inflated |
| Citation in blog posts | Author preference | Operational success |
| Fork count | Modification interest | Production usage |
| `npx <skill> add` count | Install attempts | Successful uses |

Per landscape research, public skill ecosystems are dominated by **awareness inversions**: high-star repos with prose-heavy "senior X with expertise spanning Y" prompts that fail basic adversarial review (VoltAgent issue thread cited as example); low-star repos with empirically rigorous mechanics (hamelsmu/claude-review-loop has 619 stars; levnik audit-suite has ~mid-tier stars but ships 35+ specialty workers + full orchestrator-worker contract).

## Strategic insight

If contest-refactor compares itself to competitors by stars alone, it loses honest evaluation. Three concrete failure modes:

1. **Underrate winning patterns**: dismiss hamelsmu/claude-review-loop (619★) as "small" when it actually IS the closest live Actor-Critic competitor with verified Stop-hook architecture, 2-run cap, fail-open discipline.
2. **Overrate adversarial losers**: cite VoltAgent (19k★) as competitive benchmark when its own issue thread documents it failing to question suspicious config changes. Stars ≠ quality.
3. **Anchor to aggregator inflation**: skills.sh reports 203,293 for superpowers; GitHub-direct says 203k. The 293 over-precision is wrong; the order-of-magnitude is right.

## Proposed positioning discipline (for contest-refactor's own docs)

### Rule 1: never quote stars without source + date

In any contest-refactor doc citing competitor adoption:

> github.com/<owner>/<repo> — N★ (as of <YYYY-MM-DD>)

NOT:

> ~N stars (per skills.sh)
> ~Nk stars (vague)

Source verification before quoting. Aggregator counts only as fallback with explicit "[aggregator-reported, unverified]" tag.

### Rule 2: separate quality rank from adoption rank

Already implicit in landscape research's § 5 table:

| Name | Stars | Quality Rank | Adoption Rank |
|---|---|---|---|
| levnik | mid | high | low |
| VoltAgent | 19k | mid | high |

Contest-refactor's competitive evaluations should preserve this two-axis split. When a gap doc cites a competitor's strength, cite QUALITY rank (source-inspected mechanics) not ADOPTION rank.

### Rule 3: document watchlist separately from competitors

Landscape research § 8 lists a watchlist (Jules, DeepSource AI Autofix, Cursor BugBot Autofix loop, CodeLoops, anthropics/skills future plugins, Antigravity Awesome Skills, agentskills.io spec evolution, HAMY's 9-parallel pattern, shadowX4fox cacheable prompt pattern).

These are NOT competitors yet — they're TRENDS to track. Confusing watchlist items with competitors leads to:

- Citing closed-source products as if they were inspectable
- Treating commercial vendor claims (Cursor BugBot 52→76% resolution rate, DeepSource 84.51% F1) as ground truth
- Inflating the competitive landscape's size

### Rule 4: explicit "vendor-self-published" tagging

Landscape research caveats:

> The Greptile 82%/CodeRabbit 44% benchmark and the 11/2 false-positive counts are from Greptile's own July 2025 benchmark page across 50 PRs from Sentry/Cal.com/Grafana/Keycloak — vendor-self-published, not third-party.
> The DeepSource 84.51% F1 figure is from DeepSource's own published benchmark on 165 real CVEs from the OpenSSF dataset (JavaScript/TypeScript, pre- and post-patch commits); Cursor Bugbot is runner-up at 80.45% F1. Also vendor-self-published.
> The Cursor Bugbot "35% Autofix merged into base PR" and the "52% → 76% resolution rate over six months" figures are from Cursor's own Feb 26, 2026 blog post by Jon Kaplan ("Closing the code review loop with Bugbot Autofix"). The 35% covers Autofix-proposed commits that are merged into the base PR, which includes developer-reviewed merges — not strictly "merged without human edits." Treat all three numbers as directional.

Adopt rule: **any quoted benchmark must declare source authorship**. Vendor-self-published, third-party-academic, or peer-reviewed — never elide.

## Operational tooling (minimal)

### Per-quarter watchlist refresh

Schedule (manual or via /loop): every 90 days, re-fetch:

1. Top 10 competitor README + lastest-commit timestamps
2. New entrants matching keywords (claude code skill, agent skill, actor-critic, refactor loop, etc.)
3. Vendor blog posts on tools matching contest-refactor's space

Update `analysis/contest-refactor/INVENTORY.md` with newly cloned competitors + flagging obsolete ones (analysis docs live under `analysis/contest-refactor/` per repo convention; clones live under `refs/competitors/` gitignored).

### Adoption-signal audit on each landscape claim

When writing a new gap doc citing competitor adoption, run:

```bash
gh api repos/<owner>/<repo> --jq '{stars: .stargazers_count, pushed_at: .pushed_at, license: .license.spdx_id}'
```

Record stars/pushed_at/license inline. Stale data (commit > 6 months OR license absent) flags watch.

### Quarterly aggregator sanity check

Skills.sh / ClaudePluginHub / antigravity-awesome-skills sometimes report inflated stars or stale data. Quarterly: pick 5 competitor entries, cross-check aggregator vs GitHub. If drift > 5%, document the drift in INVENTORY.md.

## Gap matrix

| Mechanism | contest-refactor today | This gap's recommendation |
|---|:--:|:--:|
| Inline source + date on competitor stars | partial (mixed practice in existing gap docs) | always required |
| Quality rank vs adoption rank separation | implicit | explicit two-column |
| Watchlist separated from competitors | — | dedicated INVENTORY.md section |
| Vendor-self-published tagging | partial (in landscape doc; not in gap docs) | required in all citations |
| Aggregator-vs-GitHub drift check | — | quarterly |
| New-entrant scan cadence | — | every 90 days |

## P2 GAPS — what to import

### Gap A (P2): Inventory update with adoption metadata

Add columns to INVENTORY.md table:

```
| Repo | Stars | Last commit | License | Stars source | Quality rank |
|---|---:|---|---|---|---|
| levnik-skills | mid (verify) | 2026-05-XX | MIT | github-direct | high |
| VoltAgent | 19k | 2026-03-XX | MIT | github-direct (aggregator-confirmed) | mid |
```

`Quality rank` is contest-refactor's own judgment after source inspection. `Stars source` is `github-direct | aggregator-reported | vendor-blog | unverified`.

### Gap B (P2): Vendor-self-published flag in gap docs

Every gap doc citing a benchmark / win-rate / adoption claim from a vendor blog MUST tag:

```markdown
> Per Cursor blog (Jon Kaplan, Feb 26, 2026): "Over 35% of Bugbot Autofix changes are merged into the base PR" — VENDOR-SELF-PUBLISHED, directional only.
```

Existing gap docs (`SCHEMA-GAP`, `GATES-GAP`, etc.) should be audited for unflagged vendor claims.

### Gap C (P2): Watchlist section in INVENTORY.md

Separate "Active competitors (source inspected)" from "Watchlist (trending; not yet inspected)":

```markdown
## Watchlist (not yet inspected)

| Name | Type | Why on watchlist | Inspect priority |
|---|---|---|---|
| Jules | Commercial (Google) | LLM-as-judge productization | low (closed-source) |
| DeepSource AI Autofix | Commercial | 84.51% F1 vendor-claim on OpenSSF benchmark | medium (vendor-self-published; treat directional) |
| Cursor BugBot Autofix loop | Commercial | 35% Autofix merge rate; resolution 52→76% over 6 months | medium |
| anthropics/skills future plugins | Official | Track for `refactor` or `architecture-review` plugin shipping | high (official source) |
| shadowX4fox cacheable prompt | Pattern | Stable-prefix → dynamic-suffix prompt for parallel sub-agents | low (one-off pattern) |
| Antigravity Awesome Skills | Aggregator | 1234-1465+ skills | low (aggregator) |
| HAMY 9-parallel pattern | Blog-only | Pattern, no repo | low |
| agentskills.io spec evolution | Spec | Track frontmatter additions (disable-model-invocation, context: fork) | high (affects skill packaging) |
| arXiv:2511.04824 follow-ups | Academic | Track for peer-review status + follow-up empirical work | medium |
```

### Gap D (P2): Quarterly competitor refresh task

Add `scripts/competitor-refresh.sh` that:

1. For each repo in `refs/competitors/`, run `git pull --depth 1`
2. For each, run `gh api repos/<owner>/<repo>` and update INVENTORY.md star + last-commit
3. Diff INVENTORY.md vs git-stored; surface drift
4. Run `find refs/competitors -name SKILL.md -newer .last-refresh` to find new skills added since last refresh
5. Update `.last-refresh` marker file

Manual cadence (90 days); not automated CI because new-skill detection benefits from human judgment.

## What NOT to do

| Tempting | Why skip |
|---|---|
| Auto-poll GitHub for star changes every loop | No value to contest-refactor users; only noise. Star changes don't affect running loops. |
| Rank competitors by stars in landscape analysis | Landscape research already cautions against this. Adoption ≠ quality. |
| Cite vendor-self-published benchmarks as ground truth | Always tag as vendor-self-published, directional. |
| Consume aggregator-reported metrics without GitHub cross-check | Per landscape caveat. |
| Pretend closed-source products are inspectable competitors | Jules / DeepSource / Cursor BugBot stay on WATCHLIST, not competitor inventory. Mark as "behavioral-claim-only; source not available." |
| Treat absent-LICENSE repos as "free to copy patterns from" | hamelsmu/claude-review-loop has NO LICENSE. Patterns are documented but reproduction has unclear copyright posture. Note in any adoption recommendation. |

## Pairing with other gap docs

- **INVENTORY.md updates**: every other gap doc references INVENTORY; this gap proposes the schema additions
- **CROSS-MODEL-CRITIC-GAP**: cites hamelsmu/claude-review-loop's NO-LICENSE situation; this gap formalizes the disclosure pattern
- **All gap docs**: should be audited to flag any unflagged vendor claims per Gap B

## Adoption order

1. **Phase 1 (housekeeping)**: Audit existing 14 gap docs for unflagged vendor claims; add `— VENDOR-SELF-PUBLISHED` tags where needed
2. **Phase 2**: Add Quality rank + License + Stars source columns to INVENTORY.md
3. **Phase 3**: Split INVENTORY.md into "Inspected competitors" + "Watchlist" sections
4. **Phase 4 (optional)**: Ship `scripts/competitor-refresh.sh` for quarterly manual cadence
5. **Phase 5 (defer)**: Automate the refresh as opt-in CI; default off

## Why this is P2 (lowest priority)

This gap doesn't change contest-refactor's mechanics, schema, or runtime behavior. It's a discipline rule for contest-refactor's competitive analysis docs and ongoing landscape research. Affects DOCS quality, not skill quality.

But it's worth writing because: without it, future research updates to RESEARCH-DELTA / new gap docs / landscape refreshes drift into mixing quality with adoption signals. The discipline must be documented somewhere; this doc is that somewhere.
