# Optional fill-in-later feedback

Use the [blank CSV with fictional examples](next-action-feedback-template.csv). A private working
copy is provided under ignored `data/next-action-feedback.csv`; fill only its `your_answer` column
in Numbers, Excel, or a text editor. One case is enough to start; duplicate a case group if useful.
Do not enter real context in the tracked template or commit completed responses.

For a behavior-prediction example, the useful minimum is task, completed prior actions and the
actual next action, recorded after it occurred. The latest observation makes it useful for a
context-aware model. Plain English is fine; no taxonomy memorization or live A/B interaction.
Unknown answers stay blank. Do not guess, reconstruct unavailable outputs, or include later
information in the pre-action context. Optional preferred action/reason are separate feedback
about assistance, not replacement behavior labels. Retrospective memories may be imperfect and
must be labeled as user-reported, not verified tool traces.

Examples are illustrations only. Blank forms and example cells are never training/evaluation rows.
No response is collected until the operator fills it in and asks us to use it. This form does not
restart the timed/manual #49 trial or alter #51's completed result. It is optional; automatic
offline work can continue without it under a separately scoped experiment.

## Model respondents

Fable or another model can answer the same context questions as a proxy, audit ambiguous mappings,
or propose synthetic examples. Record model identity and keep those answers separate from human
responses and observed next-action labels. Withhold the future action/result from a model asked
to predict it. Do not let model opinions grade their own generated data as human ground truth.
For a real prediction benchmark, compare with the next action already recorded in trajectories;
model votes cannot establish the operator's preferences or product usefulness.
