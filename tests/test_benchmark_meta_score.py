"""Synthetic scoring controls; no model downloads or benchmark calls."""
import importlib.util
import math
from pathlib import Path
import sqlite3

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("benchmark_meta_score", ROOT / "benchmark-tests/meta_score.py")
scorer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scorer)


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "results.db"
    with sqlite3.connect(path) as conn:
        conn.executescript((ROOT / "benchmark-tests/schema.sql").read_text())
        conn.execute("""INSERT INTO rounds
            (round_id, protocol_id, started_at, tb_dataset_version, tb_harness_commit,
             backend, backend_version, quantization, context_window, temperature,
             top_p, seed, thinking_mode, machine)
            VALUES ('R001','synthetic','2026-09-17','fixture','fixture','fixture',
                    'fixture','fixture',100,0,1,42,'off','fixture')""")
        for model in ("a", "b"):
            conn.execute("INSERT INTO models (model_id,display_name,hf_repo,weights_file) VALUES (?,?,?,?)",
                         (model, model, "synthetic", "synthetic"))
            for task in ("t1", "t2"):
                for attempt in range(1, 5):
                    conn.execute("""INSERT INTO tb_trials
                        (round_id,model_id,task_id,attempt,resolved,wall_seconds,output_tokens)
                        VALUES ('R001',?,?,?,?,2,10)""", (model, task, attempt, int(model == "a")))
        for question, domain in (("q1", "biology"), ("q2", "physics")):
            conn.execute("INSERT INTO gpqa_questions VALUES (?,?,?,?)", (question, domain, None, "Synthetic"))
            for model in ("a", "b"):
                conn.execute("""INSERT INTO gpqa_trials
                    (round_id,model_id,question_id,correct,is_no_answer)
                    VALUES ('R001',?,?,?,?)""", (model, question, int(question == "q1"), 0))
    return path


def test_schema_integration_and_zero_score(database):
    scorer.main(str(database), "R001")
    with sqlite3.connect(database) as conn:
        rows = conn.execute("SELECT model_id,meta_grade,tb_z_vs_round FROM meta_grades ORDER BY model_id").fetchall()
        assert rows[0] == ("a", math.sqrt(0.5), 1.0)
        assert rows[1] == ("b", 0.0, -1.0)
        assert conn.execute("SELECT median_wall_seconds,total_output_tokens FROM tb_aggregates LIMIT 1").fetchone() == (2, 80)


@pytest.mark.parametrize("rows", [[], [("t", 1)] * 3, [("t", 1)] * 5,
                                      [("t", 1)] * 4 + [("incomplete", 0)], [("t", 2)] * 4])
def test_pass4_rejects_missing_extra_or_invalid_trials(rows):
    with pytest.raises(ValueError):
        scorer.tb_pass_hat_k(rows)


@pytest.mark.parametrize("mutation", [
    "DELETE FROM gpqa_trials WHERE model_id='b'",
    "DELETE FROM tb_trials WHERE model_id='b' AND attempt=4",
    "INSERT INTO tb_trials (round_id,model_id,task_id,attempt,resolved) VALUES ('R001','a','t1',1,1)",
    "UPDATE tb_trials SET is_infra_fail=1 WHERE model_id='b' AND task_id='t2'",
    "UPDATE gpqa_trials SET question_id='q3' WHERE model_id='b' AND question_id='q1'",
    "UPDATE gpqa_trials SET is_no_answer=1,correct=1 WHERE model_id='b' AND question_id='q1'",
])
def test_invalid_round_fails_before_writing(database, mutation):
    with sqlite3.connect(database) as conn:
        conn.execute(mutation)
    with pytest.raises(ValueError):
        scorer.main(str(database), "R001")
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tb_aggregates").fetchone()[0] == 0


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        scorer.main(str(path), "R001")
    assert not path.exists()


def test_infra_replacement_and_no_answer(database):
    with sqlite3.connect(database) as conn:
        conn.execute("""INSERT INTO tb_trials (round_id,model_id,task_id,attempt,resolved,is_infra_fail)
            VALUES ('R001','a','t1',1,0,1)""")
        conn.execute("UPDATE gpqa_trials SET correct=0,is_no_answer=1 WHERE question_id='q1'")
    scorer.main(str(database), "R001")
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT meta_grade FROM meta_grades WHERE model_id='a'").fetchone() == (0.0,)
        assert conn.execute("SELECT n_questions,n_no_answer,accuracy_bio,accuracy_phys,accuracy_chem FROM gpqa_aggregates WHERE model_id='a'").fetchone() == (2, 1, 0.0, 0.0, None)


def test_failed_write_rolls_back_all_projections(database):
    scorer.main(str(database), "R001")
    with sqlite3.connect(database) as conn:
        before = conn.execute("SELECT * FROM tb_aggregates ORDER BY model_id").fetchall()
        conn.execute("UPDATE tb_trials SET resolved=0 WHERE model_id='a'")
        conn.execute("""CREATE TRIGGER fail_gpqa BEFORE INSERT ON gpqa_aggregates
            BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="synthetic write failure"):
        scorer.main(str(database), "R001")
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT * FROM tb_aggregates ORDER BY model_id").fetchall() == before


def test_removed_cohort_members_do_not_leave_stale_grades(database):
    scorer.main(str(database), "R001")
    with sqlite3.connect(database) as conn:
        conn.execute("DELETE FROM tb_trials WHERE model_id='b'")
        conn.execute("DELETE FROM gpqa_trials WHERE model_id='b'")
    scorer.main(str(database), "R001")
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT model_id,tb_z_vs_round FROM meta_grades").fetchall() == [("a", None)]
