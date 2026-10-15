#!/usr/bin/env python3
"""Main-owned, read-only incremental scope audit. Never execute worker code.

Authority/checkpoints come from one immutable control snapshot. A result belongs
to the audited SOURCE, not whatever happens to be the branch tip at completion.
The old G2 checker remains available for historical evidence, not new audits.
"""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import governance as g


def ancestor(api, before, after):
    g.need(bool(g.SHA.fullmatch(before)) and bool(g.SHA.fullmatch(after)), "invalid SHA")
    return api.get(f"compare/{before}...{after}?per_page=1").get("status") in {"ahead", "identical"}


def authority(registry, role):
    """Task prose can change without revoking a writer; permission changes cannot."""
    return {"reservation_revision": registry["reservation_revision"], **{
        key: role[key] for key in ("id", "state", "branch", "assignment_epoch",
                                  "global_writer", "allowed_paths", "owned_semantics", "cursor")}}


def owner(registry, branch):
    roles = [r for r in g.validate_registry(registry) if r["branch"] == branch and r["state"] == "active"]
    g.need(len(roles) == 1, "branch has no unique active owner")
    return roles[0]


def complete_delta(compare, maximum):
    total = compare.get("total_commits")
    commits = compare.get("commits")
    g.need(compare.get("status") in {"ahead", "identical"}, "checkpoint is not an ancestor")
    g.need(type(total) is int and 0 <= total <= maximum,
           "delta budget exceeded: M0 must accept an intermediate scope receipt, not raise a lifetime limit")
    g.need(isinstance(commits, list) and len(commits) == total, "incomplete delta page")
    ids = [c.get("sha") for c in commits if isinstance(c, dict)]
    g.need(len(ids) == total and all(isinstance(s, str) and g.SHA.fullmatch(s) for s in ids)
           and len(set(ids)) == total, "invalid/duplicate delta commits")
    return ids


def audit(api, branch, source, control):
    registry = api.file(".governance/registry.json", control)
    role = owner(registry, branch)
    initial_authority = authority(registry, role)
    policy = api.file(".governance/policy.json", control)
    maximum = policy["max_delta_commits"]
    g.need(0 < maximum < 100, "delta budget must fit one complete API page")
    g.need(ancestor(api, source, api.head(branch)), "SOURCE is not on assigned branch")
    cursor = api.file(role["cursor"], source)
    g.validate_cursor(cursor, role, registry["reservation_revision"])
    checked, inherited, base = [], [], source
    if not role["global_writer"]:
        checkpoints = api.file(".governance/scope-checkpoints.json", control)
        g.need(checkpoints.get("schema_version") == 1, "unknown checkpoint schema")
        entry = checkpoints["roles"].get(role["id"])
        g.need(isinstance(entry, dict) and entry.get("authority") == initial_authority,
               "missing/stale main-approved scope checkpoint")
        base = entry["source_sha"]
        g.need(bool(entry.get("evidence_ref")), "checkpoint has no reviewed evidence")
        compare = api.get(f"compare/{base}...{source}?per_page={maximum + 1}")
        total_paths = 0
        for sha in complete_delta(compare, maximum):
            if ancestor(api, sha, control):
                inherited.append(sha)
                continue
            delta = g.commit_delta(api, sha, policy["max_paths_per_commit"])
            # Main imports are exempt above. A worker-created merge requires an
            # explicit main review/checkpoint; do not guess merge conflict intent.
            g.need(delta["parents"] == 1, "unreviewed worker merge: request M0 integration")
            paths = delta["paths"]
            total_paths += len(paths)
            g.need(total_paths <= policy["max_total_delta_paths"], "delta path budget exceeded")
            g.need(bool(paths) and all(g.path_ok(p) and any(g.under(p, prefix)
                   for prefix in role["allowed_paths"]) for p in paths), "worker path outside authority")
            checked.append(delta)
    final_control = api.head("main")
    final_registry = api.file(".governance/registry.json", final_control)
    g.need(authority(final_registry, owner(final_registry, branch)) == initial_authority,
           "writer authority changed during audit; retry against new assignment")
    final_head = api.head(branch)
    g.need(ancestor(api, source, final_head), "audited SOURCE was removed from assigned history")
    return {"schema_version": 1, "result": "ROLE_SCOPE_PASS", "role_id": role["id"],
            "branch": branch, "source_sha": source, "control_sha": control,
            "final_control_sha": final_control, "authority": initial_authority,
            "checkpoint_sha": base, "delta_commits": checked,
            "main_inherited_commits": inherited, "is_current_head": source == final_head,
            "final_branch_head": final_head, "cursor_sequence": cursor["sequence"],
            "handoff": "NOT_EVALUATED", "product": "NOT_RUN", "performance": "NOT_RUN",
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "checker_source": os.environ.get("GITHUB_SHA")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--control", help="Immutable main snapshot; candidate only in maintenance verification")
    parser.add_argument("--output", default="out/scope.json")
    args = parser.parse_args()
    api = g.GitHub(os.environ["GITHUB_REPOSITORY"])
    control = args.control or api.head("main")
    report = audit(api, args.branch, args.source, control)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (g.ContractError, KeyError, ValueError) as exc:
        print("SCOPE_AUDIT_FAILED: " + str(exc), file=sys.stderr)
        sys.exit(1)
