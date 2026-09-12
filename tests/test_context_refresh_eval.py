import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike" / "coding_core"))
import context_refresh_eval as ev
import context_refresh as refresh
import prepare_openhands as prep


@pytest.mark.parametrize("rows", [[], [{"case_id": "a", "predicted_action": "read"}] * 2,
    [{"case_id": "a", "predicted_action": "fake"}, {"case_id": "b", "predicted_action": "read"}],
    [{"case_id": "wrong", "predicted_action": "read"}, {"case_id": "b", "predicted_action": "read"}]])
def test_malformed_predictions_rejected(rows):
    with pytest.raises(ValueError):
        ev.predictions({"predictions": rows}, ["a", "b"])


def test_request_has_no_executable_surface_and_budget_can_fail():
    body = ev.request_body("inert source")
    assert body["messages"] == [{"role": "user", "content": "inert source"}]
    assert not {"tools", "functions", "plugins", "models"} & set(body)
    assert body["max_tokens"] == 4096 and body["temperature"] == 0
    assert body["reasoning"] == {"enabled": True, "effort": "low"}
    model = {"pricing": {"prompt": "0.000002", "completion": "0.000006"}}
    assert ev.budget({"q2": "x"}, model)["total_with_one_retry_usd"] < 1
    with pytest.raises(ValueError, match="ceiling"):
        ev.budget({"q2": "x" * 1000000}, model)
    with pytest.raises(ValueError, match="prices"):
        ev.budget({"q2": "x"}, {"pricing": {"prompt": "nan", "completion": "0.1"}})


def scoring_fixture(tmp_path):
    data, out = tmp_path / "data", tmp_path / "out"
    data.mkdir(); out.mkdir()
    packets = [dict(case_id=f"case-{i:02d}", task="task", observation=str(i), history=["read"])
               for i in range(30)]
    rows = [dict(q2=dict(issue=str(i), task="task", observation=str(i), history=["read"], target="edit"))
            for i in range(30)]
    refresh.write_json(data / "answer-key.json", rows)
    refresh.write_json(data / "baseline-predictions.json", [dict.fromkeys(
        ("majority", "repeat_last", "markov_1", "phase_backoff"), "read") for _ in rows])
    for arm in refresh.ARMS:
        refresh.write_json(data / (arm + "-quiz.json"), packets)
        (data / (arm + "-prompt.txt")).write_text("inert " + arm)
    refresh.write_json(data / "manifest.json", dict(format="coding-core-q3-paired-v1", quiz_cases=30,
        hashes={p.name: prep.digest(p) for p in data.iterdir()}))
    refresh.write_json(out / "preflight.json", dict(input_manifest_sha256=prep.digest(data / "manifest.json")))
    for arm in refresh.ARMS:
        predicted = [{"case_id": p["case_id"], "predicted_action": "edit" if arm == "q3" else "read"}
                     for p in packets]
        raw = dict(model=refresh.MODEL, choices=[dict(message=dict(content=json.dumps(dict(predictions=predicted))))])
        refresh.write_json(out / (arm + "-response.json"), raw)
        refresh.write_json(out / (arm + "-request.json"), ev.request_body("inert " + arm))
        refresh.write_json(out / (arm + "-locked.json"), dict(predictions=predicted, elapsed_seconds=1,
            response_sha256=prep.digest(out / (arm + "-response.json")),
            request_sha256=prep.digest(out / (arm + "-request.json"))))
    return data, out


def test_real_scorer_red_controls_and_replay(tmp_path):
    data, out = scoring_fixture(tmp_path)
    result = ev.score(data, out)
    assert result["metrics"]["q3"]["correct"] == 30
    assert result["metrics"]["q2"]["correct"] == 0
    assert result["exploratory_followup_signal"] is True
    assert ev.score(data, out) == result
    path = out / "q3-locked.json"
    lock = ev.read(path)
    lock["predictions"][0]["predicted_action"] = "read"
    path.write_text(json.dumps(lock))
    with pytest.raises(ValueError, match="differ from raw"):
        ev.score(data, out)
    (data / "q3-prompt.txt").write_text("same-length changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        ev.score(data, out)


def test_wrong_predictions_fail_the_followup_rule(tmp_path):
    data, out = scoring_fixture(tmp_path)
    path = out / "q3-response.json"
    raw = ev.read(path)
    bad = {"predictions": [{"case_id": f"case-{i:02d}", "predicted_action": "read"} for i in range(30)]}
    raw["choices"][0]["message"]["content"] = json.dumps(bad)
    path.write_text(json.dumps(raw))
    lock_path = out / "q3-locked.json"
    lock = ev.read(lock_path)
    lock.update(predictions=bad["predictions"], response_sha256=prep.digest(path))
    lock_path.write_text(json.dumps(lock))
    result = ev.score(data, out)
    assert result["metrics"]["q3"]["accuracy_pct"] == 0
    assert result["exploratory_followup_signal"] is False
