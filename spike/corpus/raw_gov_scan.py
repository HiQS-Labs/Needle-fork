"""#9: two-pass deterministic scan of RAW Claude Code transcripts for governance acts.

The question this answers is NOT "can we extract governance" -- it is:

    Does the raw transcript contain governance acts that the CURRENT extractor
    is losing, or is governance genuinely this rare?

That matters because #2 ("arguments still read as invocations") is an open,
known labelling defect of exactly the class that would silently drop these.
Comparing the RAW ceiling against what `data/corpus-*/` actually produced
separates extractor loss from real scarcity, and the two answers point at
completely different work.

TWO PASSES, deliberately:

  Pass 1 (this file, --pass1) -- cheap, high-recall regex over raw JSONL lines.
    Optimised for RECALL: it may over-match. It never decides a label; it only
    says "this line is worth parsing". Regex over raw text is the wrong tool for
    labelling -- that is precisely the bug class in #2 -- but it is the right
    tool for cutting gigabytes down to candidates.

  Pass 2 (--pass2) -- parse each candidate as a real tool call and label it with
    `utils/corpus/taxonomy.py`, which already carries the segmentation, the
    specificity tiers, and the ARG_CONSUMERS rule that stops a package name or a
    grep pattern being read as an invocation. Precision lives here, in the
    shared labeller, NOT in a second pile of regexes.

Privacy: pass 1 prints counts only. Pass 2 writes labelled rows to --out, which
must live outside the repo -- transcripts contain real prompt text and this repo
is public. `data/` is gitignored; nothing derived from prompt text gets committed.
"""
import argparse, collections, glob, json, os, re, sys

# Pass-1 candidate patterns. HIGH RECALL, low precision, on purpose.
CANDIDATE = re.compile(
    r'git\s+mv\b|'
    r'1-INBOX|2-WORKING|3-COMPLETED|'
    r'releases_app\.py|releases_cycle\.py|release-lanes\.sh|'
    r'gh\s+release\b|git\s+tag\b|'
    r'pdda\.sh|validate\.sh|'
    r'relay-drive\.sh|marathon-drive\.sh|consult\.sh|'
    r'ROADMAP\.md|RELEASES\.md|CHANGELOG\.md'
)

# Narrow signatures, reported per label in pass 1 as a ceiling estimate only.
SIGS = {
 "promote_capture":  re.compile(r'git\s+mv\b[^"\']*1-INBOX[^"\']*2-WORKING'),
 "complete_doc":     re.compile(r'git\s+mv\b[^"\']*(2-WORKING|1-INBOX)[^"\']*3-COMPLETED'),
 "park_roadmap_row": re.compile(r'releases_app\.py\s+roadmap\b'),
 "cut_release":      re.compile(r'releases_app\.py\s+(cut|release)\b|releases_cycle\.py'),
 "publish_release":  re.compile(r'gh\s+release\s+create|git\s+tag\s+-a'),
 "run_pdda_check":   re.compile(r'pdda\.sh\b'),
 "run_validate":     re.compile(r'validate\.sh\b'),
 "start_relay":      re.compile(r'relay-drive\.sh|marathon-drive\.sh|consult\.sh'),
}

def iter_lines(root):
    for fp in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        try:
            with open(fp, errors="ignore") as fh:
                for line in fh:
                    yield fp, line
        except OSError:
            continue

def pass1(root):
    hits = collections.Counter()
    cands = 0; lines = 0
    for _, line in iter_lines(root):
        lines += 1
        if not CANDIDATE.search(line):
            continue
        cands += 1
        for lab, rx in SIGS.items():
            if rx.search(line):
                hits[lab] += 1
    return lines, cands, hits

def pass2(root, out):
    """Parse candidates as real tool calls and label via the shared taxonomy."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "utils", "corpus"))
    import taxonomy as tx
    counts = collections.Counter(); written = 0
    fh_out = open(out, "w") if out else None
    for fp, line in iter_lines(root):
        if not CANDIDATE.search(line):
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        # walk the record for tool_use blocks; shape varies by transcript version
        stack = [rec]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("type") == "tool_use" and "name" in node:
                    # label_call returns (label, evidence) -- NOT a bare string.
                    # Treating the tuple as truthy silently counted tuples as keys
                    # and reported zero governance. Caught by testing the labeller
                    # directly on a known governance command before believing the
                    # scan's output.
                    lab, _ev = tx.label_call(node.get("name", ""), node.get("input", {}) or {})
                    if lab:
                        counts[lab] += 1
                        if fh_out:
                            fh_out.write(json.dumps({"label": lab,
                                                     "tool": node.get("name"),
                                                     "source": os.path.basename(fp)}) + "\n")
                            written += 1
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
    if fh_out:
        fh_out.close()
    return counts, written

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="a ~/.claude/projects directory")
    ap.add_argument("--pass2", action="store_true")
    ap.add_argument("--out", default="", help="pass 2 only; MUST be outside the repo")
    args = ap.parse_args()

    if not args.pass2:
        lines, cands, hits = pass1(args.root)
        print(f"lines scanned   : {lines:,}")
        print(f"candidate lines : {cands:,}  ({100*cands/max(lines,1):.2f}%)\n")
        print(f"{'label':<20}{'raw signature hits':>20}")
        for lab in SIGS:
            print(f"  {lab:<18}{hits.get(lab,0):>18}")
        print(f"\n  TOTAL: {sum(hits.values())}")
        print("\nThese are a RECALL CEILING, not labels. Run --pass2 to label them "
              "through taxonomy.py before believing any of them.")
    else:
        counts, written = pass2(args.root, args.out)
        gov = {k: v for k, v in counts.items()
               if k in ("promote_capture","complete_doc","park_roadmap_row","cut_release",
                        "publish_release","run_pdda_check","update_roadmap","update_changelog",
                        "file_capture_doc","start_relay","run_validate","update_working_doc",
                        "update_governance_doc")}
        print("labelled via taxonomy.py (governance only):")
        for k in sorted(gov, key=lambda k: -gov[k]):
            print(f"  {k:<22}{gov[k]:>7}")
        print(f"\n  governance total {sum(gov.values())} of {sum(counts.values())} labelled calls")
        if args.out:
            print(f"  wrote {written} rows -> {args.out}")

if __name__ == "__main__":
    main()
