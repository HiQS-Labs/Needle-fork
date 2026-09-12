# Coding-core experiments

Current protocol: [context-aware next action #51](../../PROJECT/3-COMPLETED/CONTEXT-NEXT-ACTION.md).
This is offline research code, not part of the installed `needle` runtime or a serving model.

```sh
python spike/coding_core/context_probe.py --out data/context-next-action-2026-09-12
```

The frozen run completed and failed its follow-up rule; do not repeat it as an active instruction.
The command is retained for reproducibility. Any new campaign needs a separately scoped decision.
Run only after reading the protocol and passing tests. The destination must not exist. Acquisition
uses a revision-checked, byte/time-bounded HF sample; data and detailed receipts stay ignored.
Source: [nebius/SWE-rebench-openhands-trajectories](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories),
CC BY 4.0, Nebius / Trofimova et al., 2025. Source contains agent-produced trajectories on real
issues, not human usefulness labels. No transcript code is executed.

Selective provenance (not whole-branch integration): `prepare_openhands.py`, `labels.json` and
`tests/test_coding_core.py` originate in #42 at `18274fc`; `baselines.py` and
`tests/test_private_transitions.py` in #48 at `e05b4d6`. The q1 converter defaults and baseline
logic are preserved. #51 adds opt-in context extraction and the CPU-only probe; it imports no
MLX model/training/export stack. `utils/corpus/taxonomy.py` remains the canonical mapping source.

Historical private evaluation mode requires its original trusted private manifest and is not
part of #51's run. Do not rerun it or infer its gates passed. PR #43 is held and unrelated.
