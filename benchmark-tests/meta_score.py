#!/usr/bin/env python3
"""meta_score.py — compute TB pass^4, GPQA accuracy, and the geometric-mean meta grade.

Usage:
  python3 meta_score.py results.db R001

Reads per-trial tables, writes tb_aggregates / gpqa_aggregates / meta_grades,
and prints a summary block. Assumes SQLite schema from schema.sql.
"""
import sqlite3
import sys
import math
from pathlib import Path
from statistics import median
from datetime import datetime, timezone


def tb_pass_hat_k(rows, k=4):
    """pass^k = fraction of tasks where ALL k attempts passed (reliability metric).

    Complements trial-level accuracy: accuracy rewards lucky single passes,
    pass^k penalizes flakiness, which matters for agent work.
    """
    by_task = {}
    for task_id, resolved in rows:
        by_task.setdefault(task_id, []).append(resolved)
    if not isinstance(k, int) or k < 1 or not by_task or any(len(v) != k for v in by_task.values()):
        raise ValueError("every task must have exactly k valid attempts")
    if any(a not in (0, 1) for v in by_task.values() for a in v):
        raise ValueError("resolved must be 0 or 1")
    return sum(all(v) for v in by_task.values()) / len(by_task)


def validate_round(conn, round_id):
    """Reject partial, unpaired or duplicate input before writing any aggregate.

    This checks observed item sets, not completeness against a frozen manifest.
    """
    if not conn.execute("SELECT 1 FROM rounds WHERE round_id=?", (round_id,)).fetchone():
        raise ValueError("unknown round")
    tb = conn.execute("SELECT * FROM tb_trials WHERE round_id=?", (round_id,)).fetchall()
    gpqa = conn.execute("""SELECT t.*,q.question_text FROM gpqa_trials t
        LEFT JOIN gpqa_questions q USING(question_id) WHERE round_id=?""", (round_id,)).fetchall()
    models = sorted({r["model_id"] for r in tb})
    if not models or set(models) != {r["model_id"] for r in gpqa}:
        raise ValueError("both benchmarks require the same nonempty model cohort")
    registry = {r[0] for r in conn.execute("SELECT model_id FROM models")}
    if not set(models).issubset(registry):
        raise ValueError("unregistered model")
    common_tasks = common_questions = None
    for model in models:
        trials = [r for r in tb if r["model_id"] == model]
        if any(r["resolved"] not in (0, 1) or r["is_infra_fail"] not in (0, 1)
               or r["attempt"] not in (1, 2, 3, 4) for r in trials):
            raise ValueError("invalid TB outcome, infra flag or attempt")
        tasks = {r["task_id"] for r in trials}
        valid = [r for r in trials if not r["is_infra_fail"]]
        slots = [(r["task_id"], r["attempt"]) for r in valid]
        expected = {(task, attempt) for task in tasks for attempt in range(1, 5)}
        if len(slots) != len(set(slots)) or set(slots) != expected:
            raise ValueError("TB requires one valid result per task/attempt slot; rerun infra failures")
        questions = [r for r in gpqa if r["model_id"] == model]
        ids = {r["question_id"] for r in questions}
        if len(ids) != len(questions) or any(
                r["attempt"] != 1 or r["correct"] not in (0, 1)
                or r["is_no_answer"] not in (0, 1) or r["question_text"] is None
                or (r["correct"] and r["is_no_answer"]) for r in questions):
            raise ValueError("GPQA requires one valid outcome per registered question")
        if common_tasks is not None and (tasks != common_tasks or ids != common_questions):
            raise ValueError("models must use identical benchmark item sets")
        common_tasks, common_questions = tasks, ids
    return models


def main(db_path, round_id):
    # A typo must not create a new empty database.
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            models = validate_round(conn, round_id)
            score_round(conn, round_id, models)
    finally:
        conn.close()


