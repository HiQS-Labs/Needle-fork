---
title: Test runner mapping correction
status: Shipped
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Correct the two confirmed runner classification defects without revising frozen evidence.
reversibility: Easy — scoped mapper and regression changes
---

# Test runner mapping — #56 completed

Authority: operator-authorized [#56](https://github.com/HiQS-Labs/Needle-fork/issues/56).
Existing shared Bash taxonomy now distinguishes unittest execution from unambiguous
runner metadata probes. No taxonomy renaming, native-editor policy changes,
dataset regeneration, model training or serving changes.

[Receipt](../../TESTS-RESULTS/2026-09-12-test-runner-mapping/SUMMARY.md) owns the
scope, limitations, red/green evidence and bounded command differential. The
debug-mantra skill kept the fix grounded in witnessed failing examples and exposed
an initial environment-prefix guard regression before landing.

Next is a separately scoped/versioned data refresh and bounded follow-up decision;
not another model panel. Prior scores/gates and PR #43's hold remain unchanged.
