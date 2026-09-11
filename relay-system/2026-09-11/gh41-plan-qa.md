# RELAY · GH-41 targeted augmentation plan QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-11.
-->

NEXT: Reviewer
STATUS: Open
ROUND: 2 / 3

## ▶ TAKE YOUR TURN — read this first (works for ANY agent: Claude, Codex, agy)
1. **Read this whole file** (header, Setup, Ground rules, every block in the Log).
2. **Check it's your turn:** `NEXT` (top) names the role to act. Confirm you are bound to it and the
   last Log block isn't already yours. If not → STOP and reply "wrong window — nudge the <other> window."
3. **Do your role's work** on the artifact named in Setup:
   - **Reviewer:** review vs the Definition of Done → graded findings
     (`[Blocker]`/`[Should]`/`[Nit]`/`[Pass]`), each with a concrete fix → end with the exact uppercase marker **VERDICT: Approved**, **VERDICT: Changes requested**, or **VERDICT: Blocked**
     (Approved | Changes requested | Blocked). **Review the whole file, not just the diff** (GH-268):
     a beta test had this loop reach `Approved` in two rounds while an independent audit of the same
     branch found 20 issues (1 critical, 4 high) — every one of them in the pre-existing code the
     change sat on, which nobody had read. Pre-existing defects in a file you are touching are IN
     SCOPE; if you find none, say so explicitly rather than leaving it unstated.
     **Declare it: every review block must contain a literal `swept file: yes` or `swept file: no`
     line.** Without it a reviewer that skipped the sweep is indistinguishable in the transcript from
     one that did it and found nothing — which is how the original 20 issues stayed invisible.
     Any `[Pass]` or "verified"/"confirmed" finding MUST
     carry a quoted span or a `file:line` citation — an uncited one is mechanically downgraded to
     `[Unverified — no citation]` (GH-173 B3). Do **not** edit the artifact; only append findings here.
   - **Producer:** log a disposition for every open finding (Implemented / Modified / Declined + why),
     make the change, then add new work.
4. **Append ONE block** at the very bottom, directly **above** the marker line. Never edit earlier turns.
5. **Update the header:** flip `NEXT`; set `STATUS` (`Approved` closes — Reviewer only; else `Open`);
   the Producer bumps `ROUND` when opening a new cycle. If the max `ROUND` ends without `Approved`,
   set `STATUS: Escalated`.
