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

G2_ACTIVATION_MAX_COMMITS = 99  # per_page=100; full 99 must be visible, 100 rejected

def complete_g2_ancestry(compare):
    """Validate a COMPLETE non-diverged bounded immutable GitHub commit page."""
    total=compare.get("total_commits",-1)
    commits=compare.get("commits")
    g.need(compare.get("status") in {"ahead","identical"} and
           type(total) is int and 0<=total<=G2_ACTIVATION_MAX_COMMITS and
           isinstance(commits,list) and len(commits)==total,
           "incomplete or diverged bounded G2 activation ancestry")
    ids=[x.get("sha") for x in commits if isinstance(x,dict)]
    g.need(len(ids)==total and all(isinstance(v,str) and g.SHA.fullmatch(v) for v in ids)
           and len(set(ids))==total,
           "invalid or repeated G2 activation SHA")
    return commits

def audit_worker_history(api,role,source,control_sha):
    """Every commit's FULL path list, parent count and exceptional sync reviewed."""
    compare=api.get(f"compare/{G2_BASE}...{source}?per_page=100")
    edges=[]
    for commit in complete_g2_ancestry(compare):
        sha=commit["sha"]
        on_main=api.get(f"compare/{sha}...{control_sha}?per_page=1")
        g.need(on_main.get("status") in {"ahead","identical","diverged","behind"},
               "main ancestor status indeterminate")
        ancestor=on_main["status"] in {"ahead","identical"}
        detail=g.commit_delta(api,sha,256)
        sync={}
        if (role["id"]=="M3" and not ancestor and detail["parents"]==1
                and detail["paths"]==[M3_G2_REFRESH_PATH]):
            # The original historical sync is immutable. A SECOND one-shot
            # parent permits M3 to receive our current checker and full 98-page
            # continuation; arbitrary root changes still fail.
            item=api.get(f"commits/{sha}?per_page=1")
            parents=item.get("parents",[])
            g.need(len(parents)==1,"M3 tool sync must have one parent")
            if parents[0].get("sha")==M3_G2_SECOND_REFRESH_PARENT:
                sync=review_m3_g2_second_single_file_refresh(api,role,sha,control_sha)
            else:
                sync=review_m3_g2_single_file_refresh(api,role,sha,control_sha)
        if (role["id"]=="M2" and not ancestor and detail["parents"]==1
                and detail["paths"]==[M2_G2_REFRESH_PATH]):
            item=api.get(f"commits/{sha}?per_page=1")
            parents=item.get("parents",[])
            g.need(len(parents)==1,"M2 tool sync must have one parent")
            if parents[0].get("sha")==M2_G2_SECOND_REFRESH_PARENT:
                sync=review_m2_g2_second_single_file_refresh(api,role,sha,control_sha)
            else:
                sync=review_m2_g2_single_file_refresh(api,role,sha,control_sha)
        if detail["parents"]==2 and not ancestor:
            if role["id"]=="M3":
                sync_paths=review_m3_main_sync(api,role,sha,control_sha)
            elif role["id"]=="M2":
                sync_paths=review_m2_main_sync(api,role,sha,control_sha)
            else:
                g.need(False,"unreviewed role attempted two-parent merge")
            merged=api.get(f"commits/{sha}?per_page=1")
            sync={"approved_main_sync":True,
                  "first_parent":merged["parents"][0]["sha"],
                  "sync_paths":sync_paths}
        edges.append(dict(detail,is_main_ancestor=ancestor,**sync))
    return {
        "activation_commits":len(edges),
        "scope_commits_checked":verify_worker_commits(role,edges),
        "main_integration_commits_exempt":sum(x["is_main_ancestor"] for x in edges),
    }


def resolve_role(registry, ref_name, declared=""):
    roles = g.validate_registry(registry)
    active = [r for r in roles if r["state"]=="active" and r["branch"]==ref_name]
    g.need(len(active)==1, "workflow ref has no unique live active owner")
    role = active[0]
    g.need(not declared or role["id"]==declared,
           "dispatch declared worker role does not own this exact branch")
    return role

