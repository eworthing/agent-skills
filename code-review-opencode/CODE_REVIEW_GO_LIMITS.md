# code-review-opencode — OpenCode Go limits and the concurrency choice

Research date: 2026-11-12.

## What OpenCode Go actually limits

OpenCode Go does **not publish a concurrency limit**. The official docs define
only dollar-based usage limits per model:

- **5-hour window:** 20% of the model's monthly allowance.
- **Weekly window:** 50%.
- **Monthly window:** 100%.

For **DeepSeek V4.1 Flash** on Go the monthly allowance is **$100**, so the
windows are **$20 per 5 hours** and **$50 per week**. Off-peak prices are
$0.15/M input, $0.003/M cached read, and $0.60/M output; peak prices double.
Peak is 01:00–04:00 and 06:00–10:00 UTC, Monday–Friday.

The docs' request estimates (43,330 per 5 hours for V4.1 Flash) assume a typical
agent request of ~410 input, ~71,300 cached, and ~310 output tokens. A
code-review finder carries the full diff (~250k input tokens), so the dollar
cost per request is much higher and the request estimate does not apply.

## What the research found about concurrency

- OpenCode Go's docs mention no per-account, per-model, or per-session
  concurrency cap.
- OpenCode does not expose per-model concurrency configuration; issue
  [#12019](https://github.com/anomalyco/opencode/issues/12019) was closed as not
  planned. Our `--concurrency` gate is the only control.
- Third-party reviews state plainly that **OpenCode Go publishes nothing on
  concurrency limits** (Ian Reppel, *The Last Vendor*). Providers that do
  publish limits, such as Synthetic (one per model per pack) and Ollama Pro
  (three), are different services.
- Some Go models have their own provider-side limits. MiniMax returns
  "Traffic is currently high ... for higher concurrency or automated workloads,
  consider upgrading" under load. GLM plans have reported one-concurrent
  limits. These are model-specific, not Go-wide.
- The provider queues excess requests rather than dropping them, so raising
  concurrency past the serving capacity increases latency and queue depth, not
  throughput.

## Empirical result for this workload

- **8 concurrent max-effort children:** all children went silent together after
  ~20 minutes; the provider was saturated and the stall watchdog interrupted
  them. Runs 5 and 6 were partial.
- **6 concurrent children (run 10):** six finders started; one stalled after
  600 s and was interrupted, the other five completed. The run was partial.
  The stall may have been contaminated by an earlier double-run, but it did not
  produce a clean complete run.
- **4 concurrent children:** multiple runs completed cleanly (run 8b was the
  first complete run; run 9 also had no dropped finders or verifiers).
- A full self-review costs roughly **$1** at off-peak V4.1 Flash prices, so the
  $20/5-hour allowance covers roughly 20 runs. The quota is not the binding
  constraint for a single review; provider queueing is.

## Recommendation

- **Default 4** for large-context reviews (full-repo or `max`). It is the
  highest value with a complete run on this workload.
- **6** is available for smaller diffs or off-peak. The 6-way trial completed
  five of six finders; retry it only on a clean provider.
- **8** is the reference fan-out and only safe when the provider is healthy and
  the diff is small. It caused the saturation described above on this repo.
- Keep the stall watchdog and the `--concurrency` override. Do not add a
  concurrency auto-tuner until a clean 6-way run is stable.

## Sources

- [OpenCode Go docs](https://opencode.ai/docs/console/go/) — plans, per-model
  dollar limits, 20%/50%/100% windows, DeepSeek V4.1 Flash pricing and monthly
  limit.
- [OpenCode inference API](https://opencode.ai/docs/console/api/inference) —
  `opencode.allowance` and cost reporting.
- [OpenCode issue #12019](https://github.com/anomalyco/opencode/issues/12019) —
  per-model concurrency configuration was closed as not planned.
- [Ian Reppel, *The Last Vendor*](https://ianreppel.org/the-last-vendor/) —
  "OpenCode Go publishes nothing on concurrency limits"; Synthetic and Ollama
  limits for comparison.
- [OpenCode issue #22811](https://github.com/anomalyco/opencode/issues/22811) —
  MiniMax provider concurrency/queue error on Go.
- [Jatin Malik, OpenCode Go routing guide](https://medium.com/@jatinkrmalik/opencode-go-oh-my-openagent-the-complete-guide-to-sota-model-routing-without-hitting-limits-49fdc8cb3417) —
  conservative concurrency advice for $15 models (predates the current V4.1
  Flash allowance).
