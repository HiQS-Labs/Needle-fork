# Recon Map — deterministic Codex, Agy, and ZCode transcript adapters

Commit: `216f336` · Mode: source reads + private aggregate/schema probes over the MacBook and
Mac Studio · Lanes run serially because this session did not delegate repository work

## Subject and change class

The subject is an offline path from three native agent-history formats to one ordered stream of
user and tool-action events. The first change adds reusable readers under `utils/corpus` and
synthetic contract tests. It does not add these sources to the Claude evaluation population,
change the frozen taxonomy, create training rows, or touch inference, packaging, or model
numerics.

**Reversibility: Easy.** The implementation is additive and generated outputs stay under ignored
`data/`. Rollback is a normal revert.

## Entry points and call paths

| Source | Canonical input | Native ordering and identity | Adapter path |
| --- | --- | --- | --- |
| Codex | `~/.codex/sessions/**/*.jsonl` | one `session_meta.payload.id` per accepted file; response items are in file order; current function/custom calls carry `call_id` | file discovery → strict JSONL read → user/action normalization → shared validator |
| Agy | `~/.gemini/{antigravity,antigravity-cli}/brain/*/.system_generated/logs/transcript.jsonl` | parent directory is the session; each planner response has an ordered `tool_calls` list keyed by step and position | canonical-file discovery → strict JSONL read → exact-repeat removal → `(step_index, call position)` identity → shared validator |
| ZCode | `~/.zcode/cli/**/*.jsonl` | rows carry `sessionId`, timestamps, and sequence numbers; scheduled calls carry `toolCallId` | file discovery → strict JSONL read → timestamp/sequence/native-ID order → user/action normalization → shared validator |

All three end at a common `NormalizedTranscript` / `NormalizedStep` contract. A later corpus
builder may translate those steps into q1 pairs, but this change stops before that boundary.

## Existing seams that remain unchanged

| Seam | Location | Contract preserved |
| --- | --- | --- |
| Claude reader | `utils/corpus/transcript_events.py` | Claude event identity and parsing remain byte-for-byte behaviorally unchanged |
| Claude corpus builder | `utils/corpus/extract_claude_transcripts.py` | Claude-only user/action sequence remains the training-data entry point |
| Frozen source verifier | `utils/corpus/build_experiment_manifest.py` | saved Claude events continue to be reconstructed from the same reader |
| Audit inventory and draw | `utils/corpus/measure_taxonomy.py`, `utils/corpus/sample_for_audit.py` | current evaluation population, exclusions, and 1,000-row gate do not admit other agents |
| Label mapper | `utils/corpus/taxonomy.py` | `v1.0.0` remains the single label source; adapters preserve native tool names rather than silently assigning labels |

## Verified source shapes

- Codex records use `{timestamp, type, payload}`. Tool calls appear as `response_item` payloads;
  current function/custom calls carry `call_id`, while legacy search calls can lack a native ID and
  use their stable source-record position. User messages are response items with a `role` and
  content blocks. Four observed files lack one usable native session identity and are rejected.
- Agy has 80 canonical Antigravity and 501 canonical Antigravity CLI transcript files on the
  Studio. The chunk files and `transcript_full.jsonl` are alternate duplicate representations, so
  recursive ingestion would double or multiply actions. Three canonical desktop transcripts repeat
  a `step_index`: two repeat the exact record and one conflicts; none of those repeated rows carries
  a tool call. Exact repeats can be removed idempotently, while a conflict makes that session
  unusable. Tool call objects contain only `name` and `args`, so no native call ID exists.
- ZCode scheduled 1,091 observed calls with zero repeated `(sessionId, toolCallId)` keys. A
  `turn_started` payload carries string user input. A `tool_call_scheduled` payload carries the
  complete tool name and dictionary input; later ledger records repeat the call state and must not
  be counted as new actions.

These are private inventory/schema observations, not public corpus statistics and not evidence that
the resulting histories are interchangeable with Claude data.

## Contracts and failure paths

- A source namespace is explicit, non-secret, and validated. Absolute mount prefixes never enter
  a session or event digest.
- Session and event IDs are SHA-256 digests over versioned canonical JSON material. Dictionary key
  order cannot change an identity.
- Each transcript has one native session. Missing or conflicting session identity, malformed JSON,
  non-dictionary tool input, duplicate native action identity, or conflicting Agy step identity is
  a hard error. Exact duplicate Agy rows are idempotent. No partial stream is returned.
- Action ordinals are contiguous after source-specific filtering. Codex and Agy retain canonical
  file order. ZCode sessions can span files, so they use required timestamps, sequence numbers, and
  native record IDs as deterministic ordering keys.
- The normalized event retains `source_tool` and source input. Tool aliases are explicit and
  versioned; unknown tools remain unknown rather than being forced into a known class.
- Raw prompts and tool arguments are private. Any eventual serialization belongs under ignored
  `data/`; public receipts may contain aggregate counts and hashes only.

## Build and rollback

The adapters use the Python standard library and are outside the installed `needle` package. Tests
use synthetic fixtures only. Focused tests cover each parser, relocation-stable identity, ordering,
duplicate rejection, malformed input, and the shared schema; the full non-slow suite remains the
merge gate. Deliberately breaking identity, ordering, and duplicate checks must make focused tests
fail before the implementation is accepted.

## Unknowns kept outside this change

| Unknown | Why it matters | What settles it |
| --- | --- | --- |
| Cross-agent label quality | Similar tool names do not prove equivalent intent | a separate blinded mapping audit by source agent |
| Domain transfer to Claude | More actions can still teach another scaffold's habits | source-separated training ablations and an untouched Claude-only test |
| Whether results improve prediction | This adapter contract deliberately omits tool results | a later privacy and value ablation with a separate versioned event format |
| Whether extra histories clear issue #25 | That gate is explicitly Claude-only | only new eligible Claude sessions and the unchanged readiness command |

## Blast radius

The radius is `utils/corpus`, synthetic tests, and this documentation. Runtime SDK users, daily
release behavior, checkpoint formats, MLX boundaries, the native engine, and all frozen evaluation
manifests are unaffected.