# One reviewed, non-force M3 incorporation of M0's pinned crypto-lock main.
# This is NOT blanket merge permission or authority from a worker-local file.
M3_APPROVED_PRE_SYNC_HEAD = "4776cc2bc17a78fc67e0898a11b439632037219a"

# M0 one-time, exact-source G2 checker refresh. NOT a generic tools/ grant.
# The M3 writer must create a SINGLE-PARENT commit directly on this parent,
# touching exactly one file, whose Git blob is byte-identical to live M0 main.
M3_G2_REFRESH_PARENT = "56907bdb4630d0a5a6a29c2d9cd029c89086566e"
M0_G2_REFRESH_ANCHOR = "c00356739359db90a864f0894d8cdd965b2df132"
M0_M3_HISTORICAL_TOOL_SOURCE = "404d37028a4c0d9949c379647dd1299609822cc7"
M0_M3_HISTORICAL_TOOL_BLOB = "1d27c4ec8d02035fc53d4e657f2cd7427373f8df"
M3_G2_REFRESH_PATH = "tools/worker_scope_ci.py"
# The 014 M3 worker H is already at 95 ancestry commits; one strict tool
# mirror + evidence S + cursor-only H require 98, within GitHub's full 100.
M3_G2_SECOND_REFRESH_PARENT = "5eafc5065c5ee1b0d6d67610a458e970e08f3d75"

# Exact one-time M2 root checker refresh after the old worker 64-commit
# history limit. The source-owned script remains the MAIN-owned version,
# still checking every commit and every changed path, bounded <=96/100.
M2_G2_REFRESH_PARENT = "018a07c880473a896d40c0d97a59250212f7dad8"
M2_G2_REFRESH_PATH = "tools/worker_scope_ci.py"
M0_M2_REFRESH_CONTROL_ANCHOR = "af8a8b40853845b6e876224d579bfb567df48e6c"
# Fix a retroactive policy bug: compare the original M2 mirror with the
# immutable main-owned reviewer SOURCE, never with a changing live main blob.
M0_M2_HISTORICAL_TOOL_SOURCE = "e9a4455dd4c20253a4e740e76bf7339fa4a6cc25"
M0_M2_HISTORICAL_TOOL_BLOB = "26983e630ab2fbf28466dac457923904aaa6be60"
# One new permitted worker-only checker transition off the exact blocked
# M2 evidence S. It does NOT grant general tools/, merges, or root CI.
M2_G2_SECOND_REFRESH_PARENT = "deff79215b6214aeafb28ede45d1aa28d118459b"
# M3 second checker mirror is already complete. Freeze its original approved
# source, too, before any further main tool change invalidates its history.
M0_M3_SECOND_TOOL_SOURCE = "940498ccb2f3834e4287813bb250ebfb97f507fb"
M0_M3_SECOND_TOOL_BLOB = "817934b16c6e088069ad9b4c265c93daacda7759"

