# GPT 6 Luna: frozen Phase 2 replication (#80)

Canonical tracking issue: https://github.com/HiQS-Labs/Needle-fork/issues/80; predecessor #13.

Exactly two sequential fresh gpt-6-luna / Medium calls, unchanged September 9 explicit prompt and 12-case packet. Original source: XYZ-forge 5ecf2cd667a534320725b2a65fd2e23c40e9d8e3, TESTS-RESULTS/2026-09-09+Needle-13-git-analyst. Original adapter changes only the model ID. Codex CLI 0.159.1 with ephemeral, ignore-user-config, read-only and approval=never. Original 900/870 second caps; no temperature or output cap claimed. Reuse shipped consult transport, one call at a time. Stop after a failed transport or unauthorized tool action; no quality retry/substitution.

48 points/run: 12 exact verdict, 12 relevant citations, 24 semantics (two frozen requirements per case). Original grade thresholds and critical-failure caps apply. The key, old responses and old scores remain outside candidate checkout until both calls finish. Independent semantic review is reconciled with coordinator scores; no new criteria after inference. G05 official verdict UNKNOWN retained, with separate sensitivity excluding its one verdict point. Quality improvement requires positive mean-score delta without critical failures; report each dimension and both runs rather than treating a letter as proof. Baseline is historical (44/43), not fresh randomized A/B. Same 12 cases repeated twice, not 24 independent examples.

Validate original hashes and grader positive/six negative controls, commit inputs before inference, retain raw events and request timing. Report tool observability, selection-vs-backend identity, CLI/system context differences, fixture exposure and scoring subjectivity. No private corpus, product/runtime changes or production readiness claims. Billed cost unavailable; no price estimate without current verified rates.

Reversibility Easy: append corrections to evidence; no deployed state. Evidence lives here; project/roadmap/graph records link to the issue and summary.

Candidate isolation: consult runs against a separate two-file Git repository containing only QUESTIONS.md and packet.json. No key, prior results, or protocol is present in that checkout. This removes historical ambient project instructions and is a disclosed harness-context difference; the explicit candidate prompt remains byte-identical. The source adapter is unchanged except for gpt-5.6-luna → gpt-6-luna.
