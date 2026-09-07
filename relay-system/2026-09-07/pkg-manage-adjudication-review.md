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

## Codex reviewer verdict - 2026-09-07

STATUS remains Open. The core `pkg_manage` decision is directionally right: keep the canonical
label, treat the floor as a supplementation signal, and push any training-time consolidation into a
projection. But the adjudication is not approval-ready because Q6 still has live false positives,
Q7 overstates what the 45.82% baseline proves, and two codification references point to the wrong
SOP section.

1. **Rule derivation from the rails - Grade: Pass with one stretched citation.**
   `AGENTS.md` section 6 genuinely supports "fix the measurement first": it requires relevant proof
   before success claims and warns that empty or non-failing checks report false confidence
   (`AGENTS.md:74-87`). That citation is weaker when used to prove "therefore never delete on a
   floor"; the stronger rail there is reversibility. Keeping a label is plausibly Easy to collapse
   downstream, while canonical merge is Costly to undo if re-extraction needs the Studio share
   (`AGENTS.md:54-60`, `utils/corpus/taxonomy.py:58-63`). DRY also bears, but only if
   `pkg_manage` and `run_script` are accepted as distinct concepts: DRY forbids two sources of truth
   per concept, not low-frequency concepts (`GUIDING-PRINCIPLES.md:14-16`). So the conclusion holds,
   but the AGENTS section 6 citation should be phrased as "measurement-first", not as the whole
   non-deletion rule.

2. **Strongest missing argument for merging - Grade: Underweighted.**
   The best argument is not semantic purity; it is product risk from rare-class behavior. A 45M model
   over 44 labels with `pkg_manage` at 111/74,909 can clear a micro/top-3 aggregate while never
   learning a useful decision boundary for that class. Worse, the current confidence story may not
   rescue the end-of-turn hook if the Oracle uses tuned weights: local docs say fine-tuning does not
   update the confidence head and tuned agents report `confidence` as `None`
   (`doc/finetuning.md:85-87`, `needle/__init__.py:160-163`, `needle/__init__.py:250-252`,
   `doc/apis.md:168-172`). That does not imply deleting `pkg_manage`, but it does mean the accepted
   answer should explicitly require a per-label evaluation or training projection before the hook is
   allowed to act on rare labels.

3. **0.1% as a number - Grade: Medium concern.**
   Once it only flags supplementation, 0.1% is defensible as a triage heuristic, not as a learning
   guarantee. It should not be described as "the labels that can train" without a learning-curve or
   per-label validation check. There is also a small arithmetic drift: `measure_taxonomy.py` uses
   `int(args.min_support_rate * total)`, so 0.1% of 74,909 becomes 74, even though 74/74,909 is below
   0.1% (`utils/corpus/measure_taxonomy.py:117`). Use `ceil` if the phrase means "at least 0.1%",
   or describe it as an approximate floor. A better instrument would combine absolute count,
   per-governance-group minimums, and holdout recall/calibration for labels the hook may execute.

4. **SOP.md section 4 scope - Grade: Mostly scoped, but codification step creates drift risk.**
   The trigger is tight enough in principle: use it for shared-surface, expensive-to-reverse, or
   already-argued decisions, and skip reversible local calls (`SOP.md:173-175`). That avoids direct
   conflict with "stay quiet on trivial work" (`AGENTS.md:99-102`). The weak point is step 5:
   "codify in at least two places" plus "include why" invites duplicated canonical reasoning
   (`SOP.md:206-215`) despite the North Star's "one source of truth per concept" rule
   (`GUIDING-PRINCIPLES.md:14-16`). This exact review found drift from that duplication. Prefer one
   canonical decision record plus short pointers in code/contract/changelog.

5. **Codification consistency across taxonomy, contract, project doc, changelog - Grade: Fails on
   section-reference drift, otherwise consistent.**
   The support-floor meaning is substantively aligned in code (`utils/corpus/taxonomy.py:46-63`),
   contract (`oracle/labels-v1.json:5-9`), project doc
   (`PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md:277-319`), and changelog
   (`CHANGELOG.md:66-94`). But two places say the process is `SOP.md` section 5:
   `utils/corpus/taxonomy.py:44` and
   `PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md:280`. The adjudication process is actually section
   4 (`SOP.md:165`); section 5 is anti-patterns (`SOP.md:223-239`). This is exactly the kind of
   duplicated-doc drift the repo says to avoid.