def score_round(conn, round_id, models):
    now = datetime.now(timezone.utc).isoformat()
    # Aggregates are replaceable projections; removed cohort members must not linger.
    for table in ("tb_aggregates", "gpqa_aggregates", "meta_grades"):
        conn.execute(f"DELETE FROM {table} WHERE round_id=?", (round_id,))

    summary = []
    tb_scores, gpqa_scores = {}, {}

    for model_id in models:
        # -- Terminal-Bench aggregate --
        trials = conn.execute(
            "SELECT task_id, resolved, is_infra_fail, wall_seconds, output_tokens FROM tb_trials "
            "WHERE round_id = ? AND model_id = ?", (round_id, model_id)).fetchall()
        valid = [t for t in trials if not t["is_infra_fail"]]
        n_tasks = len({t["task_id"] for t in valid})
        n_attempts = conn.execute(
            "SELECT MAX(attempt) FROM tb_trials WHERE round_id = ? AND model_id = ?",
            (round_id, model_id)).fetchone()[0] or 0
        acc = (sum(t["resolved"] for t in valid) / len(valid)) if valid else 0.0
        p4 = tb_pass_hat_k([(t["task_id"], t["resolved"]) for t in valid], k=4)
        walls = [t["wall_seconds"] for t in valid if t["wall_seconds"] is not None]
        tokens = [t["output_tokens"] for t in valid if t["output_tokens"] is not None]
        conn.execute(
            "INSERT OR REPLACE INTO tb_aggregates "
            "(round_id,model_id,n_tasks,n_attempts,n_resolved,accuracy,pass_hat_k,"
            "median_wall_seconds,total_output_tokens,computed_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (round_id, model_id, n_tasks, n_attempts, sum(t["resolved"] for t in valid),
             acc, p4, median(walls) if len(walls) == len(valid) else None,
             sum(tokens) if len(tokens) == len(valid) else None, now))

        # -- GPQA aggregate --
        q = conn.execute(
            "SELECT COUNT(*) n, SUM(correct) c, SUM(is_no_answer) na FROM gpqa_trials "
            "WHERE round_id = ? AND model_id = ?", (round_id, model_id)).fetchone()
        gacc = (q["c"] / q["n"]) if q["n"] else 0.0
        domains = []
        for domain in ("biology", "physics", "chemistry"):
            d = conn.execute("""SELECT COUNT(*) n, SUM(t.correct) c FROM gpqa_trials t
                JOIN gpqa_questions q USING(question_id)
                WHERE t.round_id=? AND t.model_id=? AND lower(q.domain)=?""",
                (round_id, model_id, domain)).fetchone()
            domains.append(d["c"] / d["n"] if d["n"] else None)
        conn.execute(
            "INSERT OR REPLACE INTO gpqa_aggregates VALUES (?,?,?,?,?,?,?,?,?,?)",
            (round_id, model_id, q["n"], q["c"] or 0, q["na"] or 0, gacc, *domains, now))

        # -- Meta grade --
        meta = math.sqrt(p4 * gacc)
        conn.execute(
            "INSERT OR REPLACE INTO meta_grades VALUES (?,?,?,?,?,?,?,?)",
            (round_id, model_id, p4, gacc, meta, None, None, now))
        summary.append((model_id, n_tasks, acc, p4, q["n"], gacc, meta))
        tb_scores[model_id] = p4
        if q["n"]:
            gpqa_scores[model_id] = gacc

    # -- z-scores vs round cohort (context, not a second meta grade) --
    def z(scores, key):
        if len(scores) < 2:
            return
        vals = list(scores.values())
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(var) or 1e-9
        for mid, v in scores.items():
            conn.execute("UPDATE meta_grades SET {} = ? WHERE round_id = ? AND model_id = ?".format(key),
                         ((v - mean) / std, round_id, mid))

    z(tb_scores, "tb_z_vs_round")
    z(gpqa_scores, "gpqa_z_vs_round")

    print(f"Round {round_id} — {len(models)} models")
    print(f"{'model':<20} {'TB tasks':>8} {'TB acc':>8} {'TB pass^4':>10} "
          f"{'GPQA n':>7} {'GPQA acc':>9} {'meta':>7}")
    for m, nt, a, p4, nq, g, meta in summary:
        print(f"{m:<20} {nt:>8} {a:>8.3f} {(p4 or 0):>10.3f} "
              f"{nq:>7} {g:>9.3f} {(meta or 0):>7.3f}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
