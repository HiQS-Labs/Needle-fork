#!/usr/bin/env python3
"""#63 native Codex display probe. No prediction, files, network or training."""
import json
import sys

MESSAGE = (
    "Needle CONNECTION TEST — synthetic choices, not predictions: "
    "1. Read code | 2. Run tests | 3. Edit code. No feedback is being saved."
)
PROMPT = "Needle connection test\n#needle want 2"


def response(payload):
    if not isinstance(payload, dict) or payload.get("agent_id"):
        return {}
    event = payload.get("hook_event_name")
    if event == "Stop" and not payload.get("stop_hook_active"):
        return {"systemMessage": MESSAGE}
    if event == "UserPromptSubmit" and payload.get("prompt") == PROMPT:
        return {"systemMessage": "Needle CONNECTION TEST — exact synthetic prompt received unchanged."}
    return {}


def main():
    # Bound input; do not read transcript_path or echo arbitrary user content.
    try:
        raw = sys.stdin.buffer.read(65537)
        payload = json.loads(raw) if len(raw) <= 65536 else None
        result = response(payload)
    except (ValueError, OSError):
        result = {}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
