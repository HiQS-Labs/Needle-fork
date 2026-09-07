---
Goal: Review the pkg_manage adjudication, its codification, and the new SOP.md §4 process
Date: 2026-09-07
Reviewer: codex
NEXT: Reviewer
STATUS: Open
---

# Context

You are the second opinion on a decision that has **already been made and committed**. A previous
consult reached only ONE advisor (Gemini via aider); Codex and agy were both unavailable at the time.
Gemini agreed with every point — but it was handed the framing below, so its agreement is
corroboration, not verification. **Your job is to challenge the framing itself.**

Read, in this order:

- `GUIDING-PRINCIPLES.md`, `AGENTS.md`, `SOP.md` (the governance rails this was decided against)
- `utils/corpus/taxonomy.py` — the decision record at `SUPPORT_FLOOR_RATE` / `SUPPORT_FLOOR_ACTION`,
  and `BASH_RULES` / `ARG_CONSUMERS` / `PKG_MANAGERS` / `label_segment`
- `oracle/labels-v1.json` — the `support_floor` block
- `PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md` — the full decision record at the end
- `SOP.md` §4 "Adjudicating a contested decision" — the new process
- `tests/test_taxonomy.py` — in particular the tests named in Q6

## What was decided

`pkg_manage` measured 60 calls against a 0.1% support floor (74 calls), and the open question was
whether to merge it into `run_script`. Auditing the measurement first found two bugs in our own
labeler: `uv add ruff` scored as `run_linter` (the linter regex matched the package NAME as if it
were an invocation), and dependency inspection (`pip list`, `brew list`, `npm ls`) had been tightened
out of `pkg_manage` into `unmapped`. Fixed, `pkg_manage` measures 111 — above the floor. The
decision dissolved.

The durable outcome recorded was a rule: **the support floor is a supplementation gate, not a
deletion gate.** A label below it is flagged for issue #1 §3b/§3c synthesis, never deleted or merged
on the floor alone; consolidation for training belongs at the dataloader as a projection.

Corpus context: 74,909 pairs / 359 sessions, mapping coverage 98.52%, governance share 7.26%, static
top-3 majority baseline 45.82%, 44 labels of which 40 clear the floor. The model is 45M parameters
and predicts ONLY a label name (no arguments).

# Questions

Answer each one directly. Cite `file:line` wherever you disagree with a specific claim.

1. **Is the rule actually derived from the rails, or rationalised after the fact?** The claim is that
   "supplementation gate, not deletion gate" follows from `AGENTS.md` §6 (a self-chosen threshold
   deleting labels is "a check that reports confidence it never earned"), `GUIDING-PRINCIPLES.md` DRY
   ("one source of truth per concept" is about duplication, not rarity), and `AGENTS.md` §3
   (reversibility is asymmetric). Does each citation genuinely bear, or is any of them stretched to
   fit a conclusion already reached?

2. **What is the strongest argument FOR merging that is missing?** The one considered was
   calibration: a 45M model over 44 classes, where a label with ~111 examples out of 74,909 (0.15%)
   may be poorly calibrated and fire spuriously in the end-of-turn hook, which suppresses below a
   confidence floor (issue #1 §5 requires confidence separation). Is that argument adequately
   answered, under-weighted, or is there a better one — e.g. class imbalance, softmax dilution, or
   the top-3 surface making rare labels worse than useless?

3. **Is 0.1% defensible as a number at all, now that it no longer deletes anything?** If a threshold
   only flags for supplementation, is it doing real work, or is it ceremony? Would a different
   instrument (absolute count, per-group floor, learning-curve check) be more honest?

4. **Is `SOP.md` §4 correctly scoped, or does it over-generalise from a single case?** Check it
   against the rest of `SOP.md` and `AGENTS.md` for contradiction, duplication, or drift —
   `GUIDING-PRINCIPLES.md` warns specifically against a canonical thing living in two places.
   `AGENTS.md` §8 says "stay quiet on trivial work"; does §4's six-step ceremony conflict with that,
   and is its trigger condition drawn tightly enough to avoid it?

5. **Is the decision codified consistently across all four places?** `utils/corpus/taxonomy.py`,
   `oracle/labels-v1.json` (`support_floor`), `PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md`,
   `CHANGELOG.md`. Flag any drift, contradiction, or claim in one that the others do not support.

6. **Is there a REMAINING instance of the "argument read as invocation" bug class?** This bug class
   has now appeared twice: a `grep` whose PATTERN mentioned a governance word scored as
   `run_pdda_check`/`start_relay`, and `uv add ruff` scored as `run_linter`. Both were fixed by
   making a leading program consume its arguments as data (`ARG_CONSUMERS`, `PKG_MANAGERS`). **Audit
   the remaining `BASH_RULES` in `utils/corpus/taxonomy.py` for a third instance.** Concretely: can
   any rule still fire on a token appearing as an ARGUMENT rather than as the command being run?
   Consider `xargs`, `env`, `timeout`, `watch`, `git bisect run`, `nohup`, `docker run`, `make`
   targets, and any rule matching a bare filename (e.g. `requirements.txt`, `validate.sh`,
   `pdda.sh`). Name specific commands that would be mislabelled, with the rule that catches them.

7. **Is the split/holdout and baseline reporting sound?** The split is by SESSION (299/60), and the
   number the model is judged against is the static top-3 majority baseline of 45.82%. Any flaw in
   that framing?

Flag anything wrong, missing, incorrectly scoped, or over/under-engineered. Being contrarian is the
point — the previous advisor agreed with everything, which is exactly the failure mode this turn
exists to catch. If you believe the decision is simply correct, say so plainly and say which of the
seven questions you would still change your mind on.

Write your verdict below. Set STATUS to Approved if it holds up, or leave it Open with your findings
if it does not.

<!-- ▽ RELAY AUTOMATION: DO NOT MODIFY THIS BLOCK ▽ -->
▶ TAKE YOUR TURN (codex)
<!-- △ RELAY AUTOMATION: DO NOT MODIFY THIS BLOCK △ -->