6. **Commit only the relay file** (`relay(gh41-plan-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md** — the read-only path that
  `relay-drive.sh --artifact-file /Users/noelsaw/Documents/GH Repos/Needle-fork-gh41-augmentation/PROJECT/2-WORKING/GH-41-TARGETED-AUGMENTATION.md` seeds into the isolated worktree (read it there; do NOT edit it).
- Reviewer: codex   ·   Producer: claude-a
- Started: 2026-09-11
- Definition of Done: the plan is grounded in the recon map and current source; isolates issue #25; extends the canonical serializer without a second writer; bars generated rows from evaluation; specifies deterministic, privacy-safe, atomic output; contains falsifiable red controls, rollback, and a bounded implementation surface; and leaves model training/deployment outside the initial milestone.

Review the plan in full, then inspect these committed sources and tests:

- `PROJECT/2-WORKING/RECON-GH-41-AUGMENTATION.md`
- `utils/corpus/serialize.py`
- `utils/corpus/build_oracle_jsonl.py`
- `needle/model/finetune.py`
- `tests/test_serialize.py`
- `tests/test_generate.py`

Answer explicitly:

1. Are the current-system claims grounded, and does the plan choose the correct existing writer?
2. Is the issue #25 collision boundary concrete enough to prevent shared-file/data overlap?
3. Can the proposed contract actually prove training-only use, grounded provenance, deterministic output, pair completeness, deduplication, and privacy-safe reporting?
4. Are any required acceptance checks missing, vacuous on empty input, or impossible to falsify?
5. Is the initial implementation smaller than modifying the public generic augmentation API, without creating a redundant long-lived subsystem?
6. Are blast radius, rollback, dependencies, stop conditions, and deferred Phase 3 claims honest?

Cite `file:line` for every finding and give the cheapest concrete fix.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer · Round 1

swept file: yes

Verdict: Changes requested

- [Pass] The plan selects the canonical writer and keeps the generic public augmentation API out of the initial surface: it requires `serialize.to_finetune_row` and forbids a second serializer (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:66-71`), matching the existing five-field row owner (`utils/corpus/serialize.py:96-116`) and the generic provider-backed path (`needle/model/finetune.py:158-189`). No pre-existing defect in the reviewed plan file undermines this choice.
- [Blocker] “Training-only” is asserted but not preserved or enforced after composition. The required `split`/generated metadata exists only in the candidate contract (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:59-60,68-71`), while `to_finetune_row` drops it (`utils/corpus/serialize.py:110-116`); moreover the trainer automatically draws validation rows from its input unless `val_split` is zero (`needle/model/finetune.py:360-366`). Cheapest fix: specify a generated-only train artifact plus a manifest/hash that identifies every emitted row, require Phase 3 assembly to set `--val-split 0` for mixed training data and use a separately supplied real holdout, and add a red test proving any generated row in validation/evaluation is rejected.
- [Blocker] “SHA-256 provenance” does not yet prove grounding: merely requiring a hash and identities (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:68-70`) gives the composer no trusted bytes or manifest against which to recompute them, so the promised “ungrounded rows fail” check (`:75`) can be satisfied by attacker/self-declared metadata. Cheapest fix: define the hash preimage and canonical encoding, require a reviewed seed manifest (or seed record) whose digest is recomputed, bind each candidate to that digest, and test a one-byte seed/candidate mismatch red.
- [Should] The issue #25 boundary names concepts but not collision-proof paths or identifiers: “sampler, correction manifests, and evaluation-capacity lane” (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:43-45`) and “no issue #25-owned audit or manifest file changes” (`:77`) cannot prevent two lanes from reading/writing the same data, while Phase 3 later requires disjointness from #25 evidence (`:99`). Cheapest fix: list GH-41's exact new source/test/fixture/output paths and the exact #25 paths/manifest namespaces forbidden for both reads and writes; define disjointness by stable source IDs/hashes without consuming #25-owned output.
- [Should] Pair completeness and deduplication are underspecified. The plan requires two roles and “only request-field change” (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:70`) plus exact/normalized request deduplication (`:84`), but does not define pair ID grouping, normalization, hash collision behavior, ordering/tie-breaks, whether duplicates are checked across seeds and outputs, or which non-request fields must be byte-identical. Cheapest fix: add a normative canonicalization/key section and table of pair invariants, then red-test reversed input order, duplicate-across-pairs, duplicate-against-real-source, extra field drift, missing/extra role, and hash collision.
- [Should] Publishing JSONL and report is not atomic as a pair. The promise says neither is published on any validation failure (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:59-62`), but two independent final paths cannot be committed atomically with sequential `os.replace` calls; the existing builder illustrates this gap by replacing outputs one by one and writing stats afterward (`utils/corpus/build_oracle_jsonl.py:103-123`). Cheapest fix: publish a uniquely named immutable run directory containing both files and atomically replace one pointer/manifest only after fsync/close, with a fault-injection red test between staging and commit.
- [Should] The red controls remain procedural rather than falsifiable acceptance criteria: “deliberate serializer bypass” and “every new gate” (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:75-76,90-92`) do not state the observable failure, and empty-output/report checks do not demand nonzero fixture cardinality before byte/distro assertions. Cheapest fix: name each focused test and expected exception/exit/no-final-files condition, assert fixture and output counts are nonzero before comparisons, and require the bypass mutant to make the focused test fail before restoration.
- [Should] Phase 3's decision rule is not executable: “material” gain/degradation (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:99-102`) has no preregistered thresholds, uncertainty method, minimum holdout size, or stop rule, so a measured result cannot determine advance/stop without post-hoc judgment. Cheapest fix: keep Phase 3 deferred but require a pre-run experiment addendum that freezes those values and commands before any training; do not claim readiness until it exists.
- [Pass] Blast radius, dependency choice, rollback, and deployment deferral are otherwise honest and bounded: stdlib/no provider is explicit (`.relay-artifacts/GH-41-TARGETED-AUGMENTATION.md:47-50`), removal is the rollback (`:52-62`), and runtime authority is explicitly excluded (`:95-109`).

Handing off to Producer — go to the Producer window and say “take your turn”.

### Producer · Round 2

- Implemented — training-only enforcement now specifies a generated-only artifact, row-binding manifest, `--val-split 0`, separate real holdout, forbidden IDs, and a named red test.
- Implemented — grounding now has a separate reviewed-seed trust boundary, canonical hash preimage, recomputation, and a one-byte drift red test.
- Implemented — exact GH-41 owned paths and #25 reserved code/data/test namespaces are named; later disjointness uses an explicitly exported forbidden-ID manifest rather than reading #25 artifacts.
- Implemented — canonicalization, ordering, collision response, duplicate scope, and complete counterfactual pair invariants are normative.
- Implemented — publication is one immutable run-directory rename after close/fsync, with a fault-injection red test.
- Implemented — named red tests assert exact failures, nonzero cardinality, no final run, and canonical serializer use.
- Implemented — Phase 3 is blocked on a reviewed preregistration addendum containing its sample, metric, uncertainty, thresholds, commands, and stop rule.

Plan updated at `PROJECT/2-WORKING/GH-41-TARGETED-AUGMENTATION.md`; no implementation started.

Handing off to Reviewer — review the revised artifact and close Approved only if every blocker is resolved.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
