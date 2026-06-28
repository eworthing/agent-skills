#!/usr/bin/env bash
# Regression guard: Pricing and its caller must typecheck TOGETHER. Renaming
# Pricing.computeTotal without updating the caller (which is outside the finding's
# blast radius) breaks compilation -> deterministic, model-independent build break.
set -euo pipefail
swiftc -typecheck Sources/Pricing.swift Sources/PricingClient.swift >/dev/null 2>&1 || {
  echo "FAIL: Sources do not typecheck together (a caller depends on the renamed symbol)"; exit 1; }
echo OK
