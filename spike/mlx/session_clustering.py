"""Recover session provenance for a frozen manifest and test whether clustering changes anything.

The open dissent from AgentChorus #810993 and #14's G5: receipts carry no session IDs, so
row independence is unverified and every row-level p-value assumes it. That was recorded as
an irrecoverable gap. It is not irrecoverable -- `data/corpus-studio/pairs.jsonl` carries
`session`, and `serialize.serialize_query` is deterministic and shared by the trainer and the
hook, so replaying it over the pairs rebuilds each manifest row's query and joins it back.

This does NOT make the rows independent. It measures how far from independent they are, and
reports a cluster-robust interval beside the naive test so the two can be compared.

  python spike/mlx/session_clustering.py --manifest data/spike-mlx/manifests/frozen-200.jsonl \
      --config data/spike-mlx/round-gates-14/round.json
"""
import argparse
import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath("."))
from audit_round import mcnemar, read_jsonl                       # noqa: E402
from utils.corpus.serialize import serialize_query                # noqa: E402


def query_to_session(pairs):
    """Replay the shared serializer over the extractor pairs -> {query: session}.

    First writer wins: a query identical across two sessions cannot be attributed, and
    the count of those collisions is reported rather than hidden.
    """
    index, collisions = {}, 0
    for _, pair in read_jsonl(pairs):
        if not pair.get("prior_actions"):
            continue
        try:
            query = serialize_query(pair.get("recent_user_request", ""), pair["prior_actions"])
        except ValueError:
            continue                                              # not a v1-renderable pair
        if query in index and index[query] != pair["session"]:
            collisions += 1
            continue
        index.setdefault(query, pair["session"])
    return index, collisions


def cluster_bootstrap(a, b, clusters, reps, seed):
    """Resample whole sessions with replacement -- the cluster is the sampling unit."""
    rng = random.Random(seed)
    keys = list(clusters)
    deltas = []
    for _ in range(reps):
        rows = [i for key in rng.choices(keys, k=len(keys)) for i in clusters[key]]
        deltas.append(sum(a[i] for i in rows) / len(rows) - sum(b[i] for i in rows) / len(rows))
    deltas.sort()
    return deltas[int(0.025 * reps)], deltas[int(0.975 * reps)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--config", required=True, help="a #14 round.json; its arms are compared")
    ap.add_argument("--pairs", default="data/corpus-studio/pairs.jsonl")
    ap.add_argument("--baseline", default="read_file", help="training-derived comparator")
    ap.add_argument("--reps", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    index, collisions = query_to_session(a.pairs)
    manifest = read_jsonl(a.manifest)
    ids = [hashlib.sha1(raw.encode()).hexdigest() for raw, _ in manifest]
    gold = [row["answers"][0]["name"] for _, row in manifest]
    sessions = [index.get(row["query"]) for _, row in manifest]
    resolved = [s for s in sessions if s]
    print(f"cross-session query collisions in pairs: {collisions}")
    print(f"resolved {len(resolved)}/{len(manifest)} manifest rows to a session")
    if len(resolved) != len(manifest):
        print("UNRESOLVED ROWS PRESENT -- the clustering below describes only the resolved subset")
    if not resolved:
        return 2

    clusters = defaultdict(list)
    for i, s in enumerate(sessions):
        if s:
            clusters[s].append(i)
    sizes = Counter(len(v) for v in clusters.values())
    kish = sum(len(v) ** 2 for v in clusters.values()) / len(resolved)
    print(f"distinct sessions: {len(clusters)}   largest: {max(sizes)} rows")
    print(f"cluster-size histogram (rows: sessions): {dict(sorted(sizes.items()))}")
    print(f"Kish mean cluster size experienced by a row: {kish:.2f}")
    print(f"  design effect = 1 + {kish - 1:.2f} * ICC; at ICC=0.1 effective n ~ "
          f"{len(resolved) / (1 + (kish - 1) * 0.1):.0f} of {len(resolved)}")

    config = json.loads(open(a.config).read())
    arms = {}
    for arm in config["arms"]:
        by = {r["sha1"]: r for _, r in read_jsonl(arm["path"])}
        arms[arm["name"]] = [by[h]["status"] == "ok" and by[h]["pred"] == g
                             for h, g in zip(ids, gold)]
    arms["training_majority"] = [g == a.baseline for g in gold]

    print(f"\n{'comparison':<44} {'naive p':<11} {'diff pp':>8}  {'95% cluster CI (pp)':<22} agrees?")
    for left, right in config.get("comparisons", []):
        if left not in arms or right not in arms:
            continue
        x, y = arms[left], arms[right]
        b = sum(p and not q for p, q in zip(x, y))
        c = sum(q and not p for p, q in zip(x, y))
        p = mcnemar(b, c)
        lo, hi = cluster_bootstrap(x, y, clusters, a.reps, a.seed)
        # The two disagree only when significance and the interval tell different stories.
        agrees = (p < 0.05) == (not lo <= 0 <= hi)
        print(f"{left + ' vs ' + right:<44} {p:<11.4g} {100 * (b - c) / len(x):>7.1f}  "
              f"[{100 * lo:>6.1f}, {100 * hi:>6.1f}]        {'yes' if agrees else 'NO'}")
    print("\nA cluster-robust interval is not a proof of independence; it is the same evidence"
          "\nread without assuming it. Sessions are resampled whole, so within-session"
          "\ncorrelation of any strength is carried through.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
