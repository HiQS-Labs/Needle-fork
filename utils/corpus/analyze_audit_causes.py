#!/usr/bin/env python3
"""Validate and aggregate row-level causes for a scored label audit.

Raw commands and row-level cause judgments stay under ignored ``data/``. The
public output contains aggregates only. A stratified random sample uses its
declared weights; a constrained targeted sample reports unweighted counts.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score_audit as audit  # noqa: E402
import taxonomy as tx  # noqa: E402


CAUSES = {
    "multi_action_policy": {
        "description": "Several recognized actions share one tool call; the fixed one-label policy selected a different action than the reference.",
        "falsifier": "The reference action is not independently visible among the sorter's segment labels, or only one action is present.",
    },
    "shell_visibility": {
        "description": "A wrapper, control-flow construct, environment prefix, or heredoc shape hides the reference action from the current parser.",
        "falsifier": "The current parser exposes the reference action directly without interpreting hidden shell structure.",
    },
    "inline_semantics": {
        "description": "The specific action is performed inside inline program text while the mapper can observe only the interpreter invocation.",
        "falsifier": "The reference action is visible outside the inline program body.",
    },
    "rule_defect": {
        "description": "A direct command has an existing label, but a missing, broad, or incorrect rule maps it elsewhere.",
        "falsifier": "Applying the existing label definitions still leaves more than one defensible answer.",
    },
    "taxonomy_boundary": {
        "description": "The current label definitions overlap or omit the observed action, so they do not specify one stable answer.",
        "falsifier": "The frozen definitions already choose one label unambiguously for the row.",
    },
    "reference_uncertain": {
        "description": "The adjudicated label is not better supported than another action in the same row under the current instructions.",
        "falsifier": "A written, predeclared rule makes the adjudicated label the unique answer for this row.",
    },
}


def _path(directory: str, name: str) -> str:
    return name if os.path.sep in name else os.path.join(directory, f"{name}.jsonl")


def _trace_labels(sample_row: dict) -> list[str]:
    if sample_row["tool"] != "Bash":
        return []
    return [
        label for segment in tx.substantive_segments(sample_row["text"])
        if (label := tx.label_segment(segment)) is not None
    ]


def analyze(directory: str, auditors: tuple[str, str], adjudicator: str,
            causes_path: str, allow_legacy_plan: bool = False) -> dict:
    plan = audit.load_plan(os.path.join(directory, "plan.json"), allow_legacy_plan)
    sample = audit.load_jsonl(
        os.path.join(directory, "sample.jsonl"), required=("tool", "text"))
    sorter = audit.load_and_validate_sorter(directory, plan, set(sample))

    first = audit.load_jsonl(
        _path(directory, auditors[0]), "label", required=("label", "confidence"))
    second = audit.load_jsonl(
        _path(directory, auditors[1]), "label", required=("label", "confidence"))
    audit.require_same_ids(f"auditor {auditors[0]}", first, set(sample))
    audit.require_same_ids(f"auditor {auditors[1]}", second, set(sample))
    judge = audit.load_jsonl(
        _path(directory, adjudicator), "label", required=("label", "confidence"),
        allow_empty=True)
    reference, _ = audit.adjudicate(sorter, first, second, judge)

    expected = {
        rid for rid in sorter
        if sorter[rid]["sorter_label"] != reference[rid]["label"]
    }
    causes = audit.load_jsonl(
        causes_path,
        required=("sorter_label", "reference_label", "cause", "confidence",
                  "observed_mechanism", "falsifier"),
        allow_empty=not expected)
    actual = set(causes)
    if actual != expected:
        raise audit.AuditError(
            "cause id set differs from adjudicated errors: "
            f"{len(expected - actual)} missing, {len(actual - expected)} extra")

    is_srs = plan["_sampling_design"] == audit.SAMPLING_DESIGN
    population_n = sum(plan["population"].values())
    grouped = collections.defaultdict(lambda: {"rows": 0, "weighted": 0.0})
    sensitive = collections.defaultdict(lambda: {"rows": 0, "weighted": 0.0})
    by_stratum = collections.defaultdict(
        lambda: collections.defaultdict(lambda: {"rows": 0, "weighted": 0.0}))
    trace_summary = collections.Counter()
    feedback_causes = {"shell_visibility", "inline_semantics", "rule_defect"}
    feedback_rows = 0
    feedback_weight = 0.0

    for rid in sorted(expected):
        row = causes[rid]
        predicted = sorter[rid]["sorter_label"]
        gold = reference[rid]["label"]
        if row["sorter_label"] != predicted or row["reference_label"] != gold:
            raise audit.AuditError(f"{rid}: recorded label pair differs from adjudicated data")
        cause = row["cause"]
        if cause not in CAUSES:
            raise audit.AuditError(f"{rid}: unknown cause {cause!r}")
        if not isinstance(row["observed_mechanism"], str) or not row["observed_mechanism"].strip():
            raise audit.AuditError(f"{rid}: empty observed_mechanism")
        if not isinstance(row["falsifier"], str) or not row["falsifier"].strip():
            raise audit.AuditError(f"{rid}: empty falsifier")

        labels = _trace_labels(sample[rid])
        if sample[rid]["tool"] == "Bash":
            current, _ = tx.label_call("Bash", {"command": sample[rid]["text"]})
            if current != predicted:
                raise audit.AuditError(
                    f"{rid}: current taxonomy gives {current!r}, frozen sorter gives {predicted!r}")
        if cause == "multi_action_policy":
            if gold not in labels or len(set(labels)) < 2:
                raise audit.AuditError(
                    f"{rid}: multi_action_policy requires the reference and another segment label")

        unit = (plan["population"][predicted] /
                plan["allocation"][predicted] / population_n
                if is_srs else 1 / len(sorter))
        grouped[cause]["rows"] += 1
        grouped[cause]["weighted"] += unit
        sensitivity_cause = cause if row["confidence"] == "high" else "unresolved"
        sensitive[sensitivity_cause]["rows"] += 1
        sensitive[sensitivity_cause]["weighted"] += unit
        by_stratum[predicted][cause]["rows"] += 1
        by_stratum[predicted][cause]["weighted"] += unit
        trace_summary["reference_visible"] += gold in labels
        trace_summary["multiple_segment_labels"] += len(set(labels)) >= 2
        if first[rid]["label"] == second[rid]["label"]:
            reference_high = (
                first[rid]["confidence"] == second[rid]["confidence"] == "high")
        else:
            reference_high = judge[rid]["confidence"] == "high"
        if cause in feedback_causes and row["confidence"] == "high" and reference_high:
            feedback_rows += 1
            feedback_weight += unit

    scored, _ = audit.score_reference(sorter, reference)
    estimated_error = (1 - audit.stratified_estimate(
        scored["per_label"], plan["population"])["estimate"]
        if is_srs else len(expected) / len(sorter))
    classified_error = sum(v["weighted"] for v in grouped.values())
    if abs(estimated_error - classified_error) > 1e-6:
        raise audit.AuditError(
            "classified weights do not reproduce the adjudicated estimated error")

    contribution_key = ("population_error_contribution" if is_srs
                        else "sample_error_contribution")
    share_key = ("share_of_estimated_error" if is_srs
                 else "share_of_sample_errors")

    def render(groups):
        return {
            name: {
                "rows": values["rows"],
                contribution_key: round(values["weighted"], 6),
                share_key: (
                    round(values["weighted"] / classified_error, 6)
                    if classified_error else None),
            }
            for name, values in sorted(
                groups.items(), key=lambda item: (-item[1]["weighted"], item[0]))
        }

    return {
        "measurement_contract": {
            "source": "frozen adjudicated audit errors",
            "plan_format": plan["_loaded_format"],
            "sampling": plan["_sampling_design"],
            "classification": "one reviewer-assigned primary observed cause per error row",
            "privacy": "aggregate only; raw commands and row judgments remain under data/",
            "limitations": (
                "Cause assignment is reviewer judgment; weights estimate prevalence in the "
                "saved frame, not causal effect of a fix." if is_srs else
                "Cause assignment is reviewer judgment. The targeted draw supports sample "
                "counts only, not a population estimate or confidence interval."),
        },
        "errors": {
            "rows": len(expected),
            "sample_error_rate": round(len(expected) / len(sorter), 6),
            "population_error_estimate": (
                round(classified_error, 6) if is_srs else None),
        },
        "cause_definitions": CAUSES,
        "trace": dict(trace_summary),
        "by_cause": render(grouped),
        "low_confidence_as_unresolved": render(sensitive),
        "reviewed_correction_seed": {
            "selection": "high-confidence cause plus high-confidence adjudicated reference in shell_visibility, inline_semantics, or rule_defect",
            "rows": feedback_rows,
            contribution_key: round(feedback_weight, 6),
            share_key: (
                round(feedback_weight / classified_error, 6)
                if classified_error else None),
            "training_use": "reference label is the matched treatment target; frozen sorter label is the matched control target",
            "limitation": (
                "This is a development seed, not a holdout, and its weighted "
                "contribution is not the expected gain from training." if is_srs else
                "This is a development seed, not a holdout. Its share of this targeted "
                "sample is not a population estimate or the expected gain from training."),
        },
        "by_predicted_stratum": {
            label: render(values) for label, values in sorted(by_stratum.items())
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/audit")
    ap.add_argument("--auditors", default="claude,agy")
    ap.add_argument("--adjudicator", default="codex")
    ap.add_argument("--causes", default="data/audit/error-causes.jsonl")
    ap.add_argument("--allow-legacy-plan", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    names = tuple(name.strip() for name in args.auditors.split(",") if name.strip())
    try:
        if len(names) != 2 or len(set(names)) != 2:
            raise audit.AuditError("--auditors must name exactly two distinct files")
        inputs = {
            os.path.realpath(os.path.join(args.dir, name))
            for name in ("plan.json", "sample.jsonl", "sorter.jsonl")
        }
        inputs.update(os.path.realpath(_path(args.dir, name)) for name in (*names, args.adjudicator))
        inputs.add(os.path.realpath(args.causes))
        if os.path.realpath(args.out) in inputs:
            raise audit.AuditError("output file must not overwrite cause-analysis inputs")
        report = analyze(
            args.dir, names, args.adjudicator, args.causes, args.allow_legacy_plan)
        audit.write_json(args.out, report)
        message = f"classified {report['errors']['rows']} errors"
        population_error = report["errors"]["population_error_estimate"]
        if population_error is not None:
            message += f"; weighted population error {100 * population_error:.2f}%"
        else:
            message += (f"; targeted-sample error "
                        f"{100 * report['errors']['sample_error_rate']:.2f}%")
        print(message)
        return 0
    except (audit.AuditError, OSError, json.JSONDecodeError) as exc:
        print(f"audit cause analysis failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
