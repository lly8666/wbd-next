#!/usr/bin/env python3
"""Main-owned central scope audit using the SAME bounded, fully-paginated G2 standard.

All history/parent/path decisions reuse tools.worker_scope_ci on the frozen
main checkout. Never load worker-side executable files. Source/authority and
handoff metadata are checked separately; no second 64-commit delta gate.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import governance as g
from tools import worker_scope_ci as g2


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


def check_role_metadata(api, role, source, cursor):
    """Validate worker data using main code, never load executable worker tools."""
    for ref in cursor["evidence_refs"]:
        evidence = api.file(ref, source)
        g.need(evidence.get("schema_version") == 1 and
               evidence.get("source_sha") == cursor["last_tested_source"], "cursor evidence SOURCE mismatch")
        if not cursor["unverified"]:
            # A scoped component receipt may use PASS_SCOPED_*; this is a
            # verified SOURCE/artifact status, not a product-level PASS.
            result = evidence.get("result")
            g.need(isinstance(result, str) and
                   (result == "PASS" or result.startswith("PASS_SCOPED_")) and
                   evidence.get("artifact_verified") is True,
                   "verified cursor lacks a source-matched scoped PASS artifact")
    for ref in cursor["context_refs"]:
        item = api.get(f"contents/{quote(ref, safe='/')}?ref={source}")
        g.need(item.get("type") == "file", "missing cursor context reference")
    for ref in cursor["open_requests"]:
        if ref.endswith(".md"):
            # Existing G2 coordination notes are not Actions dispatch intents.
            item = api.get(f"contents/{quote(ref, safe='/')}?ref={source}")
            g.need(item.get("type") == "file", "missing coordination request")
            continue
        request = api.file(ref, source)
        g.validate_request(request)
        g.need(request["role_id"] == role["id"] and request["assignment_epoch"] == role["assignment_epoch"],
               "open intent belongs to another role/epoch")


def audit(api, branch, source, control):
    registry = api.file(".governance/registry.json", control)
    role = owner(registry, branch)
    initial_authority = authority(registry, role)
    # Admission/history/merge/rename/path and complete pagination checks use
    # the identical main-owned G2 code as successful worker Governance. Do
    # not create a second checkpoint window, single-page budget or special
    # exception list here: they drift and reject legitimate worker histories.
    g.need(ancestor(api, source, api.head(branch)), "SOURCE is not on assigned branch")
    cursor = api.file(role["cursor"], source)
    g.validate_cursor(cursor, role, registry["reservation_revision"])
    check_role_metadata(api, role, source, cursor)
    history = {"activation_commits": 0, "scope_commits_checked": 0,
               "main_integration_commits_exempt": 0}
    if not role["global_writer"]:
        history = g2.audit_worker_history(api, role, source, control)
    final_control = api.head("main")
    final_registry = api.file(".governance/registry.json", final_control)
    g.need(authority(final_registry, owner(final_registry, branch)) == initial_authority,
           "writer authority changed during audit; retry against new assignment")
    final_head = api.head(branch)
    g.need(ancestor(api, source, final_head), "audited SOURCE was removed from assigned history")
    return {"schema_version": 1, "result": "ROLE_SCOPE_PASS", "role_id": role["id"],
            "branch": branch, "source_sha": source, "control_sha": control,
            "final_control_sha": final_control, "authority": initial_authority,
            "scope_standard": "G2_ACTIVATION_COMPLETE_PAGINATED_V1",
            "activation_base_sha": g2.G2_BASE,
            "activation_max_commits": g2.G2_ACTIVATION_MAX_COMMITS,
            "activation_page_size": g2.G2_ACTIVATION_PAGE_SIZE,
            "activation_commits": history["activation_commits"],
            "scope_commits_checked": history["scope_commits_checked"],
            "main_integration_commits_exempt": history["main_integration_commits_exempt"],
            "is_current_head": source == final_head,
            "final_branch_head": final_head, "cursor_sequence": cursor["sequence"],
            "role_metadata": "PASS_CURRENT_TOOL_READS_WORKER_DATA_ONLY",
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