def review_m2_g2_single_file_refresh(api,role,sha,control_sha):
    """Approve just one exact-parent byte-identical M0 checker sync on M2."""
    g.need(role["id"]=="M2","M2 checker refresh is M2-only")
    detail=g.commit_delta(api,sha,256)
    g.need(detail["parents"]==1 and detail["paths"]==[M2_G2_REFRESH_PATH],
           "M2 checker refresh must be sole path single-parent commit")
    item=api.get(f"commits/{sha}?per_page=1")
    parents=item.get("parents",[])
    g.need(len(parents)==1 and parents[0].get("sha")==M2_G2_REFRESH_PARENT,
           "M2 checker refresh requires exact frozen blocked worker H")
    for anchor_sha in (M0_M2_REFRESH_CONTROL_ANCHOR,M0_M2_HISTORICAL_TOOL_SOURCE):
        anchor=api.get(f"compare/{anchor_sha}...{control_sha}?per_page=1")
        g.need(anchor.get("status") in {"ahead","identical"},
               "historical M2 checker approval source is not on authoritative main")
    reviewed=api.get(f"contents/{M2_G2_REFRESH_PATH}?ref={M0_M2_HISTORICAL_TOOL_SOURCE}")
    actual=api.get(f"contents/{M2_G2_REFRESH_PATH}?ref={sha}")
    g.need(reviewed.get("type")=="file" and actual.get("type")=="file" and
           reviewed.get("sha")==M0_M2_HISTORICAL_TOOL_BLOB and
           reviewed.get("sha")==actual.get("sha"),
           "M2 old checker mirror does not match immutable main-approved blob")
    return {"approved_m2_g2_tool_refresh":True,
            "first_parent":M2_G2_REFRESH_PARENT,
            "sync_paths":[M2_G2_REFRESH_PATH]}


def review_m2_g2_second_single_file_refresh(api,role,sha,control_sha):
    """One exact new M2 tool sync: sole file/direct parent and main-owned blob.

    This is a bridge until M2 runs the corrected checker on its worker branch;
    no generic tool write or checkout-based scope bypass is authorized.
    """
    g.need(role["id"]=="M2","second M2 checker refresh is M2-only")
    detail=g.commit_delta(api,sha,256)
    g.need(detail["parents"]==1 and detail["paths"]==[M2_G2_REFRESH_PATH],
           "second M2 tool sync must be sole path in single-parent commit")
    item=api.get(f"commits/{sha}?per_page=1")
    parents=item.get("parents",[])
    g.need(len(parents)==1 and
           parents[0].get("sha")==M2_G2_SECOND_REFRESH_PARENT,
           "second M2 checker mirror must directly follow blocked evidence S")
    for anchor_sha in (M0_M2_REFRESH_CONTROL_ANCHOR,M0_M2_HISTORICAL_TOOL_SOURCE):
        anchor=api.get(f"compare/{anchor_sha}...{control_sha}?per_page=1")
        g.need(anchor.get("status") in {"ahead","identical"},
               "second M2 checker mirror missing immutable reviewed main ancestry")
    reviewed=api.get(f"contents/{M2_G2_REFRESH_PATH}?ref={control_sha}")
    actual=api.get(f"contents/{M2_G2_REFRESH_PATH}?ref={sha}")
    g.need(reviewed.get("type")=="file" and actual.get("type")=="file" and
           bool(reviewed.get("sha")) and reviewed.get("sha")==actual.get("sha"),
           "second M2 checker mirror must copy byte-identical current main tool")
    return {"approved_m2_g2_tool_refresh_v2":True,
            "first_parent":M2_G2_SECOND_REFRESH_PARENT,
            "sync_paths":[M2_G2_REFRESH_PATH]}

