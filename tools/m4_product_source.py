#!/usr/bin/env python3
"""M0-only: attest exact M4 G2 artifact before original-Go product smoke.

This is read-only; component/product evidence is produced later by real Actions.
"""
import argparse
import base64
import hashlib
import re
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import governance as g

REPO = "lly8666/wbd-next"
BRANCH = "work/m4-r1-platform"
SCOPE_PATH = ".github/workflows/scope-audit.yml"
SCOPE_WORKFLOW_ID = 385257385
BOOTSTRAP_SCOPE_RUN = 39219843238
M4_CONTROL_REF = "qualification/m4-product-windows-v1"
LEGACY_SOURCE = "a7a82db31fe736ffedee330795a3234d358f1984"

def need(condition, reason):
    if not condition:
        raise ValueError(reason)

def trusted_event(event, run):
    trigger = event.get("workflow_run", {})
    return (trigger.get("id") == run.get("id") and
            trigger.get("workflow_id") == SCOPE_WORKFLOW_ID and
            trigger.get("path") == SCOPE_PATH and
            trigger.get("status") == "completed" and
            trigger.get("conclusion") == "success" and
            trigger.get("event") == "workflow_run" and
            trigger.get("head_branch") == "main" and
            (trigger.get("head_repository") or {}).get("full_name") == REPO)

def verified_receipt(raw, run, registry):
    need(len(raw) <= 2_000_000, "oversized M4 scope artifact")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        need(names in (["scope-M4.json"], ["out/scope-M4.json"]),
             "not exact M4 scope artifact")
        data = json.loads(z.read(names[0]))
    roles = [r for r in g.validate_registry(registry)
             if r["id"] == "M4" and r["state"] == "active" and
             r["branch"] == BRANCH and not r["global_writer"]]
    need(len(roles) == 1, "M4 authority unavailable")
    role = roles[0]
    sha = data.get("source_sha", "")
    auth = data.get("authority") or {}
    need(isinstance(sha, str) and bool(g.SHA.fullmatch(sha)),
         "invalid worker SOURCE")
    need(data.get("result") == "ROLE_SCOPE_PASS" and
         data.get("scope_standard") == "G2_ACTIVATION_COMPLETE_PAGINATED_V1" and
         data.get("branch") == BRANCH and data.get("role_id") == "M4" and
         data.get("is_current_head") is True and
         data.get("run_id") == str(run["id"]) and
         data.get("run_attempt") == str(run["run_attempt"]) and
         data.get("control_sha") == run["head_sha"] and
         data.get("final_control_sha") and
         run.get("display_title") == "scope|" + BRANCH + "|" + sha,
         "G2 scope SOURCE/control/run mismatch")
    for key in ("id", "branch", "state", "assignment_epoch", "allowed_paths",
                "owned_semantics", "cursor", "global_writer"):
        need(auth.get(key) == role.get(key), "M4 role authority changed: " + key)
    need(auth.get("reservation_revision") == registry["reservation_revision"],
         "M4 reservation revision changed")
    return sha, data

