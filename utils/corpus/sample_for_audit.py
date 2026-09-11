#!/usr/bin/env python3
"""Draw a stratified sample of labelled calls for a blind correctness audit.

WHY THIS EXISTS
    Every number measured about the sorter counts RESOLUTION -- did a call get *a*
    label. Nothing has measured whether the label is RIGHT (issue #1 §2 defines
    dataset validity as coverage, which cannot tell a right label from a wrong one).
    See PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md and LESSONS-LEARNED.md §15.

PRIVACY -- READ BEFORE CHANGING
    The sample contains REAL COMMAND TEXT from the operator's private transcripts,
    and this repository is PUBLIC. Everything this script writes goes under `data/`,
    which is gitignored, and must NEVER be committed -- not in a relay file, not in
    a receipt, not in an issue comment. Only aggregates leave `data/`.

BLIND PROTOCOL
    `sample.jsonl` carries the call text WITHOUT the sorter's label, so an auditor
    assigns a label without anchoring on the answer. The sorter's labels are held
    back in `sorter.jsonl` and joined only at scoring time.

READINESS
    `--check-only` validates a manifest-restricted source and emits aggregate JSON
    from the same post-filter pool and exact allocator used by the real draw. It
    never writes sample rows and keeps exit 2 for an incomplete gate.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy as tx
from measure_taxonomy import iter_call_records, iter_calls
from transcript_events import (IDENTITY_FORMAT_VERSION, read_transcript,
                               validate_namespace)


EXPERIMENT_MANIFEST_VERSION = 1
SAMPLING_DESIGN = "stratified-srswor-v1"
TARGETED_DESIGN = "session-constrained-targeted-v1"
READINESS_REPORT_VERSION = "audit-readiness-v1"


class DrawCapacityError(ValueError):
    """The requested label quotas cannot fit under the session cap."""

    def __init__(self, capacity: int, target: int):
        self.capacity = capacity
        self.target = target
        super().__init__(
            f"label quotas and session cap permit only {capacity} rows, "
            f"below requested {target}")


def render(tool: str, inp: dict) -> str:
    """What the sorter actually reads, as one auditable line."""
    if tool == "Bash":
        return (inp.get("command") or "").strip()
    fp = inp.get("file_path") or inp.get("path") or ""
    pat = inp.get("pattern") or inp.get("query") or ""
    return " ".join(x for x in (fp, pat) if x).strip()


def allocate(counts: dict, target: int, floor: int) -> dict:
    """Floor per stratum, remainder proportional to sqrt(count).

    Uniform allocation would give the governance labels 2-3 rows -- they are the
    labels the Oracle exists for and the thinnest in the corpus. sqrt keeps the
    large strata represented without letting `read_file` eat the sample.
    """
    if not counts or any(v <= 0 for v in counts.values()):
        raise ValueError("population strata must be non-empty positive counts")
    if target <= 0 or floor <= 0:
        raise ValueError("target and floor must be positive")
    if target > sum(counts.values()):
        raise ValueError("target exceeds the renderable population")

    take = {k: min(v, floor) for k, v in counts.items()}
    minimum = sum(take.values())
    if target < minimum:
        raise ValueError(f"target {target} is below the {minimum}-row stratum floor")
    rest = target - sum(take.values())
    while rest:
        room = {k: counts[k] - take[k] for k in counts if counts[k] > take[k]}
        if not room:
            raise ValueError("allocation exhausted the population before reaching target")
        weights = {k: math.sqrt(counts[k]) for k in room}
        total_weight = sum(weights.values())
        quotas = {k: rest * weights[k] / total_weight for k in room}
        grants = {k: min(room[k], int(quotas[k])) for k in room}
        granted = sum(grants.values())
        if not granted:
            # Largest-remainder tie break is deterministic by label.
            k = max(room, key=lambda x: (quotas[x], weights[x], x))
            grants[k] = 1
            granted = 1
        for k, amount in grants.items():
            take[k] += amount
        rest -= granted
    return {k: v for k, v in take.items() if v}


def _row_rank(seed: int, row: dict) -> str:
    identity = row.get("source_event_id") or json.dumps(
        [row["session"], row["tool"], row["text"]], ensure_ascii=False)
    return hashlib.sha256(f"{seed}:{identity}".encode()).hexdigest()


def _add_edge(graph: list[list[list[int]]], source: int, target: int,
              capacity: int, cost: int) -> list[int]:
    forward = [target, len(graph[target]), capacity, cost, capacity]
    reverse = [source, len(graph[source]), 0, -cost, 0]
    graph[source].append(forward)
    graph[target].append(reverse)
    return forward


def _min_cost_flow(graph: list[list[list[int]]], source: int, sink: int,
                   target_flow: int) -> tuple[int, int]:
    """Integral successive-shortest-path flow for the small audit graph."""
    flow = cost = 0
    node_count = len(graph)
    while flow < target_flow:
        distance = [float("inf")] * node_count
        previous: list[tuple[int, int] | None] = [None] * node_count
        queued = [False] * node_count
        queue = collections.deque([source])
        distance[source] = 0
        queued[source] = True
        while queue:
            node = queue.popleft()
            queued[node] = False
            for edge_index, edge in enumerate(graph[node]):
                neighbor, _, capacity, edge_cost, _ = edge
                candidate = distance[node] + edge_cost
                if capacity > 0 and candidate < distance[neighbor]:
                    distance[neighbor] = candidate
                    previous[neighbor] = (node, edge_index)
                    if not queued[neighbor]:
                        queue.append(neighbor)
                        queued[neighbor] = True
        if previous[sink] is None:
            break
        amount = target_flow - flow
        node = sink
        while node != source:
            prior, edge_index = previous[node]
            amount = min(amount, graph[prior][edge_index][2])
            node = prior
        node = sink
        while node != source:
            prior, edge_index = previous[node]
            edge = graph[prior][edge_index]
            edge[2] -= amount
            graph[node][edge[1]][2] += amount
            cost += amount * edge[3]
            node = prior
        flow += amount
    return flow, cost


def _targeted_draw(pool: dict, plan: dict, seed: int, min_sessions: int,
                   max_per_session: int) -> list[tuple[str, dict]]:
    """Solve exact label quotas under a session cap, maximizing session spread."""
    target = sum(plan.values())
    cap = max_per_session or target
    if min_sessions > target:
        raise ValueError(
            f"required {min_sessions} sessions exceeds the {target}-row target")
    grouped = collections.defaultdict(list)
    for label in sorted(plan):
        for row in pool[label]:
            grouped[(label, row["session"])].append(row)
    sessions = sorted(
        {session for _, session in grouped},
        key=lambda session: hashlib.sha256(
            f"{seed}:session:{session}".encode()).hexdigest())
    if len(sessions) < min_sessions:
        raise ValueError(
            f"eligible inventory has {len(sessions)} sessions, below required {min_sessions}")

    labels = sorted(plan)
    source = 0
    label_nodes = {label: index + 1 for index, label in enumerate(labels)}
    session_start = 1 + len(labels)
    session_nodes = {
        session: session_start + index for index, session in enumerate(sessions)}
    sink = session_start + len(sessions)
    graph: list[list[list[int]]] = [[] for _ in range(sink + 1)]
    for label in labels:
        _add_edge(graph, source, label_nodes[label], plan[label], 0)
    allocation_edges = {}
    for label in labels:
        available_sessions = [
            session for session in sessions if (label, session) in grouped]
        available_sessions.sort(key=lambda session: hashlib.sha256(
            f"{seed}:label-session:{label}:{session}".encode()).hexdigest())
        for session in available_sessions:
            allocation_edges[(label, session)] = _add_edge(
                graph, label_nodes[label], session_nodes[session],
                len(grouped[(label, session)]), 0)
    for session in sessions:
        _add_edge(graph, session_nodes[session], sink, 1, -1)
        if cap > 1:
            _add_edge(graph, session_nodes[session], sink, cap - 1, 0)

    flow, flow_cost = _min_cost_flow(graph, source, sink, target)
    if flow != target:
        raise DrawCapacityError(flow, target)
    used_sessions = -flow_cost
    if used_sessions < min_sessions:
        raise ValueError(
            f"constraints permit at most {used_sessions} sessions, below required {min_sessions}")

    selected = []
    for key, edge in allocation_edges.items():
        amount = edge[4] - edge[2]
        if not amount:
            continue
        label, _ = key
        candidates = sorted(grouped[key], key=lambda row: _row_rank(seed, row))
        selected.extend((label, row) for row in candidates[:amount])
    if len(selected) != target:
        raise ValueError(f"flow selected {len(selected)} rows, expected {target}")
    return selected


def readiness_inventory(pool: dict, target: int, min_sessions: int,
                        max_per_session: int) -> dict:
    """Return aggregate inventory metrics from the exact post-filter pool."""
    session_counts = collections.Counter(
        row["session"] for rows in pool.values() for row in rows)
    cap = max_per_session or target
    return {
        "status": "INCOMPLETE",
        "target_rows": target,
        "reviewable_rows": sum(map(len, pool.values())),
        "reviewable_labels_present": len(pool),
        "eligible_sessions": len(session_counts),
        "min_sessions": min_sessions,
        "max_per_session": max_per_session,
        "raw_session_cap_capacity": sum(
            min(count, cap) for count in session_counts.values()),
        "label_constrained_capacity": None,
    }


def targeted_readiness(pool: dict, plan: dict, seed: int, min_sessions: int,
                       max_per_session: int) -> dict:
    """Return aggregate feasibility metrics from the exact post-filter pool."""
    target = sum(plan.values())
    report = readiness_inventory(
        pool, target, min_sessions, max_per_session)
    try:
        selected = _targeted_draw(
            pool, plan, seed, 0, max_per_session)
    except DrawCapacityError as exc:
        report["label_constrained_capacity"] = exc.capacity
        report["reason"] = str(exc)
    except ValueError as exc:
        report["reason"] = str(exc)
    else:
        report["label_constrained_capacity"] = target
        try:
            selected = _targeted_draw(
                pool, plan, seed, min_sessions, max_per_session)
        except ValueError as exc:
            report["reason"] = str(exc)
        else:
            report.update({
                "status": "READY",
                "selected_sessions": len({row["session"] for _, row in selected}),
                "reason": None,
            })
    return report


def _finish_draw(selected: list[tuple[str, dict]], seed: int
                 ) -> tuple[list[dict], list[dict]]:
    """Shuffle selected rows and assign blind IDs without exposing strata."""
    rng = random.Random(seed)
    rng.shuffle(selected)
    sample, truth, ids = [], [], set()
    for ordinal, (label, row) in enumerate(selected):
        stable_event = row.get("source_event_id")
        identity = (["event", stable_event] if stable_event else
                    ["legacy", row["session"], row["tool"], row["text"]])
        material = json.dumps([seed, ordinal, identity], ensure_ascii=False,
                              separators=(",", ":"))
        rid = "a" + hashlib.sha256(material.encode()).hexdigest()[:16]
        if rid in ids:
            raise ValueError("blind row ID collision")
        ids.add(rid)
        sample.append({"id": rid, "tool": row["tool"], "text": row["text"]})
        truth_row = {"id": rid, "sorter_label": label, "session": row["session"]}
        for key in ("identity_format", "source_namespace", "source_relpath",
                    "transcript_sha256", "source_event_id", "source_event_ordinal"):
            if key in row:
                truth_row[key] = row[key]
        truth.append(truth_row)
    return sample, truth


def draw(pool: dict, plan: dict, seed: int, min_sessions: int = 0,
         max_per_session: int = 0) -> tuple[list[dict], list[dict]]:
    """Use SRS without session limits or an explicitly targeted constrained draw."""
    if min_sessions < 0 or max_per_session < 0:
        raise ValueError("session constraints cannot be negative")
    if min_sessions or max_per_session:
        selected = _targeted_draw(
            pool, plan, seed, min_sessions, max_per_session)
    else:
        rng = random.Random(seed)
        selected = []
        for label in sorted(plan):
            for row in rng.sample(pool[label], plan[label]):
                selected.append((label, row))
    sample, truth = _finish_draw(selected, seed)
    session_counts = collections.Counter(row["session"] for row in truth)
    if min_sessions and len(session_counts) < min_sessions:
        raise ValueError(
            f"frozen SRS draw has {len(session_counts)} sessions, "
            f"below required {min_sessions}")
    observed_max = max(session_counts.values(), default=0)
    if max_per_session and observed_max > max_per_session:
        raise ValueError(
            f"frozen SRS draw has {observed_max} rows from one session, "
            f"above cap {max_per_session}")
    return sample, truth


def _parse_source_roots(values: list[str]) -> dict[str, str]:
    roots = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--source-root must be NAMESPACE=PATH")
        namespace, path = value.split("=", 1)
        validate_namespace(namespace)
        if namespace in roots:
            raise ValueError(f"duplicate source namespace {namespace!r}")
        root = os.path.realpath(os.path.expanduser(path))
        if not os.path.isdir(root):
            raise ValueError(f"source root for {namespace!r} is not a directory")
        roots[namespace] = root
    if not roots:
        raise ValueError("at least one --source-root is required with --eligible-manifest")
    return roots


def _load_manifest_pool(path: str, side: str, source_roots: list[str]
                        ) -> tuple[dict, str, dict]:
    """Rebuild auditable calls for one source-gated manifest side."""
    with open(path) as fh:
        manifest = json.load(fh)
    if not isinstance(manifest, dict):
        raise ValueError("eligible manifest must be a JSON object")
    claimed = manifest.get("manifest_sha256")
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    actual = hashlib.sha256(json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    if claimed != actual:
        raise ValueError("eligible manifest hash does not match its contents")
    if manifest.get("manifest_format_version") != EXPERIMENT_MANIFEST_VERSION:
        raise ValueError("unsupported eligible manifest format")
    if manifest.get("identity_format") != IDENTITY_FORMAT_VERSION:
        raise ValueError("eligible manifest identity format differs")
    if manifest.get("label_set_version") != tx.LABEL_SET_VERSION:
        raise ValueError("eligible manifest label set differs")
    sides = manifest.get("sides")
    if side not in ("correction", "evaluation") or not isinstance(sides, dict):
        raise ValueError("--manifest-side must be correction or evaluation")
    section = sides.get(side)
    rows = section.get("rows") if isinstance(section, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"eligible manifest side {side!r} has no rows")

    roots = _parse_source_roots(source_roots)
    expected = {}
    grouped = collections.defaultdict(list)
    required = {
        "source_namespace", "source_relpath", "session", "transcript_sha256",
        "source_event_id", "source_event_ordinal", "label",
    }
    for row in rows:
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError("eligible manifest row lacks source identity")
        event_id = row["source_event_id"]
        if event_id in expected:
            raise ValueError(f"duplicate eligible source_event_id {event_id}")
        namespace = row["source_namespace"]
        if namespace not in roots:
            raise ValueError(f"no --source-root declared for {namespace!r}")
        expected[event_id] = row
        grouped[(namespace, row["source_relpath"])].append(row)

    pool = collections.defaultdict(list)
    unrenderable = 0
    for (namespace, relpath), group in sorted(grouped.items()):
        root = roots[namespace]
        source_path = os.path.realpath(os.path.join(root, relpath))
        try:
            inside = os.path.commonpath([root, source_path]) == root
        except ValueError:
            inside = False
        if not inside or source_path == root:
            raise ValueError(f"source_relpath escapes its declared root: {relpath!r}")
        meta, steps = read_transcript(source_path, root, namespace)
        actions = {step.source_event_id: step for step in steps if step.kind == "action"}
        for row in group:
            if (row["session"] != meta.session_id or
                    row["transcript_sha256"] != meta.transcript_sha256):
                raise ValueError(f"source identity drift for {namespace}:{relpath}")
            step = actions.get(row["source_event_id"])
            if step is None or step.action_ordinal != row["source_event_ordinal"]:
                raise ValueError(f"source event drift for {namespace}:{relpath}")
            label, _ = tx.label_call(step.tool, step.tool_input or {})
            if label != row["label"]:
                raise ValueError(f"sorter label drift for {row['source_event_id']}")
            text = render(step.tool, step.tool_input or {})
            if not text:
                unrenderable += 1
                continue
            pool[label].append({
                "session": meta.session_id,
                "tool": step.tool,
                "text": text,
                "identity_format": IDENTITY_FORMAT_VERSION,
                "source_namespace": namespace,
                "source_relpath": relpath,
                "transcript_sha256": meta.transcript_sha256,
                "source_event_id": step.source_event_id,
                "source_event_ordinal": step.action_ordinal,
            })
    if sum(map(len, pool.values())) + unrenderable != len(expected):
        raise ValueError("eligible manifest events were not reconstructed exactly once")
    if not pool:
        raise ValueError("eligible manifest has no auditable source events")
    return pool, claimed, {
        "manifest_rows": len(expected),
        "excluded_unrenderable": unrenderable,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--source-namespace",
                    help="opt into v3 audit rows with mount-invariant source identity")
    ap.add_argument("--eligible-manifest",
                    help="private PR #26 experiment manifest used to restrict the draw")
    ap.add_argument("--manifest-side", choices=("correction", "evaluation"))
    ap.add_argument("--source-root", action="append", default=[],
                    help="NAMESPACE=PATH; repeat for every eligible-manifest namespace")
    ap.add_argument("--out-dir", default="data/audit")
    ap.add_argument("--target", type=int, default=400)
    ap.add_argument("--floor", type=int, default=8,
                    help="minimum rows per label present in the corpus")
    ap.add_argument("--seed", type=int, default=20260909)
    ap.add_argument("--min-sessions", type=int, default=0)
    ap.add_argument("--max-per-session", type=int, default=0)
    ap.add_argument(
        "--check-only", action="store_true",
        help="validate a manifest-restricted draw and print aggregate JSON without writing it")
    args = ap.parse_args(argv)

    if args.check_only and not args.eligible_manifest:
        print("refusing: --check-only requires --eligible-manifest", file=sys.stderr)
        return 2
    if not args.check_only:
        data_root = os.path.realpath("data")
        output_dir = os.path.realpath(args.out_dir)
        try:
            inside_data = os.path.commonpath([data_root, output_dir]) == data_root
        except ValueError:
            inside_data = False
        if not inside_data or output_dir == data_root:
            print("refusing: the sample contains real prompt text and must stay under data/",
                  file=sys.stderr)
            return 2
        occupied = sorted(os.listdir(args.out_dir)) if os.path.isdir(args.out_dir) else []
        if occupied:
            print(f"refusing to overwrite an existing audit ({', '.join(occupied)}); "
                  "choose a new --out-dir", file=sys.stderr)
            return 2

    pool = collections.defaultdict(list)
    manifest_sha256 = None
    manifest_selection = None
    try:
        if args.eligible_manifest:
            if not args.manifest_side:
                raise ValueError("--manifest-side is required with --eligible-manifest")
            if args.source_namespace:
                raise ValueError("--source-namespace cannot be combined with --eligible-manifest")
            if args.min_sessions <= 0 or args.max_per_session <= 0:
                raise ValueError(
                    "manifest-restricted draws require positive --min-sessions and "
                    "--max-per-session")
            pool, manifest_sha256, manifest_selection = _load_manifest_pool(
                args.eligible_manifest, args.manifest_side, args.source_root)
        elif args.source_root or args.manifest_side:
            raise ValueError("--source-root/--manifest-side require --eligible-manifest")
        elif args.source_namespace:
            validate_namespace(args.source_namespace)
            records = iter_call_records(args.source, args.source_namespace)
            for record in records:
                label, _ = tx.label_call(record["tool"], record["input"])
                text = render(record["tool"], record["input"])
                if text:
                    pool[label].append({
                        "session": record["session"],
                        "tool": record["tool"],
                        "text": text,
                        "identity_format": IDENTITY_FORMAT_VERSION,
                        "source_namespace": record["source_namespace"],
                        "source_relpath": record["source_relpath"],
                        "transcript_sha256": record["transcript_sha256"],
                        "source_event_id": record["source_event_id"],
                        "source_event_ordinal": record["source_event_ordinal"],
                    })
        else:
            for path, tool, inp in iter_calls(args.source):
                label, _ = tx.label_call(tool, inp)
                text = render(tool, inp)
                if text:
                    pool[label].append({"session": path, "tool": tool, "text": text})
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"refusing: cannot identify source calls: {exc}", file=sys.stderr)
        return 2

    counts = {k: len(v) for k, v in pool.items()}
    try:
        plan = allocate(counts, args.target, args.floor)
    except ValueError as exc:
        if args.check_only:
            report = {
                "report_format": READINESS_REPORT_VERSION,
                "eligible_manifest_sha256": manifest_sha256,
                "manifest_side": args.manifest_side,
                "manifest_rows": manifest_selection["manifest_rows"],
                "excluded_unrenderable": manifest_selection["excluded_unrenderable"],
                "seed": args.seed,
                "floor": args.floor,
                **readiness_inventory(
                    pool, args.target, args.min_sessions, args.max_per_session),
                "reason": str(exc),
            }
            print(json.dumps(report, sort_keys=True))
            return 2
        print(f"refusing: {exc}", file=sys.stderr)
        return 2

    if args.check_only:
        report = {
            "report_format": READINESS_REPORT_VERSION,
            "eligible_manifest_sha256": manifest_sha256,
            "manifest_side": args.manifest_side,
            "manifest_rows": manifest_selection["manifest_rows"],
            "excluded_unrenderable": manifest_selection["excluded_unrenderable"],
            "seed": args.seed,
            "floor": args.floor,
            **targeted_readiness(
                pool, plan, args.seed, args.min_sessions, args.max_per_session),
        }
        print(json.dumps(report, sort_keys=True))
        return 0 if report["status"] == "READY" else 2

    try:
        sample, truth = draw(
            pool, plan, args.seed, args.min_sessions, args.max_per_session)
    except ValueError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 2
    os.makedirs(args.out_dir, exist_ok=True)
    n = len(sample)
    for name, rows in (("sample.jsonl", sample), ("sorter.jsonl", truth)):
        with open(os.path.join(args.out_dir, name), "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    with open(os.path.join(args.out_dir, "plan.json"), "w") as fh:
        design = (TARGETED_DESIGN if args.min_sessions or args.max_per_session
                  else SAMPLING_DESIGN)
        plan_doc = {"audit_format_version": 3 if args.source_namespace else 2,
                   "seed": args.seed, "target": args.target, "floor": args.floor,
                   "sampling_design": design,
                   "label_set_version": tx.LABEL_SET_VERSION,
                   "population": counts, "allocation": plan, "drawn": n}
        if design == TARGETED_DESIGN:
            session_counts = collections.Counter(row["session"] for row in truth)
            plan_doc.update({
                "drawn_sessions": len(session_counts),
                "min_sessions": args.min_sessions,
                "max_per_session": args.max_per_session,
                "observed_max_per_session": max(session_counts.values()),
            })
        if args.source_namespace:
            plan_doc.update({"identity_format": IDENTITY_FORMAT_VERSION,
                             "source_namespace": args.source_namespace})
        if args.eligible_manifest:
            plan_doc.update({
                "audit_format_version": 3,
                "identity_format": IDENTITY_FORMAT_VERSION,
                "source_namespaces": sorted({
                    row["source_namespace"]
                    for values in pool.values() for row in values
                }),
                "eligible_manifest_sha256": manifest_sha256,
                "manifest_side": args.manifest_side,
                **manifest_selection,
                "eligible_sessions": len({
                    row["session"] for values in pool.values() for row in values
                }),
            })
        json.dump(plan_doc, fh, indent=2)

    print(f"population   {sum(counts.values()):,} calls across {len(counts)} labels")
    print(f"drawn        {n} rows across {len(plan)} strata (seed {args.seed})")
    print(f"wrote        {args.out_dir}/sample.jsonl (blind), sorter.jsonl (held back), plan.json")
    print("REMINDER: data/ is gitignored. Never commit or paste these rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
