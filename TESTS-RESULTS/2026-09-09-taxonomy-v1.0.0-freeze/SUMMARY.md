# Label vocabulary frozen as v1.0.0

**Date:** 2026-09-09 · **Corpus:** Studio `~/.claude/projects` over SMB · **Mapper:** `7cd7150`+
· **Machine:** MacBook Pro 14" M4 Pro, Python 3.11.15
· **Issue:** [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §1 §2

`LABEL_SET_VERSION` cut from `v1.0.0-draft` to **`v1.0.0`**; `oracle/labels-v1.json` regenerated
from `taxonomy.py` through this repo's own `build_schema`. 44 labels.

## State at the freeze

| | |
|---|---|
| Sessions / tool calls | 335 / 71,763 |
| **Mapping coverage** | **96.41%** |
| Governance share | 5.91% (4,241 calls) |
| Static top-3 baseline | **45.16%** |
| Multi-rule match rate | **78.12%** |
| Tests | **197 passed** |

The version guard was verified to fire: a contract still stamped `v1.0.0-draft` is now refused by
`serialize.load_schemas` with `RuntimeError`. Any artifact built under the draft is rejected
rather than silently mixed with post-freeze data.

## What is frozen, and what is explicitly not

**Frozen: the label NAMES.** The 44-label vocabulary and its published schema are the cross-repo
contract. Adding, removing or renaming a label is now a version bump.

**Not frozen: the sorter.** `taxonomy.py` decides *which* label a command gets, and it is still
under active repair — see below. Freezing the names does not assert the sorter is correct, and
the two artifacts version independently.

**Not frozen: supplementation.** The contract's `support_floor.action` is `"supplement"` —
*never deleted or merged on the floor alone*. `promote_capture` (8 calls) and `publish_release`
(2) sit below the floor and are kept on that basis, with `no_action` at 0 by design. **Freezing
therefore commits the project to #9.** If supplementation is abandoned, v1.0.0 ships three labels
with no training signal and a contract clause that was never honoured.

## Why freezing was judged defensible with the sorter still open

The final pre-freeze review (`codex`, `relay-system/2026-09-09/v1-freeze-final-round.md`) returned
**VERDICT: FAIL** — and its own reasoning is why the freeze still proceeds:

> "Keeping rare labels in the frozen vocabulary is defensible under the stated contract… deleting
> them at the taxonomy root would be the Costly and less reversible move. **The freeze blocker
> here is sorter correctness, not rarity alone.**"

> "For v1.0.0, the contract can freeze label names while still requiring sorter QA and
> supplementation."

Its blocker was fixed before this freeze (`7cd7150`).

## The honest limit on every number above

**96.41% coverage counts RESOLUTION, not CORRECTNESS.** 78.12% of bash commands match more than
one rule, and the winner is decided by rule order. The ~2,570 unmapped calls have never been
hand-audited, and no sample of the labelled calls has been either. codex again:

> "The 78.1% multi-match rate… blocks any claim that 96.40% coverage means correctness."

Nothing in this receipt should be read as evidence that the labels are right — only that the
sorter assigns one to 96.41% of commands.

## Seven rounds, seven disjoint defect sets

| Round | Reviewer | Found |
|---|---|---|
| 1 | corpus re-extraction diff | 3 regressions no unit test caught |
| 2 | agy | 6 defect categories |
| 3 | Codex Astra | 5 escapes |
| 4 | Codex Astra (close) | 3 blockers |
| 5 | agy | 5 classes, 21 counterexamples, **21/21 reproduced** |
| 6 | CodeRabbit | 2 defects *introduced by* round 5's fix |
| 7 | codex | 1 blocker: the flag allowlist failing a third time |
| — | own probe | `git tag -m ruff v1` → `run_linter`, reported by nobody |

Seven disjoint sets is not evidence the eighth does not exist. The vocabulary is frozen; the
sorter is not, and its remaining work is tracked in #17.