def verify_manual_request(api, attested, registry, current_main, request_id, request_ref, candidate_sha, current_run_id):
    """Only M4-owned one-file immutable I + fresh central G2 may launch Windows.
    
    Candidate SOURCE must precede I and be reachable from current G2 HEAD.
    Request file is never auto-authentication and never expands worker scope.
    """
    need(isinstance(request_id,str) and bool(g.IDENT.fullmatch(request_id))
         and request_id.startswith("M4-016-"), "invalid M4-016 request name")
    for name,value in (("request_ref",request_ref),("candidate",candidate_sha),
                       ("main control",current_main)):
        need(isinstance(value,str) and bool(g.SHA.fullmatch(value)),
             "invalid exact SHA: "+name)
    need(current_run_id is None or
         (type(current_run_id) is int and current_run_id>0),
         "bad actual Actions run")
    path=f".governance/workstreams/M4/requests/{request_id}.json"
    commit=api.get("commits/"+request_ref)
    parents=commit.get("parents",[])
    need(commit.get("sha")==request_ref and len(parents)==1 and
         len(commit.get("files",[]))==1 and
         commit["files"][0].get("filename")==path and
         commit["files"][0].get("status")=="added",
         "M4 request I must add only exact one request JSON")
    sha=attested["source_sha"]
    for ancestor,descendant in ((candidate_sha,request_ref),
                                (request_ref,sha)):
        compare=api.get(f"compare/{ancestor}...{descendant}?per_page=1")
        need(compare.get("status") in ("ahead","identical"),
             "request SOURCE/I is not in current attested M4 ancestry")
    branch=api.get("branches/"+BRANCH)
    need(branch.get("commit",{}).get("sha")==sha,
         "G2 must attest current exact M4 HEAD for manual dispatch")
    def read_owned_text(file_path,at):
        obj=api.get("contents/"+file_path+"?ref="+at)
        need(obj.get("type")=="file" and obj.get("encoding")=="base64"
             and isinstance(obj.get("content"),str), "not an immutable Git file")
        return base64.b64decode(obj["content"],validate=False)
    raw=read_owned_text(path,request_ref)
    latest=read_owned_text(path,sha)
    need(raw==latest and len(raw)<100_000, "M4 request I edited after creation")
    req=json.loads(raw)
    g.validate_request(req)
    role=next(r for r in g.validate_registry(registry) if r["id"]=="M4")
    for key,expected in {
        "request_id":request_id,"role_id":"M4",
        "task_id":role["assigned_task"],"assignment_epoch":role["assignment_epoch"],
        "reservation_revision":registry["reservation_revision"],
        "kind":"functional","status":"PLANNED",
        "workflow":".github/workflows/m0-m4-product-assembly.yml",
        "dispatch_ref":M4_CONTROL_REF,"control_sha":current_main,
        "source_sha":candidate_sha,"harness_sha":candidate_sha,
        "baseline_sha":LEGACY_SOURCE,
        "scenario":"windows-native-product-runtime-016",
        "seed":1,"samples":1,"measurement_jobs":1,
    }.items():
        need(req.get(key)==expected, "M4 request changed authority: "+key)
    need(req.get("target")=="windows-amd64" and
         req.get("config_path")=="r0/go_overlay/assembly/manifest.json",
         "M4 Windows target/manifest not pinned")
    raw_config=read_owned_text(req["config_path"],candidate_sha)
    need(hashlib.sha256(raw_config).hexdigest()==req["config_sha256"],
         "M4 candidate original-Go overlay manifest hash drift")
    if current_run_id is not None:
        runs=api.get("actions/workflows/m0-m4-product-assembly.yml/runs?event=workflow_dispatch&branch="+
                     M4_CONTROL_REF.replace("/","%2F")+"&per_page=100")
        need(runs.get("total_count",101)<=100, "M4 manual request scan unbounded")
        matching=[r for r in runs.get("workflow_runs",[])
                  if r.get("event")=="workflow_dispatch" and
                     r.get("display_title","").startswith(f"M4|{request_id}|windows-amd64|")]
        need(len(matching)==1 and matching[0].get("id")==current_run_id
             and matching[0].get("head_sha")==current_main,
             "duplicate or unrecognized manual M4 Actions request")
    report=dict(attested)
    report.update(source_sha=candidate_sha,
                  attested_worker_sha=sha,
                  request_id=request_id,request_ref=request_ref,
                  request_config_sha256=req["config_sha256"],
                  control_sha=current_main,
                  workflow=".github/workflows/m0-m4-product-assembly.yml",
                  target="windows-amd64",
                  dispatch_validation="IMMUTABLE_I_CURRENT_G2_MANIFEST_EXACT_SINGLE_RUN",
                  product="NOT_RUN_UNTIL_WINDOWS_JOB")
    return report

