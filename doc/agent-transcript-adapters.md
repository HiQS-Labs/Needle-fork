# Agent transcript adapters

Issue #34 adds read-only adapters for Codex, Agy/Antigravity, and ZCode histories. They return the
same `NormalizedTranscript` metadata and ordered `NormalizedStep` records. They do not create Oracle
training rows or change the Claude-only evaluation gate.

## Python API

Add `utils/corpus` to `sys.path`, then call the adapter for the native source root:

```python
from pathlib import Path

from codex_transcript_adapter import iter_transcripts

for meta, steps in iter_transcripts(
        Path.home() / ".codex" / "sessions", "my-codex-source"):
    actions = [step for step in steps if step.kind == "action"]
```

The other entry points have the same signature:

- `agy_transcript_adapter.iter_transcripts()` expects an Antigravity `brain` directory. It reads
  only each session's `.system_generated/logs/transcript.jsonl` and ignores duplicate chunk/full
  representations.
- `zcode_transcript_adapter.iter_transcripts()` expects the ZCode CLI storage root and groups
  selected records by native `sessionId` across files.

The namespace must be a stable, non-secret name for the source, such as `studio-codex`. Moving the
same source to another mount leaves session and event IDs unchanged. Reusing a namespace for a
different source defeats that separation contract.

## Event contract

`NormalizedTranscript` carries the event and alias format versions, source agent and namespace,
source-relative paths, a stable session digest, a canonical transcript digest, and the native
session ID. `NormalizedStep` is either a non-empty user message or an action with:

- the original tool name and input;
- an exact canonical alias when one has been declared, otherwise `None`;
- a contiguous action ordinal;
- stable source and native event identities; and
- the source timestamp when present.

An alias does not establish label correctness. Before these events enter a corpus, each agent needs
its own blind mapping audit and source-separated transfer evaluation.

## Failure behavior and privacy

Malformed JSON, ambiguous session identity, conflicting Agy steps, invalid tool inputs, and duplicate
action identity raise `AdapterError`. Exact duplicate Agy records are discarded idempotently. No
partial transcript is returned after an error.

Prompts and tool arguments remain private even though the repository is public. If a caller writes
normalized rows, it must place them below ignored `data/`. Only aggregate counts and hashes may be
promoted to tracked results.
