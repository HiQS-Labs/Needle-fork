"""Option-2 gate: can the engine emit an enum value that is ABSENT from the prompt text?

Option 2 collapses 44 tools into ONE declared tool whose `label` argument is an enum over
all 44 labels -- sidestepping the >=5-tool contract entirely. It is only viable if the
engine will emit an enum value that does not appear verbatim in the input.

The vendor documents argument grounding ("only values evidenced by the input") and the
binary carries `[debug] enum select: start=%d acc='%s' grounded=%zu best=%s`. If grounding
is enforced on enum literals, Option 2 is dead on arrival, because the whole point is
predicting a label the user never typed.

Conditions, same declared tool throughout:
  POSITIVE  the target label appears verbatim in the query  -> grounding satisfied
  ABSENT    no label string appears anywhere in the query   -> the real deployment case

A failure in ABSENT is only decisive if POSITIVE succeeds; otherwise the tool is simply
unusable and we have learned nothing about grounding. Reported separately for that reason.
"""
import json
import os
import sys
import warnings

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("NEEDLE_TELEMETRY", "0")
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath("."))
import needle                                                    # noqa: E402
from oracle_scoring import parse_native, OK, ABSTAIN             # noqa: E402

CACT = sys.argv[1] if len(sys.argv) > 1 else "data/spike-mlx/oracle-10k-qat.cact"
SYSTEM = ("You are the SDLC Oracle. Given the operator's request and the recent actions, "
          "choose the single best next action label.")

labels = sorted(json.load(open("oracle/labels-v1.json"))["labels"])
TOOL = [{
    "name": "next_action",
    "description": "Choose the single best next SDLC action label.",
    "parameters": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": labels,
                      "description": "The next action label."},
        },
        "required": ["label"],
    },
}]
tools = json.dumps(TOOL, separators=(",", ":"), ensure_ascii=False)

# Queries whose plainly-correct next action is `read_file`, in two grounding conditions.
CASES = [
    ("POSITIVE", "read_file",
     "[oracle-q1]\nREQUEST: open the config and show me what is in it\n"
     "RECENT: find_files\nThe next action label is read_file."),
    ("POSITIVE", "run_tests",
     "[oracle-q1]\nREQUEST: check the suite passes\nRECENT: apply_patch\n"
     "The next action label is run_tests."),
    ("ABSENT", "read_file",
     "[oracle-q1]\nREQUEST: open the config and show me what is in it\nRECENT: find_files"),
    ("ABSENT", "run_tests",
     "[oracle-q1]\nREQUEST: check the suite passes\nRECENT: apply_patch"),
    ("ABSENT", "commit_changes",
     "[oracle-q1]\nREQUEST: save this work to the repository history\nRECENT: apply_patch"),
]

print(f"  artifact {os.path.basename(CACT)}   1 declared tool, enum of {len(labels)} labels")
print(f"  {'cond':<9} {'expect':<16} {'emitted':<20} {'status':<12} args")
print("  " + "-" * 78)
rows = []
for cond, expect, query in CASES:
    eng = needle.Needle(tools=tools, system=SYSTEM, weights=CACT)
    try:
        env = eng.complete(query, max_new_tokens=64)
    except Exception as exc:                                       # noqa: BLE001
        env = {"error": repr(exc)}
    finally:
        try:
            eng.close()
        except Exception:
            pass
    calls = env.get("function_calls") or []
    args = calls[0].get("arguments") if calls else None
    emitted = (args or {}).get("label") if isinstance(args, dict) else None
    v = parse_native(env, {"next_action"})
    rows.append((cond, expect, emitted, v.status))
    print(f"  {cond:<9} {expect:<16} {str(emitted):<20} {v.status:<12} {json.dumps(args)[:40]}")

pos = [r for r in rows if r[0] == "POSITIVE"]
absent = [r for r in rows if r[0] == "ABSENT"]
pos_ok = sum(1 for _, _, e, _ in pos if e)
abs_ok = sum(1 for _, _, e, _ in absent if e)
print()
print(f"  POSITIVE (label in prompt): emitted a label in {pos_ok}/{len(pos)}")
print(f"  ABSENT   (label not in prompt): emitted a label in {abs_ok}/{len(absent)}")
print()
if pos_ok == 0:
    print("  INCONCLUSIVE: the enum tool never emits a label even when grounded.")
    print("  That is a tool-usability failure, not evidence about grounding. Option 2 unresolved.")
elif abs_ok == 0:
    print("  OPTION 2 BLOCKED: labels are emitted only when present verbatim in the input.")
    print("  Grounding is enforced on enum literals; predicting an unstated label is impossible.")
else:
    print("  OPTION 2 VIABLE on this evidence: the engine emitted a label absent from the prompt.")
    print("  Grounding does not block enum prediction. Accuracy is a separate question.")