def review_m3_g2_single_file_refresh(api,role,sha,control_sha):
    """One reviewed M0-owned script mirror, anchored to one M3 first parent."""
    g.need(role["id"]=="M3","G2 checker refresh is M3-only")
    detail=g.commit_delta(api,sha,256)
    g.need(detail["parents"]==1 and detail["paths"]==[M3_G2_REFRESH_PATH],
           "M3 checker refresh must be sole path in a single-parent commit")
    commit=api.get(f"commits/{sha}?per_page=1")
    parents=commit.get("parents",[])
    g.need(len(parents)==1 and parents[0].get("sha")==M3_G2_REFRESH_PARENT,
           "M3 checker refresh requires exact verified previous worker HEAD")
    # M0's complete 67/67 proof is immutable and must be an ancestor of live
    # control. Preserve epoch/role/live-ref checks in caller.
    anchor=api.get(f"compare/{M0_G2_REFRESH_ANCHOR}...{control_sha}?per_page=1")
    g.need(anchor.get("status") in {"ahead","identical"},
           "M0 full history G2 approval not on current main")
    # M3 mirrored the main checker from the historical approved snapshot.
    # New M0-owned tools cannot retroactively invalidate that one-time sync.
    history=api.get(f"compare/{M0_M3_HISTORICAL_TOOL_SOURCE}...{control_sha}?per_page=1")
    g.need(history.get("status") in {"ahead","identical"},
           "M3 checker approval source not in immutable main history")
    reviewed=api.get(f"contents/{M3_G2_REFRESH_PATH}?ref={M0_M3_HISTORICAL_TOOL_SOURCE}")
    actual=api.get(f"contents/{M3_G2_REFRESH_PATH}?ref={sha}")
    g.need(reviewed.get("type")=="file" and actual.get("type")=="file" and
           reviewed.get("sha")==M0_M3_HISTORICAL_TOOL_BLOB and
           reviewed.get("sha")==actual.get("sha") and
           isinstance(reviewed.get("sha"),str) and reviewed["sha"]!= "",
           "M3 checker refresh is not byte-identical to main-owned checker")
    return {"approved_g2_tool_refresh":True,
            "first_parent":M3_G2_REFRESH_PARENT,
            "sync_paths":[M3_G2_REFRESH_PATH]}


def review_m3_g2_second_single_file_refresh(api,role,sha,control_sha):
    """Second one-shot exact parent + live M0 tool blob; never arbitrary tools/."""
    g.need(role["id"]=="M3","second M3 checker refresh is M3-only")
    detail=g.commit_delta(api,sha,256)
    g.need(detail["parents"]==1 and detail["paths"]==[M3_G2_REFRESH_PATH],
           "second M3 checker refresh must be single parent, sole root file")
    item=api.get(f"commits/{sha}?per_page=1")
    parents=item.get("parents",[])
    g.need(len(parents)==1 and
           parents[0].get("sha")==M3_G2_SECOND_REFRESH_PARENT,
           "second M3 checker refresh must follow exact blocked M3 H")
    for anchor_sha in (M0_G2_REFRESH_ANCHOR,M0_M3_HISTORICAL_TOOL_SOURCE,
                       M0_M3_SECOND_TOOL_SOURCE):
        anchor=api.get(f"compare/{anchor_sha}...{control_sha}?per_page=1")
        g.need(anchor.get("status") in {"ahead","identical"},
               "second M3 checker approval source not on immutable main history")
    reviewed=api.get(f"contents/{M3_G2_REFRESH_PATH}?ref={M0_M3_SECOND_TOOL_SOURCE}")
    actual=api.get(f"contents/{M3_G2_REFRESH_PATH}?ref={sha}")
    g.need(reviewed.get("type")=="file" and actual.get("type")=="file" and
           reviewed.get("sha")==M0_M3_SECOND_TOOL_BLOB and
           reviewed.get("sha")==actual.get("sha"),
           "second M3 checker mirror not byte-identical to immutable M0 source")
    return {"approved_m3_g2_tool_refresh_v2":True,
            "first_parent":M3_G2_SECOND_REFRESH_PARENT,
            "sync_paths":[M3_G2_REFRESH_PATH]}


M0_CRYPTO_LOCK_SOURCE = "1ae49bd644a4624db331c80d2dce6a8d181189e0"
# One reviewed M2 restoration to the source that contains the M0-authenticated
# Rust ingress AND the fixed historical G2 selector. Not generic permission.
M2_APPROVED_PRE_SYNC_HEAD = "2cd993a9675d38dcbe161bdebf093c0890734fdf"
M0_M2_INGRESS_SOURCE = "29ebcb19863602ae1fc059fa3524837e90944da9"
M2_SYNC_PROTECTED = frozenset({
    "Cargo.toml", "Cargo.lock", "crates/wbd-recovery/Cargo.toml",
})


