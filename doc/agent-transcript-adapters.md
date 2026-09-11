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

## Mechanical label-coverage audit

Run `audit_agent_label_coverage.py` separately for each source. It applies only the adapter's exact
tool alias and then calls the unchanged `v1.0.0` taxonomy mapper:

```bash
python3 utils/corpus/audit_agent_label_coverage.py \
  --source zcode --root /private/source/root --namespace studio-zcode \
  --out data/agent-audit/zcode.json
```

Valid source names are `codex`, `agy_desktop`, `agy_cli`, and `zcode`. The output contains aggregate
counts, tool and label distributions, input field-name shapes, format versions, and a source-state
digest. It never writes argument values, prompt text, source paths, or native identities. A source
with zero actions, duplicate normalized sessions, incomplete accounting, or a source-wide ZCode
parse error exits nonzero rather than producing a partial passing result.

Mapping coverage is only a schema-compatibility measurement. It does not show that the assigned
labels are semantically right; that requires a separate blind human review before training use.

## Blind semantic-label sample

After a source clears the mechanical gate, draw its semantic-review sample separately. The command
reuses the normalized adapter, unchanged taxonomy, and exact stratified allocator. It writes private
tool arguments to `sample.jsonl`, holds predictions back in `sorter.jsonl`, and records aggregate
allocation metadata in `plan.json`:

```bash
python3 utils/corpus/sample_agent_label_audit.py \
  --source zcode --root /private/source/root --namespace studio-zcode \
  --target 200 --floor 4 --seed 3701 \
  --out-dir data/agent-label-review/zcode-v1
```

The output directory must be new and below a directory named `data`; all three files stay private
until review is complete. Only aggregate plan or scored-result fields may be promoted after a
privacy scan. The sample contains no sorter labels, and the sorter file contains no tool arguments.

## Failure behavior and privacy

Malformed JSON, ambiguous session identity, conflicting Agy steps, invalid tool inputs, and duplicate
action identity raise `AdapterError`. Exact duplicate Agy records are discarded idempotently. No
partial transcript is returned after an error.

Prompts and tool arguments remain private even though the repository is public. If a caller writes
normalized rows, it must place them below ignored `data/`. Only aggregate counts and hashes may be
promoted to tracked results.
