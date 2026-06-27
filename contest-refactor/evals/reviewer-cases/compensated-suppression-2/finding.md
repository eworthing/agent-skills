<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — ArticleLoader duplicates endpoint URL fragments across three methods with no single site of knowledge (Priority 1)

- **Claim:** `ArticleLoader` constructs full URL strings inline in each method body, repeating the base URL (`https://cms.example.com/api/v2`) and query-parameter defaults independently at three call sites.
- **Source:** `Sources/ArticleLoader.swift:9` (`fetchLatest`), `:15` (`fetchArticle`), and `:21` (`search`) each contain an independent `URL(string:)` literal with duplicated host and path prefix; no shared constant or builder for the path structure.
- **Consequence:** any hostname, API version bump, or per-request default change requires hunting and updating three independent string literals independently — Locality failure, regression risk on partial updates.
- **Severity:** Noticeable weakness.
- **Remedy (minimal_correction_path):** extract endpoint URL construction to a single constants namespace so every method reads from one site of knowledge.