def verify_worker_commits(role, commits):
    """Only original worker paths; one reviewed M3 main-sync merge is exceptional."""
    checked=0
    for item in commits:
        g.need(item.get("is_main_ancestor") is True or item.get("is_main_ancestor") is False,
               "worker ancestry unknown")
        if item["is_main_ancestor"]:
            # M0 commits on main are already under main-role validation.
            continue
        if item.get("approved_g2_tool_refresh") is True:
            g.need(role["id"]=="M3" and item.get("parents")==1 and
                   item.get("first_parent")==M3_G2_REFRESH_PARENT and
                   item.get("sync_paths")==[M3_G2_REFRESH_PATH] and
                   item.get("paths")==[M3_G2_REFRESH_PATH],
                   "M3 one-time checker refresh violated M0 pin")
            checked += 1
            continue
        if item.get("approved_m3_g2_tool_refresh_v2") is True:
            g.need(role["id"]=="M3" and item.get("parents")==1 and
                   item.get("first_parent")==M3_G2_SECOND_REFRESH_PARENT and
                   item.get("sync_paths")==[M3_G2_REFRESH_PATH] and
                   item.get("paths")==[M3_G2_REFRESH_PATH],
                   "second one-time M3 checker mirror violated M0 pin")
            checked += 1
            continue
        if item.get("approved_m2_g2_tool_refresh") is True:
            g.need(role["id"]=="M2" and item.get("parents")==1 and
                   item.get("first_parent")==M2_G2_REFRESH_PARENT and
                   item.get("sync_paths")==[M2_G2_REFRESH_PATH] and
                   item.get("paths")==[M2_G2_REFRESH_PATH],
                   "M2 exact checker refresh violated M0 policy pin")
        if item.get("approved_m2_g2_tool_refresh_v2") is True:
            g.need(role["id"]=="M2" and item.get("parents")==1 and
                   item.get("first_parent")==M2_G2_SECOND_REFRESH_PARENT and
                   item.get("sync_paths")==[M2_G2_REFRESH_PATH] and
                   item.get("paths")==[M2_G2_REFRESH_PATH],
                   "second M2 checker mirror violated M0 strict policy pin")
            checked += 1
            continue
        if item.get("parents")==2:
            approved_first = {
                "M3": M3_APPROVED_PRE_SYNC_HEAD,
                "M2": M2_APPROVED_PRE_SYNC_HEAD,
            }
            g.need(role["id"] in approved_first and
                   item.get("first_parent")==approved_first[role["id"]] and
                   item.get("approved_main_sync") is True,
                   "worker merge commit requires exact M0-approved first parent")
            # The checker puts sync_paths from a FULL main-parent->merge tree
            # comparison here. A first-parent-only delta cannot attest scope.
            paths=item.get("sync_paths", [])
            limit = 16 if role["id"]=="M2" else 32
            protected = (M2_SYNC_PROTECTED if role["id"]=="M2" else
                         {"Cargo.toml","Cargo.lock","crates/wbd-codec/Cargo.toml"})
            g.need(bool(paths) and len(paths)<=limit and
                   all(g.path_ok(p) and p not in protected and
                       any(g.under(p,q) for q in role["allowed_paths"])
                       for p in paths),
                   "reviewed merge regressed main-owned contracts or escaped role scope")
            checked += 1
            continue
        g.need(item.get("parents")==1, "worker merge commit requires M0 review")
        paths=item["paths"]
        g.need(bool(paths) and all(g.path_ok(p) for p in paths),
               "empty, unsafe, or unreviewed worker commit")
        g.need(all(any(g.under(p,q) for q in role["allowed_paths"]) for p in paths),
               "worker write is outside assigned allowed_paths")
        checked += 1
    return checked


