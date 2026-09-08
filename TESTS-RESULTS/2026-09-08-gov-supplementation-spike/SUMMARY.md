# #9 spike — do the five zero-support governance labels exist, and is the prompt correlation usable?

**Date:** 2026-09-08 · **Issue:** [#9](https://github.com/HiQS-Labs/Needle-fork/issues/9)
Read-only census over local git history + the CLIO prompt log. No prompt text or file contents
were read into any output.

## Q0 — do the events exist? **Yes, in quantity.**

Detected by **path and rename**, not commit message: a rename across PDDA lifecycle folders *is*
the governance act, whereas a message is the author's prose about it.

| label | commits (all repos) | corpus support before |
|---|---|---|
| `park_roadmap_row` | 791 | 68 |
| `cut_release` | 349 | 0 |
| `publish_release` | 263 | 1 |
| `complete_doc` | 156 | 0 |
| `promote_capture` | 67 | 14 |

## Q0b — but most `publish_release` is not ours

`publish_release` was dominated by **third-party clones** — `dify` (152), `nmig` (32),
`shopify_python_api` (19) — whose tags are *upstream's* releases, not our governance acts.
Restricting to the 8 repos that appear in the CLIO log drops it from **263 → 11**.

Kept: `XYZ-forge`, `LTVera-Pandas`, `pdda`, `rebalanceOS`, `AEGIS-Sleuth-Slackbot`,
`Needle-fork`, `XYZ-code-intelligence`, `giant-brains-claude-skills`. Dropped 13 third-party.

## Q1 — does the prompt→event correlation survive per label? **Mostly NO.**

Null control: prompt timestamps shuffled uniformly across each repo's prompt span, 5 trials.

| label | events | 15 min real/null | lift | verdict |
|---|---|---|---|---|
| `cut_release` | 348 | 41% / 13% | **+28pp** | **strong** |
| `complete_doc` | 149 | 25% / 12% | **+13pp** | moderate |
| `park_roadmap_row` | 772 | 20% / 13% | +7pp | weak |
| `promote_capture` | 48 | 15% / 18% | **−3pp** | **no signal** |
| `publish_release` | 11 | 0% / 15% | **−15pp** | **no signal**, n too small |

**The aggregate finding did not generalise.** XYZ-forge's headline **+38.5pp** lift was measured
over *all* commits — dominated by ordinary coding work following prompts. Per governance label the
picture is far weaker, and for two labels it is absent entirely.

Plausible mechanism, untested: `cut_release` is a deliberate act performed right after an explicit
instruction, so a prompt precedes it. `promote_capture` is a `git mv` that happens in batch, via
`pdda.sh` automation, or folded into a larger commit — so no prompt sits immediately before it.

## What this changes

1. **Prompt correlation is not the primary source.** It is viable for `cut_release`, partially for
   `complete_doc`, and not at all for `promote_capture` / `publish_release`.
2. **#1 §3c does not require a prompt.** "Mine git/PR history" can build rows whose *context* is
   reconstructed from repo state and preceding commits, with the governance act as the label. That
   path is unaffected by these lift numbers and now looks like the better primary route — the
   events are there (Q0), only the prompt pairing is unreliable.
3. **Two labels may be unfixable from git alone.** `promote_capture` has **48** events in our repos
   and `publish_release` **11** — both under the 75-row support floor even before any pairing loss.
   They need a different source, or an explicit decision to keep them below floor and supplement by
   synthesis (`taxonomy.py`'s support floor is a *supplementation* gate, never a delete gate).

## Method notes

- `spike/corpus/gov_event_census.py` — one `git log --all --name-status -M` pass per repo.
- `spike/corpus/gov_lift.py` — per-label lift with the shuffled-timestamp control.
- Both read-only, aggregate output only, per `measure_taxonomy.py`'s precedent.
