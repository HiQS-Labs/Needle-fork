# Phase 2 follow-up — GH-81

Issue: https://github.com/HiQS-Labs/Needle-fork/issues/81. Predecessors #80 and #13.

Two fresh sequential calls each: GPT 6 Luna High using the #80 adapter with only medium → high; Claude Sonnet 5.5 Medium via Claude Code 2.1.284. Medium is the published Claude Code default; effort names are not equal compute across vendors. No fallback, retries, answer repair, temperature override or prompt tuning. Original 900/870-second caps. Stop a lane after transport failure or unexpected tool execution. Use the existing consult transport; its slot name codex is transport only.

Explicit prompt, QUESTIONS, packet, expected key and grader are byte-identical to #80 and the September 9 baseline. Candidate cwd is a disposable two-file git checkout, containing only QUESTIONS.md and packet.json; no answer key, prior output or scores. Claude tools/MCP/skills/hooks disabled, no session persistence; Codex same ephemeral/read-only/ignore-user-config as #80. Native system context and vendor harness differ, so this is a workflow comparison, not controlled model-only causation. No backend identity attestation beyond returned metadata.

48 points: exact verdict + relevant citation + two semantic requirements for each of 12 cases. Original rubric, grade thresholds and critical-failure caps from #80/baseline/PROTOCOL.md apply. Independently review semantic marks and reconcile against historical calibration. G05 UNKNOWN remains official; report sensitivity omitting its verdict point. Report all run scores and dimensions. Improvement means positive mean delta without critical failure; two repeats are not a general capability claim. Historical baselines not rerun. Capture nonempty outputs, controls, input hashes, raw events, timing, usage and CLI pricing telemetry (not a bill).

Full-roster pricing research uses official public current standard API token rates, cache rates, active promotional terms separately, and unknowns where exact route pricing is unestablished. Date the table. API estimates are not subscription invoices. No runtime/product changes. Reversibility Easy: append corrections, no deployed state.
