"""Synthetic-only contract checks; these cannot establish app rendering."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

PATH = Path(__file__).resolve().parents[1] / "utils/hooks/codex_connection_probe.py"
spec = importlib.util.spec_from_file_location("codex_connection_probe", PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_stop_is_warning_only():
    result = probe.response({"hook_event_name": "Stop"})
    assert result == {"systemMessage": probe.MESSAGE}
    assert "synthetic" in result["systemMessage"]
    assert probe.response({"hook_event_name": "Stop", "stop_hook_active": True}) == {}
    assert probe.response({"hook_event_name": "Stop", "agent_id": "child"}) == {}


def test_prompt_is_exact_and_not_echoed():
    assert probe.response({"hook_event_name": "UserPromptSubmit", "prompt": probe.PROMPT})
    assert probe.response({"hook_event_name": "UserPromptSubmit", "prompt": "private text"}) == {}
    assert probe.response({"hook_event_name": "UserPromptSubmit", "prompt": probe.PROMPT + "extra"}) == {}


def test_bad_or_large_input_is_nonblocking():
    for raw in (b"bad json", b"[]", b"x" * 65537):
        run = subprocess.run([sys.executable, str(PATH)], input=raw, capture_output=True, timeout=2)
        assert run.returncode == 0
        assert json.loads(run.stdout) == {}
        assert run.stderr == b""
