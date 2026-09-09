# Label correctness — the first measurement, 84.7%

**Date:** 2026-09-09 · **Mapper:** `main` @ `13a156b` · **Label set:** `v1.0.0` (44 labels)
· **Sample:** 399 rows, 40 strata, seed 20260909 · **Machine:** Mac16,8, Python 3.11.15
· **Refs:** [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §2 · `LESSONS-LEARNED.md` §15

Every previous number about the sorter counted **resolution** — did a call get *a* label
(coverage 96.41%). This is the first measurement of whether the label is **right**.

## Protocol

Stratified sample (floor 8/label + √count remainder) so the governance labels the Oracle exists
for get real coverage. **Blind**: both auditors saw only the call text, never the sorter's answer.
Two independent auditors (Claude, agy) labelled all 399; `codex` adjudicated the 82 disagreements
without seeing the sorter's label either.

Gold = the auditors' shared label where they agreed (317 rows), codex's adjudication where they
did not (82 rows).

## Result

| | n | precision | 95% CI |
|---|---|---|---|
| **Overall (adjudicated)** | 399 | **84.7%** | 80.9–87.9% |
| **Governance strata** | 113 | **95.6%** | 90.1–98.1% |
| Everything else | 286 | 80.4% | 75.4–84.6% |

Raw auditor passes before adjudication: Claude **78.9%** (74.7–82.7), agy **83.7%** (79.8–87.0).
**Inter-rater agreement was 79.4%** (75.2–83.1) — *lower* than agy's agreement with the sorter.
That bounds how precisely the sorter can be scored at all, and is itself the finding.

codex sided with Claude on 36 ties, with agy on 37, and chose a **third** label on 9. An even
split is what genuine ambiguity looks like; a lopsided one would have meant a bad auditor.

## Where it fails — concentrated, not spread

| label | precision | 95% CI |
|---|---|---|
| `unmapped` | **0/11 = 0%** | 0–26% |
| `run_script` | 5/15 = 33.3% | 15–58% |
| `sys_inspect` | 4/10 = 40.0% | 17–69% |
| `pkg_manage` | 4/9 = 44.4% | 19–73% |
| `run_build` | 4/9 = 44.4% | 19–73% |

**`unmapped` scored 0 of 11.** Every call the sorter declined to label had a real label available.
Coverage counts abstention as honest; this says most of it was not. That is the false-negative
side, and coverage is structurally blind to it.

The rest are the **generic buckets** — `run_script`, `sys_inspect`, `run_build` — absorbing more
specific intents.

## The good news, and it is the part that matters most

**Governance precision is 95.6%.** Those 13 labels are what this Oracle exists to predict, and
they are the *strongest* stratum, not the weakest — the opposite of what seven rounds of
adversarial review on governance spoofing would have led anyone to predict.

## A claim of mine that the adjudicator rejected

I observed that on the 240 rows where both auditors were confident *and* agreed, the sorter scored
**96.2%**, versus 52.8% on the remaining 159 — and argued the taxonomy was ambiguous rather than
the sorter broken. codex graded that a **[Blocker]**:

> "The 'sorter is good because it scores 96.2% on confident agreements, therefore the taxonomy is
> ambiguous' argument is **circular** if the confident-agree subset is treated as ground truth
> without checking whether confidence tracks easy/rule-shaped rows. It is evidence the sorter
> handles easy cases, not proof that lower overall score is caused by taxonomy ambiguity."

**It is right.** Many "clear" rows are clear because they are decidable from a filename
(`Edit CHANGELOG.md` → `update_changelog`), which the sorter can hardly get wrong. The split is
real; the *causal* reading of it was not established.

Partial counter-evidence, recorded as partial: murkiness is **concentrated by label**, not spread
by difficulty — `cut_release` and `session_control` were contested on 9 of 9 rows each, `gh_cli`
and `update_pr` on 9 of 10, and twelve labels carry 62% of all contested rows. That is a property
of those definitions. It weakens the circularity objection without settling it; settling it needs
a difficulty measure independent of auditor confidence.

## Taxonomy findings from the adjudicator

- **[Should] A real v1.0.0 gap: commenting on or updating a GitHub *issue*.** `update_pr` says PR,
  `read_issue` is read-only, `gh_cli` is a fallback. Recommended: add `update_issue` in v1.0.1.
- **[Should] `find_files`/`read_file`, `apply_patch`/`fs_mutate`, `search_code`/`sys_inspect`** are
  boundary ambiguities needing written **precedence rules** for mixed commands, not new labels.
- **[Should] `search_code`/`unmapped`** was mostly *auditor* error, not a taxonomy defect.
- codex's overall recommendation: **keep the 44 labels**, add precedence guidance, add one label.

## What this does not establish

- **One corpus, one operator.** 399 rows from one developer's sessions.
- **Auditor error is unmeasured in absolute terms.** 79.4% inter-rater agreement is a *ceiling
  artifact*: the sorter cannot be scored more finely than the auditors agree.
- **Not model accuracy.** This measures the labels the model would be trained on, not the model.
- **Claude is not an independent auditor.** I wrote the sorter; my pass is expected to be biased
  *toward* it. That my score (78.9%) came in *below* agy's (83.7%) is unexplained and worth noting
  rather than explaining away.
- The 10.7% of calls with no renderable text (`delegate_agent`, `track_todo`, `ask_user`,
  `no_action`) are outside the frame — they come from a direct tool-name mapping.

## Reproduce

```sh
python3.11 utils/corpus/sample_for_audit.py --source "<transcripts>"   # writes data/audit/ (gitignored)
python3.11 utils/corpus/score_audit.py --auditors claude,agy --out <receipt>
```
