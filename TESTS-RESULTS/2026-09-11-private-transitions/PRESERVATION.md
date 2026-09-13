# PR #48 evidence preservation — 2026-09-12

Historical negative result preserved, not rerun or promoted. Authority:
[#48 preservation gates](https://github.com/HiQS-Labs/Needle-fork/pull/48#issuecomment-5649880801).
Source commit: `e05b4d6a5fc54bef051be01a841731d0f7fac043`.
The landing commit is the commit introducing this receipt; its full SHA and remote
retrievability checks are posted in #48's closure comment (avoids a self-referential hash).

## Inventory and equality

| Source artifact | Source bytes | Source SHA-256 | Preservation |
|---|---:|---|---|
| `PROJECT/3-COMPLETED/PRIVATE-TRANSITIONS.md` | 7,074 | `9b75db6c931222e9ce2522ff7f87cac66a46a2f5389198a2f9259873a7871730` | Historical banner and next-step cell only; 7,469 bytes |
| `SUMMARY.md` in this directory | 5,222 | `31754430a877c1f77f480e4afdd9784e66cabc530cd37cb77504a92be7954745` | Byte-identical |
| `metrics.json` in this directory | 2,701 | `0506cdaab35c5b4b4f4212f94813f7211211ad784df851b96017d79a28f2bdd5` | Byte-identical |

All inputs/outputs were checked nonempty. Reversing only the two documented plan
edits reproduced the source bytes exactly. Source and main evaluator/test Git blobs
already match: `spike/coding_core/baselines.py` at
`8649a16a1f58333911f65d0d0f875a144bc7679e`; `tests/test_private_transitions.py`
at `d741aeb6908489b3a41e2ed36f26ed74cea3ce39`. No predictor code imported.

## Verification

Pooled receipt arithmetic checked against nonzero denominators: 45,127 training
rows; 23,442 evaluation rows; 13,239 changes. Every published count/percentage
agrees; both families retain failed gates and the overall decision remains `stop`.
In-memory negative controls for an altered correct-count, an empty score group,
and a false promotion were each rejected. This checks retained evidence, not new
predictor performance. The original run's test counts remain historical.

The preserved files contain no private prompt rows, source/session identifiers,
machine paths or private input hashes. Public code hashes and aggregate counts
are intentional. Relative links were checked, and main's README, FINDINGS and
ROADMAP history was not replaced by old branch versions. Current non-slow suite
and remote artifact verification are recorded in the closure comment.

Close without merging the branch after remote verification; retain the branch.
PR #43's operator hold is unaffected. Closing an experiment is not passing it.
