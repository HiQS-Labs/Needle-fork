# Is a small shortlist prototype worthwhile? — 2026-09-12

## TLDR

Do not build an interaction prototype yet. My recommendation is one final,
one-hour offline shortlist check as a stop/go diagnostic—not another model
campaign. The advisors disagree about whether even that is worth doing; neither
endorses a demo now, and useful recommendations remain unproven.

Authority: [#62](https://github.com/HiQS-Labs/Needle-fork/issues/62), under #1.
[Proposed scope](../PROJECT/1-INBOX/SHORTLIST-FEASIBILITY.md); not executed.

## Disagree — and adjudication

**Run a cheap check, or stop now?** Codex CLI Sol High recommends the check first,
because existing counters can test a narrower shortlist hypothesis cheaply. Agy
recommends parking everything as a proxy-metric treadmill. I favor the bounded
check only because a negative result can end this count-based lane without more
model spend. A pass would establish at most relative coarse-label coverage on
reused development data, not that a user benefits. No automatic demo or training.

**How much evidence would it add?** Agy describes the proposed input as “40 reused
development cases.” The proposal actually uses 1,722 rows across 40 reused issues;
the previous model quiz sampled 40 cases. The committed
[manifest](../TESTS-RESULTS/2026-09-12-context-refresh/manifest.json) resolves the
count. Also, three of six labels is half the label vocabulary, not a guaranteed
50% observed hit rate: class frequencies and conditioning matter. Thus a same-case
lift over strong controls is a legitimate narrow measurement, though Agy is right
that it does not measure useful advice. The scope already separates these claims.

**Does no calibration time mean no potential product use?** Agy says the abandoned
manual trial rules out interaction. That inference is too strong: unwillingness to
fill ratings does not prove unwillingness to use helpful suggestions. Sol more
narrowly notes that a demo currently lacks a credible usefulness endpoint. Adopt
that restraint, not a blanket conclusion that this operator cannot use the product.

**Resources and stopping rules.** Sol suggests 90 minutes and more issue wins than
losses; Agy's fallback, despite recommending no work, is a four-hour shadow daemon
with a 60% hit@3 cutoff on 50 live actions. Retain the original one-hour offline
cap and adopt Sol's wins-over-losses restraint before scoring. Reject the daemon:
it expands collection/privacy/integration scope, cannot establish usefulness, and
its proposed absolute cutoff has no same-case baseline. Do not turn either model's
advice into new runtime authorization. “Park” means no automatic tuning; reopening
would need materially new evidence and an explicit decision, not a permanent claim
that every future next-action approach must fail.

## Agree

Both advise against an interactive demo now. Both recognize that recorded-label
agreement is not intent, actionable guidance or human acceptance, that operator
burden matters, and that another training/model-panel campaign is unjustified.
Both regard CPU-only, read-only, bounded-input constraints as sensible. Sol notes
that replay could illustrate ordering/repetition/stability; Agy notes that passive
logging could measure latency/domain shift. Neither measurement proves usefulness,
and neither requires us to build another integration today.

## Sorted follow-through

- **Blocking:** operator decision before execution; nonempty trusted inputs,
  unchanged old scores and held #43, same-case strong controls and a fixed stopping
  rule before any new score. No interaction prototype until its learning question
  and low-burden observation method are explicitly scoped. An offline pass does
  not clear that blocker.
- **Worth doing, optional:** the single capped check; issue wins-over-losses added
  to its proposed rule. Reuse existing guards and add only new-seam tests. Sol
  warned against exhaustive diagnostic infrastructure; if verification cannot fit
  the cap, stop rather than quietly weaken the checks or extend the work.
- **Skip / out of scope:** building a replay UI or shadow daemon now, the arbitrary
  60% live cutoff, new collection, manual CSV assignments, more advisors, model
  tuning, training, changing old failed gates, or closing #62 merely on advice.

## Provenance and limits

One-shot `consult` harness, two independent advisors, 2 answered / 0 failed,
about 130 seconds. Same prompt and tracked/untracked proposal in a disposable
repository worktree; ignored data excluded. No benchmark or prototype execution.
Codex CLI 0.153.4 header attests `gpt-5.6-sol`, reasoning `high`, provider OpenAI,
read-only sandbox. Agy was invoked through the existing wrapper pinned to
`gemini-3.1-pro-high`, effort `high`; its plain-text answer carries no independent
backend model attestation. Agy is repo-isolated, not a host-process sandbox.

Raw prompt/transcripts remain in ignored `data/shortlist-consult/`, run
`prototype-value-183736`; they include machine-local paths. The harness attached
a no-firsthand-citation warning to Sol. Its actual answer includes source-line
citations, and the transcript records source reads, which I inspected; retain the
warning rather than treating either advisor's prose as runtime verification.
Dollar cost is not available for this CLI consult. Advice is conditional and can
share blind spots; the reconciliation above, not a claimed consensus, owns the call.
