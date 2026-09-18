-- schema.sql — structured results collection for the two-benchmark eval protocol.
-- One SQLite DB per round (or per model) at: results/R00X/results.db
-- Apply with: sqlite3 results.db < schema.sql

PRAGMA journal_mode = WAL;

-- ─── Round + protocol identity ────────────────────────────────────────────
CREATE TABLE rounds (
    round_id        TEXT PRIMARY KEY,          -- 'R001', 'R002', ...
    protocol_id     TEXT NOT NULL,             -- 'tbx-gpqa-v1'
    started_at      TEXT NOT NULL,             -- ISO 8601 UTC
    finished_at     TEXT,
    config_path     TEXT,                      -- path to eval-config.yaml copy
    tb_dataset_version TEXT NOT NULL,          -- e.g. 'terminal-bench-core 0.1.1'
    tb_harness_commit  TEXT NOT NULL,
    backend         TEXT NOT NULL,             -- 'llama.cpp'
    backend_version TEXT NOT NULL,
    quantization    TEXT NOT NULL,             -- 'Q4_K_M'
    context_window  INTEGER NOT NULL,
    temperature     REAL NOT NULL,
    top_p           REAL NOT NULL,
    seed            INTEGER NOT NULL,
    thinking_mode   TEXT NOT NULL,             -- 'native' | 'forced' | 'off'
    machine         TEXT NOT NULL,
    notes           TEXT
);

-- ─── Model registry (frozen per round) ───────────────────────────────────
CREATE TABLE models (
    model_id        TEXT PRIMARY KEY,          -- short slug, e.g. 'qwen38-27b'
    display_name    TEXT NOT NULL,
    hf_repo         TEXT NOT NULL,
    weights_file    TEXT NOT NULL,             -- exact GGUF filename
    file_size_gb    REAL,
    params_b        REAL,                      -- claimed parameter count
    is_moe          INTEGER DEFAULT 0,
    active_params_b REAL,
    context_trained INTEGER,                   -- trained context length
    license         TEXT,
    provenance      TEXT,                      -- model card URL + date accessed
    notes           TEXT
);

-- ─── Terminal-Bench per-trial results ────────────────────────────────────
CREATE TABLE tb_trials (
    trial_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id        TEXT NOT NULL REFERENCES rounds(round_id),
    model_id        TEXT NOT NULL REFERENCES models(model_id),
    task_id         TEXT NOT NULL,
    attempt         INTEGER NOT NULL,          -- 1..n_attempts
    resolved        INTEGER NOT NULL,          -- 1/0
    parser_results  TEXT,                      -- JSON blob from harness
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    started_at      TEXT,
    ended_at        TEXT,
    wall_seconds    REAL,
    error           TEXT,                      -- harness/infra failure vs model failure
    is_infra_fail   INTEGER DEFAULT 0          -- exclude from accuracy if 1 (rerun instead)
);
CREATE INDEX idx_tb_trials ON tb_trials(round_id, model_id, task_id);

-- ─── Terminal-Bench per-model aggregate ──────────────────────────────────
CREATE TABLE tb_aggregates (
    round_id        TEXT NOT NULL REFERENCES rounds(round_id),
    model_id        TEXT NOT NULL REFERENCES models(model_id),
    n_tasks         INTEGER NOT NULL,
    n_attempts      INTEGER NOT NULL,
    n_resolved      INTEGER NOT NULL,
    accuracy        REAL NOT NULL,             -- resolved / total trials
    pass_hat_k      REAL,                      -- pass^4 primary metric
    median_wall_seconds REAL,
    total_output_tokens INTEGER,
    computed_at     TEXT NOT NULL,
    PRIMARY KEY (round_id, model_id)
);

-- ─── GPQA Diamond per-question results ───────────────────────────────────
CREATE TABLE gpqa_questions (
    question_id     TEXT PRIMARY KEY,          -- stable: hash of question text
    domain          TEXT,                      -- biology / physics / chemistry
    difficulty      TEXT,                      -- from dataset metadata
    question_text   TEXT NOT NULL
);

CREATE TABLE gpqa_trials (
    trial_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id        TEXT NOT NULL REFERENCES rounds(round_id),
    model_id        TEXT NOT NULL REFERENCES models(model_id),
    question_id     TEXT NOT NULL REFERENCES gpqa_questions(question_id),
    attempt         INTEGER NOT NULL DEFAULT 1,
    predicted_letter TEXT,                     -- 'A'-'D' or NULL if no-answer
    correct         INTEGER NOT NULL,          -- 1/0
    is_no_answer    INTEGER DEFAULT 0,         -- extraction failed
    raw_response_path TEXT,                    -- path to full CoT response on disk
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    wall_seconds    REAL
);
CREATE INDEX idx_gpqa_trials ON gpqa_trials(round_id, model_id);

-- ─── GPQA per-model aggregate (accuracy overall + per-domain) ────────────
CREATE TABLE gpqa_aggregates (
    round_id        TEXT NOT NULL REFERENCES rounds(round_id),
    model_id        TEXT NOT NULL REFERENCES models(model_id),
    n_questions     INTEGER NOT NULL,
    n_correct       INTEGER NOT NULL,
    n_no_answer     INTEGER NOT NULL,
    accuracy        REAL NOT NULL,
    accuracy_bio    REAL,
    accuracy_phys   REAL,
    accuracy_chem   REAL,
    computed_at     TEXT NOT NULL,
    PRIMARY KEY (round_id, model_id)
);

-- ─── Meta grade per model per round ──────────────────────────────────────
CREATE TABLE meta_grades (
    round_id        TEXT NOT NULL REFERENCES rounds(round_id),
    model_id        TEXT NOT NULL REFERENCES models(model_id),
    tb_metric       REAL NOT NULL,             -- pass^4
    gpqa_accuracy   REAL NOT NULL,
    meta_grade      REAL NOT NULL,             -- geometric mean
    tb_z_vs_round   REAL,                      -- z-score vs round cohort
    gpqa_z_vs_round REAL,
    computed_at     TEXT NOT NULL,
    PRIMARY KEY (round_id, model_id)
);

-- ─── Infra / environment incident log ────────────────────────────────────
CREATE TABLE incidents (
    incident_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id        TEXT NOT NULL REFERENCES rounds(round_id),
    model_id        TEXT,
    benchmark       TEXT NOT NULL,             -- 'tb' | 'gpqa'
    severity        TEXT NOT NULL,             -- 'info' | 'warning' | 'fatal'
    description     TEXT NOT NULL,
    resolved        INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);