def review_m3_main_sync(api, role, sha, control_sha):
    """Review exact immutable two-parent commit; fail closed on drift or truncation."""
    g.need(role["id"]=="M3", "only M3 has this approved root-dependency sync")
    detail=api.get(f"commits/{sha}?per_page=100")
    parents=detail.get("parents", [])
    g.need(len(parents)==2 and parents[0]["sha"]==M3_APPROVED_PRE_SYNC_HEAD,
           "M3 sync changed worker first parent or used >2 parents")
    main_parent=parents[1]["sha"]
    for before,after in ((main_parent,control_sha),(M0_CRYPTO_LOCK_SOURCE,main_parent)):
        compare=api.get(f"compare/{before}...{after}?per_page=1")
        g.need(compare.get("status") in {"ahead","identical"},
               "M3 sync second parent is not approved M0 main ancestry")
    net=api.get(f"compare/{main_parent}...{sha}?per_page=100")
    g.need(net.get("status")=="ahead" and
           0 < net.get("total_commits",0) <= 12 and
           len(net.get("commits",[]))==net.get("total_commits"),
           "M3 main-to-sync ancestry truncated or unexpected")
    files=net.get("files",[])
    g.need(0<len(files)<=32, "M3 main-to-sync file diff is missing or unbounded")
    paths={p for f in files for p in
           (f.get("filename"),f.get("previous_filename")) if p}
    g.need(0<len(paths)<=32, "M3 main-to-sync rename paths exceed approved bound")
    # A real merge must preserve the M0 root Cargo lock and the M0-owned codec
    # dependency declaration, not simply overwrite them with old worker copies.
    g.need(not paths.intersection({"Cargo.toml","Cargo.lock",
                                   "crates/wbd-codec/Cargo.toml"}),
           "M3 merge regressed locked shared crypto dependency manifests")
    g.need(all(g.path_ok(p) and
               any(g.under(p,q) for q in role["allowed_paths"])
               for p in paths), "M3 sync merged unauthorized tree changes")
    return sorted(paths)

def review_m2_main_sync(api, role, sha, control_sha):
    """Review ONE M2 current-base merge, preserving main contracts and ownership.

    G2 status is a scope proof, not an execution qualification. An authorized
    M2 writer still must safely merge without force and run native Actions.
    """
    g.need(role["id"]=="M2", "only M2 has this reviewed recovery sync")
    detail=api.get(f"commits/{sha}?per_page=100")
    parents=detail.get("parents", [])
    g.need(len(parents)==2 and
           parents[0]["sha"]==M2_APPROVED_PRE_SYNC_HEAD,
           "M2 merge must retain exact original M2 HEAD as first parent")
    main_parent=parents[1]["sha"]
    for before,after in ((main_parent,control_sha),(M0_M2_INGRESS_SOURCE,main_parent)):
        compare=api.get(f"compare/{before}...{after}?per_page=1")
        g.need(compare.get("status") in {"ahead","identical"},
               "M2 merge second parent lacks current approved main ingress/CI source")
    # Unlike conventional merge-commit commit_delta, this covers M2's
    # resulting tree versus actual M0 main, including rename old/new paths.
    net=api.get(f"compare/{main_parent}...{sha}?per_page=100")
    g.need(net.get("status")=="ahead" and
           0<net.get("total_commits",0)<=12 and
           len(net.get("commits",[]))==net["total_commits"],
           "M2 main-to-sync ancestry incomplete, diverged, or unbounded")
    files=net.get("files",[])
    g.need(0<len(files)<=16, "M2 main-to-sync tree difference unbounded")
    paths={p for f in files for p in
           (f.get("filename"),f.get("previous_filename")) if p}
    g.need(0<len(paths)<=16, "M2 sync rename paths missing or unbounded")
    g.need(not paths.intersection(M2_SYNC_PROTECTED),
           "M2 sync must not revert root Cargo.lock/dependency manifests")
    g.need(all(g.path_ok(p) and
               any(g.under(p,q) for q in role["allowed_paths"])
               for p in paths), "M2 sync includes unauthorised main-owned paths")
    return sorted(paths)


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
        verified=audit_worker_history(api,role,source,control_sha)
        result["scope_commits_checked"]=verified["scope_commits_checked"]
        result["main_integration_commits_exempt"]=verified["main_integration_commits_exempt"]
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
