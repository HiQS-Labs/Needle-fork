# Native connection probe checkpoint — not a predictor

Source: `utils/hooks/codex_connection_probe.py`; tests:
`tests/test_codex_connection_probe.py`.

- Focused tests: 3 passed in 0.11s.
- Full non-slow suite: 513 passed, 6 skipped, 11 deselected in 16.09s.
- In-memory negative control replaced the warning response with a continuation
  decision: warning-only assertion failed. Restored original response: passed.
- Local VS Code extension inventory: `openai.chatgpt-26.908.40401-darwin-arm64`.
  Its bundled webview handles `hook/completed`; that is source evidence, not proof
  that this window displays our warning.
- Agy Gemini 3.1 Pro High approved the probe review; relay exit 8 because its
  verdict vocabulary did not match the shipped validator. Review retained under
  `relay-system/2026-09-13/needle-63-probe-qa.md`.
- Local hook configuration created; no existing file replaced, no trust bypass.
  Runtime trust/loading and three-turn visible display checks remain unverified.
- No prompt data retained, prediction generated, model trained, or skill installed.

Next: observe one synthetic warning in the app, then complete the planned
three-turn and disable/re-enable checks. Absence of the warning is not success.
