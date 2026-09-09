# Taxonomy v1 — Studio corpus under the corrected positional rules

**Date:** 2026-09-09 · **Corpus source:** `~/.claude/projects` on noel's Mac Studio,
mounted read-only over SMB (whole-disk share) · **Label set:** `v1.0.0-draft` (44 labels)
· **Mapper:** `5ed316d` (`main`, post-#16) · **Machine:** MacBook Pro 14" M4 Pro, Python 3.11.15
· **Issue:** [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §2, [#2](https://github.com/HiQS-Labs/Needle-fork/issues/2)

This is the re-measurement the §2 gate was re-opened for. It **supersedes**
`../2026-09-07-taxonomy-v1-studio/` as the current gate result; that receipt keeps its
numbers as the record of what the pre-fix mapper measured.

## Result — the §2 gate

| | |
|---|---|
| Sessions | **335** |
| Tool calls | **71,547** |
| **Mapping coverage (§2 gate)** | **96.33%** |
| Unmapped | 3.67% (2,625 calls) |
| Governance share | **5.90%** (4,218 calls) |
| Labels in use | 43 of 44 |
| Static top-1 baseline | 17.12% (`read_file`) |
| **Static top-3 baseline** | **45.08%** (`read_file`, `run_script`, `search_code`) |
| Labelling wall | 149.2 s (measure pass 177.5 s total) |

Corpus extraction (`data/corpus-v1/`, gitignored, never committed): 321 sessions used /
16 skipped, **71,186 pairs**, split 274 train / 47 holdout, coverage 96.32%, 55 s wall.

## Coverage fell 2.19 points, and a control attributes all of it to the rule change

The naive comparison — 98.52% on 2026-09-07 against 96.33% today — confounds two
changes: the positional fix, and corpus drift (the Studio had 383 transcripts then and
337 now, as Claude Code rotates them). Reporting the delta without separating those
would have been unattributable.

**Control: the pre-fix mapper (`0700238`) re-run over *today's* corpus.** Both runs saw
an identical 335 sessions and 71,547 calls, so the only variable is the mapper.

| Mapper | Corpus | Coverage | Governance share | top-3 |
|---|---|---|---|---|
| pre-fix `0700238` | 2026-09-07 (383 files) | 98.52% | 7.26% | 45.82% |
| **pre-fix `0700238`** | **today (337 files)** | **98.52%** | 6.61% | 46.76% |
| **post-fix `5ed316d`** | **today (337 files)** | **96.33%** | 5.90% | 45.08% |

- **Corpus drift → 0.00 pp of coverage.** The pre-fix mapper scores 98.52% on both
  corpora. Drift moved governance share and the baselines, but not the gate.
- **Rule change → −2.19 pp**, corpus held constant. The entire drop is the fix.

## Why a *lower* number is the fix working

`unmapped` is the honest bucket. Before #16, a command that merely *displayed* or
*carried* a path could match a rule positionally — `echo mv PROJECT/1-INBOX/x.md ...`
scored `promote_capture`, `chmod +x validate.sh` scored `run_validate`. Those calls
counted as *covered*. They were covered by a **wrong** label.

The fix establishes a command's role before reading its operands, so those calls now
fall through to `unmapped`. Coverage counts *resolution*, not *correctness*, so removing
false positives can only push it down. **The old 98.52% was inflated by mislabelling.**

The governance numbers show the same thing from the other side: on the identical corpus
the fix removes **513 governance calls** (4,731 → 4,218, 6.61% → 5.90%). Governance was
over-counted by ~10.8% relative, which is exactly the class of error #2 reported —
and governance is the group this Oracle exists to get right.

## Support floor — two stragglers now, not three

At 0.10% of calls (72), below-floor labels are **flagged for supplementation**
(#1 §3b/§3c), never deleted or merged:

| Label | 2026-09-07 | today | vs floor |
|---|---|---|---|
| `pkg_manage` | 111 | **94** (0.13%) | clears |
| `park_roadmap_row` | 68 | **96** (0.13%) | **now clears** |
| `complete_doc` | — | 88 (0.12%) | clears |
| `promote_capture` | 14 | **8** (0.01%) | below |
| `publish_release` | 1 | **2** (0.00%) | below |
| `no_action` | 0 | 0 | below, by design (abstain slice, not a labelled call) |

`park_roadmap_row` crossing the floor is a direct consequence of the fix: it was
previously losing real calls to mislabelling. `promote_capture` fell 14 → 8 because six
of those were display text, not moves. Both remain #9's supplementation targets.

## Ambiguity is unchanged and still the structural risk

`multi_rule_pct` 78.09%, `compound_pct` 95.38% over 55,269 bash commands — statistically
identical to the control's 77.87% / 95.38%. The fix corrected *which* rule wins in the
positional case; it did not reduce how often multiple rules match. That remains the
open structural weakness behind the taxonomy.

## What this receipt does not establish

- **Not a correctness measurement.** Coverage counts resolution. 96.33% is not a claim
  that 96.33% of labels are *right*; the 2,625 unmapped calls were not hand-audited, and
  no sample of the 2.19 pp that moved was manually verified as genuinely display text.
- **Single corpus, single operator.** One person's transcripts on two machines.
- **Round 4 of #16 had no adversarial review.** AgentChorus #309930 closed before the
  final fix landed and CodeRabbit reported `pass` while rate-limited.

## Reproduce

```sh
SRC="/Volumes/Macintosh HD-1/Users/noelsaw/.claude/projects"   # mount smb://noels-mac-studio.local
python3.11 utils/corpus/measure_taxonomy.py --source "$SRC" \
  --out TESTS-RESULTS/2026-09-09-taxonomy-studio-postfix/raw-metrics.json
python3.11 utils/corpus/extract_claude_transcripts.py --source "$SRC" --out-dir data/corpus-v1
```

Control: the same `measure_taxonomy.py` invocation from a worktree at `0700238`.
`data/` is gitignored and must never be committed — it contains real prompt text and
this repo is public. `--show-evidence` prints matched command text and is local-only.
