#!/usr/bin/env python3
"""Validate and score a blind, predicted-label-stratified correctness audit.

The unweighted audit score describes the deliberately rebalanced sample. Corpus
estimates use the population and allocation frozen in plan.json. Sampling-error
intervals do not include auditor/reference error or cross-operator generalization.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy as tx  # noqa: E402
from transcript_events import IDENTITY_FORMAT_VERSION, validate_namespace  # noqa: E402


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AuditError(ValueError):
    """The audit inputs do not form one complete, internally consistent run."""


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Binomial interval for a single stratum or an explicitly unweighted sample."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def load_jsonl(path: str, label_key: str | None = None,
               required: tuple[str, ...] = (),
               allow_empty: bool = False) -> dict[str, dict]:
    """Load once and fail closed on malformed, duplicate, or unknown rows."""
    rows = {}
    try:
        fh = open(path)
    except OSError as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc
    with fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditError(f"{path}:{lineno}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise AuditError(f"{path}:{lineno}: row must be an object")
            rid = row.get("id")
            if not isinstance(rid, str) or not rid:
                raise AuditError(f"{path}:{lineno}: missing non-empty id")
            if rid in rows:
                raise AuditError(f"{path}:{lineno}: duplicate id {rid}")
            missing = [field for field in required if field not in row]
            if missing:
                raise AuditError(f"{path}:{lineno}: missing fields {', '.join(missing)}")
            if label_key:
                label = row.get(label_key)
                if label not in tx.LABELS_V1:
                    raise AuditError(f"{path}:{lineno}: unknown label {label!r}")
            confidence = row.get("confidence")
            if "confidence" in required and confidence is None:
                raise AuditError(f"{path}:{lineno}: missing non-null confidence")
            if confidence is not None and confidence not in {"high", "low"}:
                raise AuditError(f"{path}:{lineno}: invalid confidence {confidence!r}")
            rows[rid] = row
    if not rows and not allow_empty:
        raise AuditError(f"{path}: no rows")
    return rows


def require_same_ids(role: str, rows: dict, expected: set[str]) -> None:
    actual = set(rows)
    if actual != expected:
        raise AuditError(
            f"{role} id set differs from sample: "
            f"{len(expected - actual)} missing, {len(actual - expected)} extra")


def load_plan(path: str, allow_legacy: bool = False) -> dict:
    try:
        with open(path) as fh:
            plan = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc
    if not isinstance(plan, dict):
        raise AuditError(f"{path}: plan must be an object")
    format_version = plan.get("audit_format_version")
    if format_version not in {2, 3}:
        if not (allow_legacy and format_version is None):
            raise AuditError(
                f"{path}: audit format is {format_version!r}, expected 2 or 3")
        plan["_loaded_format"] = "legacy-unversioned (explicitly allowed)"
    else:
        plan["_loaded_format"] = str(format_version)
    if format_version == 3:
        if plan.get("identity_format") != IDENTITY_FORMAT_VERSION:
            raise AuditError(
                f"{path}: identity format is {plan.get('identity_format')!r}, "
                f"expected {IDENTITY_FORMAT_VERSION!r}")
        try:
            validate_namespace(plan.get("source_namespace"))
        except ValueError as exc:
            raise AuditError(f"{path}: invalid source namespace: {exc}") from exc
    if plan.get("label_set_version") != tx.LABEL_SET_VERSION:
        raise AuditError(
            f"{path}: label set is {plan.get('label_set_version')!r}, "
            f"current taxonomy is {tx.LABEL_SET_VERSION!r}")
    population, allocation = plan.get("population"), plan.get("allocation")
    if not isinstance(population, dict) or not isinstance(allocation, dict) or not population:
        raise AuditError(f"{path}: population and allocation must be non-empty objects")
    if set(population) != set(allocation):
        raise AuditError(f"{path}: population and allocation strata differ")
    for label in population:
        if label not in tx.LABELS_V1:
            raise AuditError(f"{path}: unknown stratum {label!r}")
        Nh, nh = population[label], allocation[label]
        if not isinstance(Nh, int) or not isinstance(nh, int) or not (0 < nh <= Nh):
            raise AuditError(f"{path}: invalid counts for {label}: N={Nh!r}, n={nh!r}")
    if plan.get("drawn") != sum(allocation.values()):
        raise AuditError(f"{path}: drawn does not equal the allocation total")
    return plan


def score_reference(sorter: dict, reference: dict) -> tuple[dict, list[dict]]:
    per = collections.defaultdict(lambda: [0, 0])
    confusion = collections.Counter()
    low = 0
    for rid, sorted_row in sorter.items():
        gold, got = reference[rid]["label"], sorted_row["sorter_label"]
        per[got][1] += 1
        if gold == got:
            per[got][0] += 1
        else:
            confusion[(got, gold)] += 1
        low += reference[rid].get("confidence") == "low"
    n = sum(v[1] for v in per.values())
    k = sum(v[0] for v in per.values())
    result = {
        "n": n,
        "agree": k,
        "sample_agreement": round(k / n, 4),
        "low_confidence_rows": low,
        "per_label": {
            label: {
                "n": values[1],
                "agree": values[0],
                "precision": round(values[0] / values[1], 4),
                "wilson_ci95": [round(x, 4) for x in wilson(values[0], values[1])],
            }
            for label, values in sorted(per.items())
        },
    }
    full_confusion = [
        {"sorter": got, "reference": gold, "n": count}
        for (got, gold), count in sorted(
            confusion.items(), key=lambda item: (-item[1], item[0]))
    ]
    return result, full_confusion


def stratified_estimate(per_label: dict, population: dict,
                        labels: set[str] | None = None) -> dict:
    """SRS-without-replacement estimate, with sampling-error-only normal CI."""
    labels = set(population) if labels is None else set(labels) & set(population)
    population_n = sum(population[label] for label in labels)
    if not population_n:
        raise AuditError("cannot estimate an empty group of strata")
    estimate = variance = 0.0
    contributions = {}
    for label in sorted(labels):
        if label not in per_label:
            raise AuditError(f"sample has no rows for population stratum {label!r}")
        Nh = population[label]
        nh = per_label[label]["n"]
        if nh > Nh:
            raise AuditError(f"sample for {label} exceeds its population")
        ph = per_label[label]["agree"] / nh
        weight = Nh / population_n
        estimate += weight * ph
        contributions[label] = weight * (1 - ph)
        if nh == 1 and Nh > 1:
            raise AuditError(f"cannot estimate variance for {label}: n=1, N={Nh}")
        if nh > 1:
            variance += (weight ** 2) * (1 - nh / Nh) * ph * (1 - ph) / (nh - 1)
    se = math.sqrt(variance)
    return {
        "population_n": population_n,
        "estimate": round(estimate, 6),
        "standard_error": round(se, 6),
        "ci95": [round(max(0.0, estimate - 1.96 * se), 6),
                 round(min(1.0, estimate + 1.96 * se), 6)],
        "method": "stratified SRSWOR normal approximation; sampling error only",
        "limitations": "Does not include reference-label error or cross-operator generalization; "
                       "small all-right/all-wrong strata contribute zero estimated variance.",
        "error_contribution": {
            label: round(value, 6)
            for label, value in sorted(contributions.items(),
                                       key=lambda item: (-item[1], item[0]))
        },
    }


def adjudicate(sorter: dict, first: dict, second: dict,
               adjudicator: dict) -> tuple[dict, int]:
    disagreements = {
        rid for rid in sorter if first[rid]["label"] != second[rid]["label"]
    }
    actual = set(adjudicator)
    if actual != disagreements:
        raise AuditError(
            "adjudicator id set differs from auditor disagreements: "
            f"{len(disagreements - actual)} missing, {len(actual - disagreements)} extra")
    gold = {}
    for rid in sorter:
        label = (first[rid]["label"] if rid not in disagreements
                 else adjudicator[rid]["label"])
        gold[rid] = {"id": rid, "label": label}
    return gold, len(disagreements)


def inter_rater(sorter: dict, first: dict, second: dict,
                population: dict) -> dict:
    per = collections.defaultdict(lambda: [0, 0])
    for rid, sorted_row in sorter.items():
        label = sorted_row["sorter_label"]
        per[label][1] += 1
        per[label][0] += first[rid]["label"] == second[rid]["label"]
    by_stratum = {
        label: {"n": values[1], "agree": values[0]}
        for label, values in per.items()
    }
    n = len(sorter)
    same = sum(values[0] for values in per.values())
    return {
        "n": n,
        "agree": same,
        "sample_agreement": round(same / n, 4),
        "population_weighted": stratified_estimate(by_stratum, population),
    }


def subset_summary(sorter: dict, gold: dict, ids: set[str]) -> dict:
    n = len(ids)
    k = sum(sorter[rid]["sorter_label"] == gold[rid]["label"] for rid in ids)
    return {
        "n": n,
        "correct": k,
        "agreement": round(k / n, 4) if n else None,
    }


def optional_stratified_estimate(per_label: dict, population: dict,
                                 labels: set[str]) -> dict | None:
    """Return no estimate when the requested subset has no population strata."""
    labels = set(labels) & set(population)
    return stratified_estimate(per_label, population, labels) if labels else None


def write_json(path: str, value: dict) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(value, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/audit")
    ap.add_argument("--auditors", default="claude,agy")
    ap.add_argument("--adjudicator",
                    help="JSONL basename or path containing exactly the disagreement IDs")
    ap.add_argument("--allow-legacy-plan", action="store_true",
                    help="explicitly accept the frozen pre-v2 plan with no format version")
    ap.add_argument("--out", help="write validated raw auditor aggregates here")
    ap.add_argument("--adjudicated-out", help="write the deterministic adjudicated aggregate here")
    args = ap.parse_args(argv)

    try:
        plan_path = os.path.join(args.dir, "plan.json")
        sample_path = os.path.join(args.dir, "sample.jsonl")
        sorter_path = os.path.join(args.dir, "sorter.jsonl")
        plan = load_plan(plan_path, allow_legacy=args.allow_legacy_plan)
        sample = load_jsonl(sample_path,
                            required=("tool", "text"))
        sorter_required = ["sorter_label", "session"]
        if plan.get("audit_format_version") == 3:
            sorter_required.extend((
                "identity_format", "source_namespace", "source_relpath",
                "transcript_sha256", "source_event_id", "source_event_ordinal"))
        sorter = load_jsonl(sorter_path, "sorter_label",
                            required=tuple(sorter_required))
        sample_ids = set(sample)
        require_same_ids("sorter", sorter, sample_ids)
        if plan.get("audit_format_version") == 3:
            event_ids = [row["source_event_id"] for row in sorter.values()]
            if len(event_ids) != len(set(event_ids)):
                raise AuditError("sorter contains duplicate source_event_id values")
            for rid, row in sorter.items():
                if row["identity_format"] != IDENTITY_FORMAT_VERSION:
                    raise AuditError(f"sorter row {rid} has wrong identity_format")
                if row["source_namespace"] != plan["source_namespace"]:
                    raise AuditError(f"sorter row {rid} has wrong source_namespace")
                for field in ("session", "transcript_sha256", "source_event_id"):
                    if (not isinstance(row[field], str) or
                            not _SHA256_RE.fullmatch(row[field])):
                        raise AuditError(f"sorter row {rid} has invalid {field}")
                ordinal = row["source_event_ordinal"]
                if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
                    raise AuditError(f"sorter row {rid} has invalid source_event_ordinal")
        if len(sorter) != plan["drawn"]:
            raise AuditError("sorter row count differs from plan.drawn")
        observed = collections.Counter(row["sorter_label"] for row in sorter.values())
        if dict(observed) != plan["allocation"]:
            raise AuditError("sorter strata do not match plan.allocation")

        names = [name.strip() for name in args.auditors.split(",") if name.strip()]
        if not names or len(names) != len(set(names)):
            raise AuditError("--auditors must name one or more distinct files")
        auditors = {}
        auditor_paths = {
            name: name if os.path.sep in name else os.path.join(args.dir, f"{name}.jsonl")
            for name in names
        }
        resolved_auditors = {}
        for name, path in auditor_paths.items():
            resolved = os.path.realpath(path)
            if resolved in resolved_auditors:
                raise AuditError(
                    f"auditors {resolved_auditors[resolved]!r} and {name!r} "
                    "resolve to the same file")
            resolved_auditors[resolved] = name
            auditors[name] = load_jsonl(path, "label", required=("label", "confidence"))
            require_same_ids(f"auditor {name}", auditors[name], sample_ids)

        adjudicator_path = None
        if args.adjudicator:
            adjudicator_path = (
                args.adjudicator if os.path.sep in args.adjudicator
                else os.path.join(args.dir, f"{args.adjudicator}.jsonl"))
        input_paths = {
            os.path.realpath(path)
            for path in (plan_path, sample_path, sorter_path, *auditor_paths.values())
        }
        if adjudicator_path:
            resolved_adjudicator = os.path.realpath(adjudicator_path)
            if resolved_adjudicator in resolved_auditors:
                raise AuditError("adjudicator and auditor must resolve to different files")
            input_paths.add(resolved_adjudicator)
        output_paths = [
            os.path.realpath(path)
            for path in (args.out, args.adjudicated_out) if path
        ]
        if len(output_paths) != len(set(output_paths)):
            raise AuditError("--out and --adjudicated-out must be different files")
        if any(path in input_paths for path in output_paths):
            raise AuditError("output files must not overwrite audit inputs")

        report = {
            "measurement_contract": {
                "sampling": "predicted-label stratified, unequal allocation",
                "plan_format": plan["_loaded_format"],
                "sample_statistics": "unweighted agreement on the audited rows",
                "population_statistics": "weighted by plan.population; sampling error only",
            },
            "auditors": {},
            "disagreement": None,
            "confusion": {},
        }
        for name, answers in auditors.items():
            scored, confusion = score_reference(sorter, answers)
            scored["population_weighted"] = stratified_estimate(
                scored["per_label"], plan["population"])
            report["auditors"][name] = scored
            report["confusion"][name] = confusion
            print(f"auditor {name}: {scored['agree']}/{scored['n']} = "
                  f"{100 * scored['agree'] / scored['n']:.1f}% sample agreement; "
                  f"{100 * scored['population_weighted']['estimate']:.1f}% weighted")

        if len(auditors) == 2:
            first, second = auditors[names[0]], auditors[names[1]]
            report["disagreement"] = inter_rater(
                sorter, first, second, plan["population"])

        if bool(args.adjudicator) != bool(args.adjudicated_out):
            raise AuditError("--adjudicator and --adjudicated-out must be used together")
        if args.adjudicator:
            if len(auditors) != 2:
                raise AuditError("adjudication requires exactly two auditors")
            judge = load_jsonl(adjudicator_path, "label", required=("label", "confidence"),
                               allow_empty=True)
            gold, disagreement_n = adjudicate(
                sorter, auditors[names[0]], auditors[names[1]], judge)
            scored, confusion = score_reference(sorter, gold)
            all_ids = set(sorter)
            governance_labels = {
                label for label in plan["population"]
                if tx.LABELS_V1[label]["tier"] == tx.GOVERNANCE
            }
            governance_ids = {
                rid for rid, row in sorter.items()
                if row["sorter_label"] in governance_labels
            }
            mapped_labels = set(plan["population"]) - {"unmapped"}
            adjudicated = {
                "measurement_contract": report["measurement_contract"],
                "adjudicated": subset_summary(sorter, gold, all_ids),
                "governance": subset_summary(sorter, gold, governance_ids),
                "non_governance": subset_summary(sorter, gold, all_ids - governance_ids),
                "population_weighted": {
                    "all": stratified_estimate(scored["per_label"], plan["population"]),
                    "governance": optional_stratified_estimate(
                        scored["per_label"], plan["population"], governance_labels),
                    "non_governance": optional_stratified_estimate(
                        scored["per_label"], plan["population"],
                        set(plan["population"]) - governance_labels),
                    "assigned_only": optional_stratified_estimate(
                        scored["per_label"], plan["population"], mapped_labels),
                },
                "per_label": scored["per_label"],
                "confusion": confusion,
                "reference": {
                    "auditors": names,
                    "agreed_without_adjudication": len(sorter) - disagreement_n,
                    "disagreements_adjudicated": disagreement_n,
                    "limitations": "Agreement with this adjudicated reference is not absolute truth; "
                                   "shared auditor errors were not independently measured.",
                },
            }
            write_json(args.adjudicated_out, adjudicated)
            population = adjudicated["population_weighted"]["all"]
            print(f"adjudicated: {adjudicated['adjudicated']['correct']}/{len(sorter)} = "
                  f"{100 * adjudicated['adjudicated']['correct'] / len(sorter):.1f}% "
                  "sample agreement; "
                  f"{100 * population['estimate']:.1f}% weighted "
                  f"(95% sampling CI {100 * population['ci95'][0]:.1f}-"
                  f"{100 * population['ci95'][1]:.1f}%)")

        if args.out:
            write_json(args.out, report)
        return 0
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
