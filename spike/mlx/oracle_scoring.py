"""Shared, format-specific parsing for Oracle evaluation -- with negative controls.

Two runtimes emit two different formats and MUST NOT share one parser:

  native SDK  -> an envelope dict: {"type": "call"|"respond", "function_calls": [...]}
  MLX greedy  -> render_example()'s text format (finetune.py:194):
                 <think>\n{reasoning}\n</think>\n<tool_call>[{"name":...}]</tool_call><|im_end|>

Requiring the native envelope of an MLX generation would reject every valid generation
(GPT-6 Astra, #12). Each runtime is parsed by its own reader; both normalise to one
Verdict so the arms are comparable.

The prior scorer regex-searched the whole output for `"name"`, so a label mentioned only
inside <think>, or a truncated JSON tail, scored as a correct answer. Those are now
distinct statuses and are pinned by negative controls in self_test().

Run `python spike/mlx/oracle_scoring.py` -- the self-test is the runnable check.
"""
import json
import re

OK = "ok"                      # exactly one declared label, well-formed
ABSTAIN = "abstain"            # no tool call at all (legitimate; not a parse failure)
MALFORMED = "malformed"        # a call was attempted but the JSON is unparseable/truncated
MULTIPLE = "multiple_calls"    # more than one call -- the task demands exactly one
UNDECLARED = "undeclared"      # a call naming something outside the declared label set
ERROR = "error"                # runtime raised

_BLOCK = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
_OPEN = re.compile(r"<tool_call>")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class Verdict:
    __slots__ = ("pred", "status", "raw")

    def __init__(self, pred, status, raw=""):
        self.pred, self.status, self.raw = pred, status, raw

    @property
    def answered(self):
        return self.status == OK

    def __repr__(self):
        return f"Verdict({self.pred!r}, {self.status})"


def _finish(calls, labels, raw):
    if not calls:
        return Verdict(None, ABSTAIN, raw)
    if len(calls) > 1:
        return Verdict(None, MULTIPLE, raw)
    call = calls[0]
    if not isinstance(call, dict):
        return Verdict(None, MALFORMED, raw)
    name = call.get("name")
    if not isinstance(name, str) or not name:
        return Verdict(None, MALFORMED, raw)
    # This scorer is for the parameterless Oracle labels, not arbitrary SDK tools.
    # Omitted arguments are permitted by the existing training/native formats.
    if "arguments" in call and call["arguments"] != {}:
        return Verdict(None, MALFORMED, raw)
    if name not in labels:
        return Verdict(name, UNDECLARED, raw)
    return Verdict(name, OK, raw)


def parse_native(envelope, labels):
    """Native SDK envelope -> Verdict."""
    if not isinstance(envelope, dict):
        return Verdict(None, MALFORMED, repr(envelope))
    raw = json.dumps(envelope)
    calls = envelope.get("function_calls")
    if calls is None:
        calls = []
    if not isinstance(calls, list):
        return Verdict(None, MALFORMED, raw)
    # `type` is advisory: an envelope may say "call" yet carry none. The calls decide.
    return _finish(calls, labels, raw)


def parse_mlx_text(text, labels):
    """render_example()-format generation -> Verdict.

    A <tool_call> that is opened but never closed is TRUNCATED, not an abstention --
    the model tried to answer and ran out of budget. That is a defect to count, not a
    silent zero, and it is exactly what the old regex scored as a correct answer.
    """
    raw = text or ""
    if not isinstance(raw, str):
        return Verdict(None, MALFORMED, repr(raw))
    blocks = list(_BLOCK.finditer(raw))
    if len(_OPEN.findall(raw)) != raw.count("</tool_call>"):
        return Verdict(None, MALFORMED, raw)
    if len(blocks) > 1:
        return Verdict(None, MULTIPLE, raw)
    m = blocks[0] if blocks else None
    if not m:
        if _OPEN.search(text or ""):
            return Verdict(None, MALFORMED, raw)   # opened, never closed => truncated
        return Verdict(None, ABSTAIN, raw)
    body = m.group(1).strip()
    try:
        calls = json.loads(body, object_pairs_hook=_unique_object)
    except (ValueError, TypeError):
        return Verdict(None, MALFORMED, raw)
    if isinstance(calls, dict):
        calls = [calls]
    if not isinstance(calls, list):
        return Verdict(None, MALFORMED, raw)
    return _finish(calls, labels, raw)


def self_test():
    L = {"run_script", "read_file", "search_code"}
    T = "<tool_call>"
    cases = [
        # (parser, payload, expected_status, expected_pred, why)
        (parse_mlx_text, f"<think>\nLAST: a -> run_script\n</think>\n{T}[{{\"name\":\"run_script\"}}]</tool_call><|im_end|>", OK, "run_script", "the happy path"),
        (parse_mlx_text, "<think>\nLAST: a -> run_script\n</think>", ABSTAIN, None, "NEGATIVE CONTROL: label named only inside <think> -- old regex scored this correct"),
        (parse_mlx_text, f"{T}[{{\"name\":\"run_script\"", MALFORMED, None, "NEGATIVE CONTROL: truncated JSON, block never closed -- old regex scored this correct"),
        (parse_mlx_text, f"{T}[{{\"name\":\"run_script\"}},{{\"name\":\"read_file\"}}]</tool_call>", MULTIPLE, None, "NEGATIVE CONTROL: two calls, task demands one"),
        (parse_mlx_text, f"{T}[{{\"name\":\"not_a_label\"}}]</tool_call>", UNDECLARED, "not_a_label", "NEGATIVE CONTROL: undeclared label"),
        (parse_mlx_text, f"{T}[not json]</tool_call>", MALFORMED, None, "NEGATIVE CONTROL: unparseable body"),
        (parse_mlx_text, f"{T}[]</tool_call>", ABSTAIN, None, "empty call list is a real abstention"),
        (parse_mlx_text, "", ABSTAIN, None, "empty generation"),
        (parse_native, {"type": "call", "function_calls": [{"name": "read_file"}]}, OK, "read_file", "native happy path"),
        (parse_native, {"type": "respond", "function_calls": []}, ABSTAIN, None, "native abstention"),
        (parse_native, {"type": "call", "function_calls": []}, ABSTAIN, None, "NEGATIVE CONTROL: says 'call' but carries none -- calls decide, not `type`"),
        (parse_native, {"type": "call", "function_calls": [{"name": "a"}, {"name": "b"}]}, MULTIPLE, None, "native multiple calls"),
        (parse_native, {"type": "call", "function_calls": [{"name": "nope"}]}, UNDECLARED, "nope", "native undeclared label"),
        (parse_native, {"type": "call", "function_calls": [{"noname": 1}]}, MALFORMED, None, "native call without a name"),
    ]
    bad = 0
    for fn, payload, want_status, want_pred, why in cases:
        v = fn(payload, L)
        ok = (v.status == want_status and v.pred == want_pred)
        if not ok:
            bad += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {why}\n         got {v.status}/{v.pred!r} want {want_status}/{want_pred!r}")
    print(f"\n  {len(cases)-bad}/{len(cases)} passed")
    if bad:
        raise SystemExit(f"{bad} scoring case(s) FAILED -- do not score anything with this parser")
    # The point of the negative controls, stated as an assertion:
    assert parse_mlx_text("<think>LAST: x -> run_script</think>", L).pred is None, \
        "a think-only mention must NOT yield a prediction"
    print("  negative controls hold: think-only and truncated output cannot score as correct")


if __name__ == "__main__":
    self_test()