6. **Remaining argument-read-as-invocation bug class - Grade: Blocker.**
   The known `grep`/`rg` and package-manager cases are fixed by `ARG_CONSUMERS` and `PKG_MANAGERS`
   (`utils/corpus/taxonomy.py:245-277`, `utils/corpus/taxonomy.py:337-351`), and covered by tests
   (`tests/test_taxonomy.py:65-76`, `tests/test_taxonomy.py:156-187`). But `BASH_RULES` still search
   whole segments for many wrappers and data positions (`utils/corpus/taxonomy.py:195-242`). Concrete
   remaining mislabels:

   - `python3 -c "print('ruff')"` -> `run_linter` via the bare linter rule
     (`utils/corpus/taxonomy.py:219`) before `run_script` can catch Python `-c`
     (`utils/corpus/taxonomy.py:225-227`).
   - `echo pytest` -> `run_tests` via `utils/corpus/taxonomy.py:218`. Display commands are dropped
     only as tails, then restored for single-segment commands by the fallback
     (`utils/corpus/taxonomy.py:296`, `utils/corpus/taxonomy.py:330-334`).
   - `touch requirements.txt`, `cp requirements.txt /tmp/`, or `mv requirements.txt old.txt` ->
     `pkg_manage` via the bare filename branch (`utils/corpus/taxonomy.py:224`) before generic
     filesystem mutation (`utils/corpus/taxonomy.py:241`).
   - `chmod +x validate.sh` or `mv validate.sh scripts/` -> `run_validate` via the bare script name
     (`utils/corpus/taxonomy.py:200`) before `fs_mutate`.
   - `nohup sleep 1 > validate.sh` -> `run_validate` because `nohup` is treated as preamble/wrapper
     but the restored whole segment still scans the redirection target
     (`utils/corpus/taxonomy.py:292-295`, `utils/corpus/taxonomy.py:330-350`).
   - `timeout 5 echo pytest` -> `run_tests`; same wrapper/data problem, with `timeout` only
     recognized as preamble when followed by digits (`utils/corpus/taxonomy.py:292`).
   - `xargs -I{} echo pytest {}` -> `run_tests`; only `xargs echo` without flags is display-dropped
     (`utils/corpus/taxonomy.py:296`).
   - `git bisect run echo validate.sh` -> `run_validate`; `git bisect` is not classified by the git
     rules (`utils/corpus/taxonomy.py:212-215`), so governance filename matching wins.
   - `docker run --rm ruff:latest --help` -> `run_linter`; there is no `docker` rule, so the image
     name is read as a linter invocation.
   - `make validate.sh` or `make relay-drive.sh` -> `run_validate`/`start_relay` via governance
     filename rules (`utils/corpus/taxonomy.py:200-201`) before `run_build`
     (`utils/corpus/taxonomy.py:220`), even if these are make targets rather than direct script
     invocations.

   The fix should be conceptual, not another list of special cases: identify leading programs whose
   operands are data, wrappers whose child command must be parsed separately, and interpreters where
   `-c`/heredoc bodies are script content rather than outer-shell tokens. Add regression tests for
   each class, and watch them fail first per `AGENTS.md:79-82`.

7. **Split/holdout and baseline framing - Grade: Medium concern.**
   Splitting by session is correct for leakage control because adjacent pairs share context
   (`utils/corpus/extract_claude_transcripts.py:89-92`, `utils/corpus/extract_claude_transcripts.py:117-118`).
   The reported 45.82% top-3 majority baseline is useful as a corpus sanity check, but it is not
   sufficient as "the number the model is judged against." Both extraction and measurement compute
   baselines from aggregate label counts rather than a train-prior applied to holdout or a holdout
   distribution (`utils/corpus/extract_claude_transcripts.py:140-145`,
   `utils/corpus/extract_claude_transcripts.py:172-173`, `utils/corpus/measure_taxonomy.py:107-114`,
   `utils/corpus/measure_taxonomy.py:126-127`). A model can beat 45.82% micro top-3 while failing
   every rare governance or package-management label. The adjudication should require at least
   holdout top-k, macro/per-group recall, and per-label support/confusion for any label kept as an
   actionable hook target.

Verification: static, line-numbered review only. I did not run the project gate or execute taxonomy
tests, per the relay instruction to append reviewer findings only.
