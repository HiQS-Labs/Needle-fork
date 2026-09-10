# Issue #34 agent-adapter compatibility probe

**Verdict: PASS with explicit source rejections.** The three adapters parsed current private Mac
Studio histories without exposing row data. Rejected sessions remained excluded rather than being
partially ingested.

## Verified by the probe

| Source | Files seen | Sessions accepted | Sessions rejected | User steps | Actions | Exact aliases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | 1,907 | 1,903 | 4 | 6,331 | 61,548 | 29,665 |
| Agy desktop | 81 | 79 | 2 | 692 | 26,792 | 25,268 |
| Agy CLI | 501 | 501 | 0 | 501 | 5,137 | 5,131 |
| ZCode | source-wide | 21 | 0 | 21 | 1,091 | 1,091 |

The four rejected Codex files lack one unambiguous native session identity. One rejected Agy
transcript contains malformed JSON; the other has two different records at the same `step_index`.
Exact duplicate Agy records are accepted idempotently. ZCode reported no duplicate native tool-call
identity.

The focused suite passed 14 tests. Five deliberate red controls each failed the expected test when
namespace-sensitive identity, chronological ZCode ordering, ZCode sequence tie-breaking,
duplicate-call rejection, or idempotent Agy hashing was disabled. After restoring the
implementation, the focused suite and the full non-slow suite passed.

Counts describe a live local inventory at probe time. They are compatibility evidence for the
parsers, not a frozen dataset, a label-quality result, or permission to pool sources.

## Privacy

The tracked receipt contains only source classes, counts, format versions, and rejection classes.
No native session ID, source path, prompt, command, tool argument, result, or credential was copied
from the private histories.
