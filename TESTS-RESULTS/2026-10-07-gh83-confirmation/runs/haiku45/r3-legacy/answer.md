```json
{
  "assessments": [
    {
      "id": "G01",
      "verdict": "SUPPORTED",
      "analysis": "PR15 is confirmed merged (2026-09-09T17:52:26Z) with changes limited to ROADMAP.md and PHASE-2-LABEL-TAXONOMY.md, both documentation files. The diff shows corrections to planning pointers and issue references, with no runtime code modified.",
      "next_step": "Verify the corrected issue pointers (#2, #13) are accurate and currently active in the issue tracker.",
      "evidence": ["G01-E1", "G01-E2", "G01-E3"]
    },
    {
      "id": "G02",
      "verdict": "SUPPORTED",
      "analysis": "PR16 modified taxonomy.py with significant behavioral changes: new wrapper detection logic, positional command analysis, subcommand handling, and regex pattern refinements. The test file and test results validate the changes. This is behavioral modification, not file renaming.",
      "next_step": "Cross-reference the changelog entries with test results (2026-09-09-taxonomy-positional-fix) to verify all labeled behavior shifts were validated.",
      "evidence": ["G02-E1", "G02-E2", "G02-E3"]
    },
    {
      "id": "G03",
      "verdict": "CONTRADICTED",
      "analysis": "G03-E1 explicitly states PR526 is open (state: open, merged: false, merged_at: null). The claim of merger is directly contradicted by the GitHub snapshot.",
      "next_step": "Confirm current merge status by checking GitHub to determine if PR526 has since merged or remains open.",
      "evidence": ["G03-E1"]
    },
    {
      "id": "G04",
      "verdict": "UNKNOWN",
      "analysis": "PR10's title references operational SOP steps and lessons-learned guidance. Changed files are documentation (SOP.md, AGENTS.md, ROUTER.md, CHANGELOG.md) with no runtime prediction-engine code visible. The evidence does not reveal whether a prediction engine exists or is being introduced.",
      "next_step": "Inspect the full diff of SOP.md and AGENTS.md to determine if a prediction engine is mentioned in documentation or if behavioral runtime code is embedded there.",
      "evidence": ["G04-E1", "G04-E2"]
    },
    {
      "id": "G05",
      "verdict": "CONTRADICTED",
      "analysis": "The required 'unit' check passed on commit 1111111, but the PR head is currently 2222222 (changed due to new code commit). The passing check does not bind to the current head. check_inventory_complete=true confirms no checks are missing from the record.",
      "next_step": "Retrieve the check status for head_sha 2222222 to determine if the unit check has been re-run or remains pending.",
      "evidence": ["G05-E1"]
    },
    {
      "id": "G06",
      "verdict": "CONTRADICTED",
      "analysis": "The policy requires reviews to bind exactly to current head SHA. The review (APPROVED, from 'reviewer') is bound to commit aaaaaaa, while the current head is bbbbbbb. They do not match, violating the stated approval rule.",
      "next_step": "Obtain a fresh review bound to bbbbbbb or dismiss this review and collect a new one that meets the policy.",
      "evidence": ["G06-E1"]
    },
    {
      "id": "G07",
      "verdict": "CONTRADICTED",
      "analysis": "Commit c1 enabled the cache (CACHE_ENABLED = True). Commit c2, the current tip, reverted this (CACHE_ENABLED = False). The current_file state is False, confirming the cache is disabled, not enabled.",
      "next_step": "If cache should be enabled, revert commit c2 or remove the revert commit from the branch.",
      "evidence": ["G07-E1"]
    },
    {
      "id": "G08",
      "verdict": "CONTRADICTED",
      "analysis": "Both main (L) and origin/main (R) share parent A. The comparison reports left_only: 1 and right_only: 1, indicating divergent histories. A fast-forward update requires origin/main to be a strict descendant of main; divergence rules it out.",
      "next_step": "Inspect the specific diverged commits (left_only and right_only) to decide whether a merge or rebase is required before fast-forwarding.",
      "evidence": ["G08-E1"]
    },
    {
      "id": "G09",
      "verdict": "CONTRADICTED",
      "analysis": "The commit message promises 'zero disables retries.' The call_contract states max_retries=0 means no retries (attempt starts at 0). The old code `attempt < 0` correctly returns False when max_retries=0. The new code `attempt <= 0` returns True when attempt=0, allowing at least one retry. The change contradicts the promise.",
      "next_step": "Revert to `attempt < max_retries` or verify the call contract and commit message are themselves incorrect.",
      "evidence": ["G09-E1"]
    },
    {
      "id": "G10",
      "verdict": "UNKNOWN",
      "analysis": "The PR changed 130 files but only 100 are displayed (pagination limit). The next page request failed with 503. Reviews were not fetched. Without visibility into 30 files and all reviews, merge blockers cannot be ruled out.",
      "next_step": "Retry pagination to retrieve the remaining 30 files and fetch review inventory before asserting absence of merge blockers.",
      "evidence": ["G10-E1"]
    },
    {
      "id": "G11",
      "verdict": "CONTRADICTED",
      "analysis": "PR_A changes producer output format (version 1→2, 'value'→'payload'). PR_B still expects version 1 and reads 'value'. Path overlap is absent, but the producer-consumer contract is broken. The deployment note confirms they must be deployed together, proving non-overlapping paths are not a sufficient compatibility criterion.",
      "next_step": "Verify both PRs are in the same release or coordinated deployment before merging either independently.",
      "evidence": ["G11-E1"]
    },
    {
      "id": "G12",
      "verdict": "CONTRADICTED",
      "analysis": "PR90 is merged but has zero GitHub deployment records. deployment_inventory_complete=true and the scope note states only GitHub records are observed. G12-E2 is marked untrusted_PR_description and is not authoritative. Based on trustworthy evidence, there is no deployment record.",
      "next_step": "Check external deployment systems or release notes to determine actual production status; GitHub records alone show no deployment.",
      "evidence": ["G12-E1"]
    }
  ],
  "limitations": [
    "Fixture data (G05–G12) are synthetic snapshots modeling specific claim scenarios; they do not represent real deployment state.",
    "Real GitHub snapshots (G01–G04) are frozen at 2026-09-09 and may not reflect state after that date; live queries would be needed to verify open PRs or deployments.",
    "G12-E2 is explicitly marked untrusted (prompt injection risk) and is not used for verdict; only G12-E1 informs assessment.",
    "External deployment systems and CI runners beyond those visible in supplied sources are not observed.",
    "File content diffs are partial (e.g., G02-E3 omitted_remainder=true); full behavioral scope cannot be verified from excerpts alone."
  ]
}
```