def perform(api, run_id, event, current_main, registry):
    need(isinstance(run_id, int) and run_id > 0, "bad scope run ID")
    need(bool(g.SHA.fullmatch(current_main)), "bad actual main checkout SOURCE")
    run = api.get("actions/runs/" + str(run_id))
    need(run.get("id") == run_id and run.get("workflow_id") == SCOPE_WORKFLOW_ID and
         run.get("path") == SCOPE_PATH and run.get("head_branch") == "main" and
         run.get("event") == "workflow_run" and
         run.get("status") == "completed" and run.get("conclusion") == "success" and
         (run.get("head_repository") or {}).get("full_name") == REPO and
         isinstance(run.get("run_attempt"), int) and run["run_attempt"] > 0,
         "not an actual successful central G2 run")
    if event.get("event_type") == "workflow_run":
        need(trusted_event(event, run), "invalid central workflow event")
    elif event.get("event_type") == "push":
        need(run_id == BOOTSTRAP_SCOPE_RUN,
             "main bootstrap may consume only pre-reviewed M4 G2")
    else:
        need(event.get("event_type")=="workflow_dispatch",
             "unsupported G2 consumer event")
    artifacts = api.get("actions/runs/" + str(run_id) + "/artifacts?per_page=100")
    chosen = [a for a in artifacts.get("artifacts", [])
              if a.get("name") == f"central-scope-{run_id}-{run['run_attempt']}"
              and not a.get("expired")]
    need(len(chosen) == 1, "missing/ambiguous current G2 receipt artifact")
    sha, receipt = verified_receipt(api.artifact_zip(chosen[0]["id"]), run, registry)
    if event.get("event_type")=="workflow_dispatch":
        # Frozen M4 control remains usable while M0 independently advances
        # main. The central G2 must have been run AFTER this immutable
        # control was frozen, with the same live M4 authority.
        latest=api.get("branches/main").get("commit",{}).get("sha","")
        need(bool(g.SHA.fullmatch(latest)), "live main unavailable")
        for origin,end in ((current_main,run["head_sha"]),
                           (current_main,receipt["final_control_sha"]),
                           (run["head_sha"],latest),
                           (receipt["final_control_sha"],latest)):
            need(api.get(f"compare/{origin}...{end}?per_page=1").get("status")
                 in ("ahead","identical"), "stale/diverged central G2 vs frozen M4 control")
        live_blob=api.get("contents/.governance/registry.json?ref=main")
        need(live_blob.get("type")=="file" and live_blob.get("encoding")=="base64",
             "current main registry not immutable file")
        live=json.loads(base64.b64decode(live_blob["content"]))
        current_roles=g.validate_registry(live)
        local=next(r for r in g.validate_registry(registry) if r["id"]=="M4")
        current=next(r for r in current_roles if r["id"]=="M4")
        need(live["reservation_revision"]==registry["reservation_revision"] and
             all(local.get(k)==current.get(k) for k in
                 ("id","branch","state","assignment_epoch","allowed_paths",
                  "owned_semantics","assigned_task","global_writer")),
             "M4 control retired by current main authorization")
    else:
        need(api.get("compare/" + run["head_sha"] + "..." + current_main +
                     "?per_page=1").get("status") in ("ahead", "identical"),
             "G2 main checker SOURCE not in current main ancestry")
        need(api.get("compare/" + receipt["final_control_sha"] + "..." +
                     current_main + "?per_page=1").get("status") in ("ahead", "identical"),
             "G2 final main authority not in current ancestry")
    branch = api.get("branches/" + BRANCH)
    current = (branch.get("commit") or {}).get("sha", "")
    need(isinstance(current, str) and bool(g.SHA.fullmatch(current)),
         "M4 branch head unavailable")
    need(api.get("compare/" + sha + "..." + current +
                 "?per_page=1").get("status") in ("ahead", "identical"),
         "attested M4 SOURCE no longer reachable")
    return {"schema_version":1, "role_id":"M4",
            "source_sha":sha, "legacy_source":LEGACY_SOURCE,
            "main_control_sha":current_main, "g2_run_id":run_id,
            "g2_attempt":run["run_attempt"],
            "g2_artifact_id":chosen[0]["id"], "scope_result":"ROLE_SCOPE_PASS",
            "qualification":"SCOPE_ONLY_PRODUCT_NOT_RUN", "product":"NOT_RUN"}

class API:
    def __init__(self, token):
        need(bool(token), "missing Actions read token")
        self.token = token
    def get(self, endpoint):
        need(not endpoint.startswith("http"), "only repository API endpoints")
        req = urllib.request.Request(
            "https://api.github.com/repos/" + REPO + "/" + endpoint,
            headers={"Authorization":"Bearer " + self.token,
                     "Accept":"application/vnd.github+json",
                     "X-GitHub-Api-Version":"2022-11-28"})
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    def artifact_zip(self, artifact_id):
        need(type(artifact_id) is int and artifact_id > 0,
             "invalid artifact ID")
        return subprocess.check_output(
            ["gh", "api", f"repos/{REPO}/actions/artifacts/{artifact_id}/zip"],
            env={**os.environ, "GH_TOKEN":self.token})

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--scope-run-id", type=int, required=True)
    p.add_argument("--request-id")
    p.add_argument("--request-ref")
    p.add_argument("--worker-source-sha")
    p.add_argument("--control-sha")
    p.add_argument("--output", default="out/m4-source.json")
    args=p.parse_args()
    need(os.environ.get("GITHUB_REPOSITORY") == REPO, "wrong repo")
    actual=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    need(actual == os.environ.get("GITHUB_SHA"), "main checkout differs")
    event_type=os.environ.get("GITHUB_EVENT_NAME")
    need(event_type in ("push","workflow_run","workflow_dispatch"), "unsupported trigger")
    if event_type=="workflow_dispatch":
        need(os.environ.get("GITHUB_REF_NAME")==M4_CONTROL_REF and
             args.control_sha==actual, "manual dispatch must pin frozen M4 control")
        need(all((args.request_id,args.request_ref,args.worker_source_sha,args.control_sha)),
             "manual dispatch missing exact request/source/control")
    else:
        need(not any((args.request_id,args.request_ref,args.worker_source_sha,args.control_sha)),
             "manual-only inputs on unsolicited event")
    event=json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    event["event_type"]=event_type
    registry=json.loads(Path(".governance/registry.json").read_text())
    api=API(os.environ.get("GH_TOKEN"))
    report=perform(api,args.scope_run_id,event,actual,registry)
    if event_type=="workflow_dispatch":
        report=verify_manual_request(
            api,report,registry,actual,args.request_id,args.request_ref,
            args.worker_source_sha,int(os.environ["GITHUB_RUN_ID"]))
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    with open(os.environ["GITHUB_OUTPUT"],"a") as stream:
        stream.write("source_sha="+report["source_sha"]+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    try:main()
    except (ValueError, KeyError, g.ContractError, zipfile.BadZipFile,
            subprocess.CalledProcessError) as exc:
        print("M4_PRODUCT_SCOPE_DENIED: " + str(exc),file=sys.stderr)
        sys.exit(1)
