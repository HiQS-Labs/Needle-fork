"""Shared helpers for the timeline dataset prototype (stdlib only).

Paths are never hardcoded to one operator's machine. Each script takes CLI flags; when a flag is
omitted the matching environment variable is used, then a generic default:

    --clio-log    NEEDLE_TL_CLIO_LOG    (required for build_sessions.py; no default)
    --out         NEEDLE_TL_OUT         ./out next to these scripts (gitignored)
    --claude-dir  NEEDLE_TL_CLAUDE_DIR  ~/.claude/projects
    --codex-dir   NEEDLE_TL_CODEX_DIR   ~/.codex/sessions
    --agy-dir     NEEDLE_TL_AGY_DIR     ~/.gemini/antigravity
"""
import re, json, os, sqlite3

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
KNOWN_TOOLS = {"agy", "codex", "claude-code", "zcode"}

def env_path(var, default=None):
    v = os.environ.get(var)
    return os.path.expanduser(v) if v else (os.path.expanduser(default) if default else None)

DEFAULT_OUT = env_path("NEEDLE_TL_OUT", os.path.join(HERE, "out"))

def add_out_arg(ap):
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="output directory (env NEEDLE_TL_OUT; default ./out next to the scripts, gitignored)")
    return ap

def resolve_out(path):
    """Create the output dir, refusing a location inside a git checkout unless git ignores it:
    outputs contain raw prompts and private repo metadata and must never be committed."""
    import subprocess
    out = os.path.abspath(os.path.expanduser(path))
    os.makedirs(out, exist_ok=True)
    try:
        inside = subprocess.run(["git", "-C", out, "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True, timeout=5).stdout.strip() == "true"
        if inside and subprocess.run(["git", "-C", out, "check-ignore", "-q", out], timeout=5).returncode != 0:
            raise SystemExit(f"refusing to write outputs to {out}: inside a git checkout and not gitignored")
    except (OSError, subprocess.SubprocessError):
        pass
    return out

def trunc(s, n):
    s = (s or "").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"

# ---------- minimal protobuf wire-format string extractor (agy) ----------
def pb_strings(b, depth=0, path=(), out=None):
    out = [] if out is None else out
    i, n = 0, len(b)
    try:
        while i < n:
            key = s = 0
            while True:
                c = b[i]; i += 1; key |= (c & 0x7F) << s; s += 7
                if c < 0x80: break
            wt, fn = key & 7, key >> 3
            if fn == 0: return out
            if wt == 0:
                while b[i] & 0x80: i += 1
                i += 1
            elif wt == 1: i += 8
            elif wt == 5: i += 4
            elif wt == 2:
                L = s = 0
                while True:
                    c = b[i]; i += 1; L |= (c & 0x7F) << s; s += 7
                    if c < 0x80: break
                sub = b[i:i + L]; i += L
                if L > len(sub): return out
                nested = []
                if depth < 10: pb_strings(sub, depth + 1, path + (fn,), nested)
                try:
                    t = sub.decode("utf-8")
                    ok = len(t) >= 2 and sum(ch.isprintable() or ch in "\n\t\r" for ch in t) / len(t) > 0.97
                except UnicodeDecodeError:
                    ok = False
                if ok and not (nested and sum(len(x[1]) for x in nested) >= 0.8 * L and len(t) < 40):
                    out.append((path + (fn,), t))
                else:
                    out.extend(nested)
            else:
                return out
    except IndexError:
        pass
    return out

def ro_sqlite(path):
    return sqlite3.connect(f"file:{os.path.abspath(path)}?mode=ro&immutable=1", uri=True)

def dump_jsonl(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
