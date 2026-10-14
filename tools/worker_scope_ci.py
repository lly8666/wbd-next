#!/usr/bin/env python3
"""G2 role identity and per-commit worker write-scope attestation.

Must run on the actual GitHub Actions checkout. Authority is live main
registry, not workflow input or checked-out worker registry. Handoffs and
product qualification remain independent of scope/identity proof.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
# Running python tools/worker_scope_ci.py sets sys.path[0] to tools/.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import governance as g

G2_BASE = "83bd720368b9be68b3c4c94d7462d20cf4d796db"

def resolve_role(registry, ref_name, declared=""):
    roles = g.validate_registry(registry)
    active = [r for r in roles if r["state"]=="active" and r["branch"]==ref_name]
    g.need(len(active)==1, "workflow ref has no unique live active owner")
    role = active[0]
    g.need(not declared or role["id"]==declared,
           "dispatch declared worker role does not own this exact branch")
    return role

def verify_worker_commits(role, commits):
    """commits: SHA, paths, parents and is_main_ancestor; M0-root commits
    synced from main are exempt, worker-authored commits never are."""
    checked=0
    for item in commits:
        g.need(item.get("parents")==1, "worker merge commit requires M0 review")
        g.need(item.get("is_main_ancestor") is True or item.get("is_main_ancestor") is False,
               "worker ancestry unknown")
        if item["is_main_ancestor"]:continue
        paths=item["paths"]
        g.need(bool(paths) and all(g.path_ok(p) for p in paths),
               "empty, unsafe, or unreviewed worker commit")
        g.need(all(any(g.under(p,q) for q in role["allowed_paths"]) for p in paths),
               "worker write is outside assigned allowed_paths")
        checked += 1
    return checked

def main():
    repo=os.environ["GITHUB_REPOSITORY"]
    ref=os.environ["GITHUB_REF_NAME"]
    source=os.environ["GITHUB_SHA"]
    g.need(os.environ.get("GITHUB_REF")==f"refs/heads/{ref}",
           "role workflow may only validate a branch ref, not a tag or PR merge")
    actual=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    g.need(actual==source and bool(g.SHA.fullmatch(source)), "checkout SOURCE mismatch")
    api=g.GitHub(repo)
    control_sha=api.head("main")
    registry=api.file(".governance/registry.json",control_sha)
    role=resolve_role(registry,ref,os.environ.get("WBD_DECLARED_ROLE",""))
    cursor=g.read_json(".",role["cursor"])
    g.validate_cursor(cursor,role,registry["reservation_revision"])
    g.need(api.head(ref)==source, "branch ref changed while checking identity")
    g.need(g.read_json(".", ".governance/registry.json")["reservation_revision"]==
           registry["reservation_revision"], "stale branch registry revision")
    result={
        "schema_version":1,"result":"ROLE_SCOPE_PASS","role_id":role["id"],
        "branch":ref,"source_sha":source,"live_control_sha":control_sha,
        "reservation_revision":registry["reservation_revision"],
        "assignment_epoch":role["assignment_epoch"],
        "cursor_sequence":cursor["sequence"],"cursor_checkpoint":cursor["checkpoint_sha"],
        "scope_commits_checked":0,"main_integration_commits_exempt":0,
        "handoff":("BOOTSTRAP_RECOVERY_REQUIRED" if cursor["checkpoint_sha"] is None
                   else "NOT_DETERMINED_BY_SCOPE_ATTESTATION"),
        "product":"NOT_RUN",
    }
    if role["id"]!="M0":
        g.need(not role["global_writer"],"worker cannot be global integrator")
        compare=api.get(f"compare/{G2_BASE}...{source}?per_page=100")
        total=compare.get("total_commits",-1)
        g.need(compare.get("status") in {"ahead","identical"} and
               0<=total<=64 and len(compare.get("commits",[]))==total,
               "incomplete or diverged bounded G2 activation ancestry")
        edges=[]
        for commit in compare["commits"]:
            sha=commit["sha"]
            on_main=api.get(f"compare/{sha}...{control_sha}?per_page=1")
            g.need(on_main.get("status") in {"ahead","identical","diverged","behind"},
                   "main ancestor status indeterminate")
            ancestor=on_main["status"] in {"ahead","identical"}
            # Never fetch a worker change only from net diff: verify each commit.
            detail=g.commit_delta(api,sha,256)
            edges.append(dict(detail,is_main_ancestor=ancestor))
        result["scope_commits_checked"]=verify_worker_commits(role,edges)
        result["main_integration_commits_exempt"]=sum(x["is_main_ancestor"] for x in edges)
    else:
        g.need(ref=="main" and role["global_writer"], "M0 must own main")
    g.need(api.head("main")==control_sha and api.head(ref)==source,
           "control or source moved mid-audit")
    out=Path("out");out.mkdir(exist_ok=True)
    (out/"role-identity.json").write_text(json.dumps(result,indent=2)+"\n")
    with open(os.environ["GITHUB_ENV"],"a",encoding="utf-8") as f:
        f.write("WBD_ROLE_ID="+role["id"]+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    try:main()
    except (g.ContractError,KeyError,ValueError,TypeError) as e:
        print("ROLE_SCOPE_FAILED: "+str(e),file=sys.stderr)
        sys.exit(1)
