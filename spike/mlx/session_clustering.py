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


def query_to_sessions(pairs):
    """Replay the shared serializer over the extractor pairs -> {query: {sessions}}.

    Every candidate session is kept. An earlier version took the first writer and
    counted the rest as "collisions", which silently attributed an ambiguous query to
    whichever session happened to be read first (agent2, #729301). A query reachable
    from two sessions is not assignable, and the caller must treat it as such.
    """
    index = defaultdict(set)
    for _, pair in read_jsonl(pairs):
        if not pair.get("prior_actions"):
            continue
        try:
            query = serialize_query(pair.get("recent_user_request", ""), pair["prior_actions"])
        except ValueError:
            continue                                              # not a v1-renderable pair
        index[query].add(pair["session"])
    return index


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
    ap.add_argument("--training", default="data/corpus-studio/oracle-train.jsonl",
                    help="comparator is derived from this file's majority label, not supplied")
    ap.add_argument("--reps", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    index = query_to_sessions(a.pairs)
    manifest = read_jsonl(a.manifest)
    ids = [hashlib.sha1(raw.encode()).hexdigest() for raw, _ in manifest]
    gold = [row["answers"][0]["name"] for _, row in manifest]
    candidates = [index.get(row["query"], set()) for _, row in manifest]
    # Exactly one candidate = assignable. Zero = unresolved. Two or more = ambiguous.
    # Ambiguous and unresolved rows are BOTH excluded, and every number below is then
    # computed on the assigned subset only -- naive test and interval alike, so the two
    # always describe the same population.
    keep = [i for i, c in enumerate(candidates) if len(c) == 1]
    ambiguous = sum(len(c) > 1 for c in candidates)
    unresolved = sum(not c for c in candidates)
    ambiguous_in_corpus = sum(len(v) > 1 for v in index.values())
    print(f"queries in pairs reachable from >1 session: {ambiguous_in_corpus}")
    print(f"assigned {len(keep)}/{len(manifest)} manifest rows to exactly one session "
          f"({ambiguous} ambiguous, {unresolved} unresolved)")
    incomplete = bool(ambiguous or unresolved)
    if incomplete:
        print("INCOMPLETE: excluded rows are not a random subset; every figure below "
              "describes the ASSIGNED SUBSET, not the full manifest")
    if not keep:
        return 2

    clusters = defaultdict(list)
    for i in keep:
        clusters[next(iter(candidates[i]))].append(i)
    sizes = Counter(len(v) for v in clusters.values())
    kish = sum(len(v) ** 2 for v in clusters.values()) / len(keep)
    print(f"distinct sessions: {len(clusters)}   largest: {max(sizes)} rows")
    print(f"cluster-size histogram (rows: sessions): {dict(sorted(sizes.items()))}")
    print(f"Kish mean cluster size experienced by a row: {kish:.2f}")
    print(f"  design effect = 1 + {kish - 1:.2f} * ICC; at an ILLUSTRATIVE ICC=0.1, "
          f"effective n ~ {len(keep) / (1 + (kish - 1) * 0.1):.0f} of {len(keep)}")
    print("  ICC is assumed, not measured: cluster sizes alone do not measure outcome ICC.")

    config = json.loads(open(a.config).read())
    arms = {}
    for arm in config["arms"]:
        rows = [r for _, r in read_jsonl(arm["path"])]
        by = {r["sha1"]: r for r in rows}
        # Identity is re-checked here rather than assumed from the audit having passed:
        # this script is run standalone and must not score a mismatched arm silently.
        if len(by) != len(rows) or set(by) != set(ids):
            print(f"REFUSED: arm {arm['name']} does not align 1:1 with the manifest")
            return 1
        if any(by[h]["gold"] != g for h, g in zip(ids, gold)):
            print(f"REFUSED: arm {arm['name']} disagrees with the manifest gold")
            return 1
        arms[arm["name"]] = [by[h]["status"] == "ok" and by[h]["pred"] == g
                             for h, g in zip(ids, gold)]
    # Derive the comparator the way audit_round.py does, from training frequency, rather
    # than trusting a label passed on the command line.
    counts = Counter(row["answers"][0]["name"] for _, row in read_jsonl(a.training))
    baseline = min(counts, key=lambda label: (-counts[label], label))
    print(f"\ntraining-derived comparator: {baseline} ({counts[baseline]}/{sum(counts.values())})")
    arms["training_majority"] = [g == baseline for g in gold]

    scope = "ASSIGNED SUBSET" if incomplete else "full manifest"
    print(f"\nAll figures below are on the {scope} (n={len(keep)}).")
    print(f"{'comparison':<44} {'naive p':<11} {'diff pp':>8}  {'95% cluster CI (pp)':<22} agrees?")
    for left, right in config.get("comparisons", []):
        if left not in arms or right not in arms:
            continue
        # Restrict BOTH the exact test and the interval to the assigned rows.
        x = [arms[left][i] for i in keep]
        y = [arms[right][i] for i in keep]
        b = sum(p and not q for p, q in zip(x, y))
        c = sum(q and not p for p, q in zip(x, y))
        p = mcnemar(b, c)
        lo, hi = cluster_bootstrap(arms[left], arms[right], clusters, a.reps, a.seed)
        # The two disagree only when significance and the interval tell different stories.
        agrees = (p < 0.05) == (not lo <= 0 <= hi)
        print(f"{left + ' vs ' + right:<44} {p:<11.4g} {100 * (b - c) / len(x):>7.1f}  "
              f"[{100 * lo:>6.1f}, {100 * hi:>6.1f}]        {'yes' if agrees else 'NO'}")
    print("\nEXPLORATORY. This is not an enforced gate. A cluster-robust interval is not a"
          "\nproof of independence: sessions are resampled whole, so within-session"
          "\ncorrelation of any strength is carried through, but the bootstrap still assumes"
          "\nthe sampled sessions are mutually independent and represent the target"
          "\npopulation. Session IDs are path hashes (extract_claude_transcripts.py), so a"
          "\ncopied or branched source session can appear as two IDs. The correct reading is"
          "\n'these comparisons did not change under session resampling', NOT 'independence"
          "\nis established' and NOT 'no conclusion depends on independence'.")
    return 2 if incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
