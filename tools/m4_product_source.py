#!/usr/bin/env python3
"""M0-only: attest exact M4 G2 artifact before original-Go product smoke.

This is read-only; component/product evidence is produced later by real Actions.
"""
import argparse
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
    else:
        need(event.get("event_type") == "push" and
             run_id == BOOTSTRAP_SCOPE_RUN,
             "main bootstrap may consume only pre-reviewed M4 G2")
    artifacts = api.get("actions/runs/" + str(run_id) + "/artifacts?per_page=100")
    chosen = [a for a in artifacts.get("artifacts", [])
              if a.get("name") == f"central-scope-{run_id}-{run['run_attempt']}"
              and not a.get("expired")]
    need(len(chosen) == 1, "missing/ambiguous current G2 receipt artifact")
    sha, receipt = verified_receipt(api.artifact_zip(chosen[0]["id"]), run, registry)
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
    p.add_argument("--output", default="out/m4-source.json")
    args=p.parse_args()
    need(os.environ.get("GITHUB_REPOSITORY") == REPO, "wrong repo")
    actual=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    need(actual == os.environ.get("GITHUB_SHA"), "main checkout differs")
    event_type=os.environ.get("GITHUB_EVENT_NAME")
    need(event_type in ("push","workflow_run"), "unsupported trigger")
    event=json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    event["event_type"]=event_type
    registry=json.loads(Path(".governance/registry.json").read_text())
    report=perform(API(os.environ.get("GH_TOKEN")),args.scope_run_id,
                   event,actual,registry)
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
