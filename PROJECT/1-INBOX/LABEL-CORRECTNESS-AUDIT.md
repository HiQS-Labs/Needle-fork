# Label correctness audit — the gate §2 never had

**Status:** INTAKE — not started, awaiting operator decision
**Raised:** 2026-09-09 · **Refs:** [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §2 §5,
[#9](https://github.com/HiQS-Labs/Needle-fork/issues/9), [#17](https://github.com/HiQS-Labs/Needle-fork/issues/17)
**Rail:** `LESSONS-LEARNED.md` §15, §16

## The gap, in one sentence

Every number this project has measured about the label sorter counts **resolution** — did a command
get *a* label. **Nothing has ever measured whether the label is right.**

## Why it was missed, and where it belonged

[#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §2 defines dataset validity with a single
gate:

> "Report mapping coverage as a number: what fraction of extracted steps resolved to a real intent
> label vs. fell through to a generic bucket. **A low coverage number invalidates the dataset**, so
> it is a gate, not a statistic."

Coverage cannot distinguish a right label from a wrong one — a command mislabelled `promote_capture`
counts as *covered*. §2 is therefore blind to the failure that consumed seven review rounds.

**It was noticed and mis-filed.** `PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md:70-71`, written in
Phase A, says: *"the published top-3 baselines… and any per-label accuracy computed on those labels
measure the regex list, not the model."* That is the problem stated correctly — and it was treated
as a reason the **baselines** were wrong, not as a quantity to **measure**.

**This belonged in §2**, as a second gate beside coverage. §5's evaluation is *model-vs-label* and
treats labels as ground truth, so it structurally cannot surface this; by §5 a bad label set makes
every model number unattributable.

## Measured state (2026-09-09, `main` @ `69f362c`)

| | |
|---|---|
| Mapping coverage | 96.41% (**resolution only**) |
| Corpus | 335 sessions, 71,763 calls |
| Ordered bash rules | 31, first match wins |
| **Commands matching >1 rule** | **78.12%** |
| Hand-maintained table entries | 141 across 14 tables |
| Label correctness | **never measured** |
| Review rounds | 7, each finding a **disjoint** defect set |

For four commands in five the label is decided by *rule list position*, and that ordering has never
been validated — only patched when someone noticed a specific wrong answer.

## The proposal

**Hand-label a stratified random sample of ~400 commands and score the sorter against it.**

- **~400** gives roughly ±5% at 95% confidence on the overall precision estimate.
- **Stratify by label**, not uniformly. Uniform sampling gives the governance labels 2–3 rows;
  they are the labels the Oracle exists for and the thinnest in the corpus
  (`promote_capture` 8 calls, `publish_release` 2).
- **Sample from the labelled output**, so each row is (command, assigned label) and the auditor
  answers one question: *is this label right, and if not, which is?*
- **Outputs:** per-label precision with intervals, and a **confusion table** — which rules steal
  from which. The confusion table is the direct evidence about rule ordering.

## Acceptance criteria — and how each one fails

Written to be falsifiable (`LESSONS-LEARNED.md` §7: a check that cannot fail is not a check).

1. **A precision number per stratum, with an interval.**
   *Fails if:* any stratum reports a bare point estimate, or an interval computed as if the sample
   were simple-random when it was stratified.
2. **The confusion table names specific rule pairs.**
   *Fails if:* it reports only "wrong" without which label was assigned and which was correct — that
   version cannot test the ordering hypothesis and is decorative.
3. **The governance strata are separately reportable.**
   *Fails if:* governance precision is only visible inside an aggregate. Governance is ~5.9% of
   calls, so an aggregate moves by fractions of a point no matter what happens to it — the same
   trap #1 §5 already fell into and corrected.
4. **Audit decisions are recorded per row and re-checkable.**
   *Fails if:* only totals survive. A count cannot be re-adjudicated, and a wrong label and a right
   label are the same integer (`tests/test_taxonomy.py` header).
5. **A disagreement rate is reported for any row audited twice.**
   *Fails if:* no row is double-audited. Without it the precision number has an unmeasured
   auditor-error floor, and single-auditor judgment is exactly the assumption that needs a control.
6. **The result is stated as precision, never as correctness of the taxonomy.**
   *Fails if:* the write-up says "the labels are N% correct" when it measured "N% of *sampled*
   labels were judged right by *this* auditor on *this* corpus."

## What the result decides

- **High precision (≥ ~95%):** remaining sorter defects are too rare to matter for training. **Stop
  sorter work**, proceed to §4. The seven-round review loop was already past its useful end.
- **Low precision (≤ ~85%):** the model would be taught wrong answers at a rate no rule patch fixes.
  The 78.12% multi-match / rule-order design is the root cause and needs replacing, not patching.
- **Middle:** the confusion table says which strata are bad, and work is scoped to those rather than
  to the file as a whole.

**This is the point of the audit: the two outcomes demand opposite actions, and right now nobody
knows which world this project is in.**

## Cost and constraints

- Auditing is the expensive part: ~400 human judgments. The rest is scripting.
- **Sampled commands are real prompt text from private transcripts.** The sample file lives under
  `data/` (gitignored) and is **never committed**; this repo is public. Only aggregates and the
  confusion table go into `TESTS-RESULTS/`.
- `measure_taxonomy.py --show-evidence` prints matched command text and is local-only.

## Explicitly not proposed

- **An eighth review round.** Seven rounds, seven disjoint sets — `LESSONS-LEARNED.md` §16.
- **Refactoring the 141 table entries into a parser.** codex is right that the tables are the wrong
  pattern, but rewriting a mechanism before knowing whether its errors matter is backwards.
- **Training.** Training on labels of unknown quality makes any bad result unattributable — model or
  data, no way to tell.

## Open for the operator

1. Run the audit, or accept the unknown and proceed to §4 on the current labels?
2. Who audits — operator, agent with operator spot-checks on the governance strata, or both for the
   double-audited subset?
3. Sample size: ~400 (±5%) or ~1,000 (±3%) at ~2.5× the auditing cost?
