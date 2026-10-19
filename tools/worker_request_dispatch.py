#!/usr/bin/env python3
"""M0 only: exact audited M1/M3 request -> frozen v5 workflow_dispatch.

Never executes worker code, checks out workers, edits cursors, mints tokens,
or marks a component PASS. Runs only from a reviewed main checkout.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import governance as g
from tools import worker_component_validation as entry

ROLES = ("M1", "M3")
CONTROL_REF = "qualification/worker-ci-v5"
CONTROL_SHA = "484861e5aff4eb9098a25a42f1522e19716f09e8"
TARGET_WORKFLOW = ".github/workflows/worker-component-validation.yml"
SCOPE_WORKFLOW = "scope-audit.yml"
MAX_PAGES = 25
REQUEST = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,90}\Z")


def require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


class API:
    def __init__(self, repo, token):
        require(repo == entry.REPO, "wrong repository")
        require(bool(token), "missing GitHub token")
        self.repo, self.token = repo, token

    def request(self, path, data=None):
        require(not path.startswith("http"), "only repository API paths")
        url = "https://api.github.com/repos/" + self.repo + "/" + path
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url, headers=headers, method="POST" if data is not None else "GET",
            data=json.dumps(data).encode() if data is not None else None,
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.read()

    def get(self, path):
        return json.loads(self.request(path))

    def post(self, path, data):
        return self.request(path, data)

    def blob(self, path, ref):
        data = self.get("contents/" + urllib.parse.quote(path, safe="/") +
                        "?ref=" + urllib.parse.quote(ref, safe=""))
        require(data.get("type") == "file" and data.get("encoding") == "base64",
                "request/config is not a plain Git file")
        return base64.b64decode(data["content"], validate=False)

    def artifact_zip(self, artifact_id):
        require(type(artifact_id) is int and artifact_id > 0, "invalid artifact ID")
        # gh api downloads the artifact as binary; no external URL construction
        # or user-supplied download URLs. Requires only actions:read.
        process = subprocess.run(
            ["gh", "api", f"repos/{self.repo}/actions/artifacts/{artifact_id}/zip"],
            env={**os.environ, "GH_TOKEN": self.token},
            capture_output=True, check=True,
        )
        return process.stdout


def scope_receipt(zipped, role, head, run):
    require(len(zipped) <= 2_000_000, "oversized scope artifact")
    with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
        members = archive.namelist()
        require(members == [f"scope-{role}.json"] or
                members == [f"out/scope-{role}.json"],
                "scope artifact must contain exactly its role receipt")
        receipt = json.loads(archive.read(members[0]))
    require(receipt.get("result") == "ROLE_SCOPE_PASS" and
            receipt.get("role_id") == role and
            receipt.get("source_sha") == head and
            receipt.get("branch") == run["worker_branch"] and
            receipt.get("scope_standard") == "G2_ACTIVATION_COMPLETE_PAGINATED_V1" and
            receipt.get("is_current_head") is True and
            receipt.get("run_id") == str(run["id"]) and
            receipt.get("run_attempt") == str(run["run_attempt"]) and
            bool(entry.SHA.fullmatch(receipt.get("control_sha", ""))) and
            receipt.get("final_control_sha") == receipt.get("control_sha") and
            receipt.get("authority", {}).get("id") == role and
            receipt["authority"].get("state") == "active" and
            receipt["authority"].get("assignment_epoch") == run["epoch"] and
            receipt["authority"].get("reservation_revision") == run["revision"],
            "non-matching central G2 scope SOURCE/authority/run receipt")
    return receipt


def list_runs(api, workflow, suffix=""):
    # Scan all available matching history; fail closed rather than assume
    # "not in latest 100" means no duplicate.
    path = "actions/workflows/" + workflow + "/runs?per_page=100"
    if suffix:
        path += "&" + suffix
    out = []
    for page in range(1, MAX_PAGES + 1):
        payload = api.get(path + "&page=" + str(page))
        runs = payload["workflow_runs"]
        require(isinstance(runs, list), "bad Actions workflow run list")
        out.extend(runs)
        if len(runs) < 100:
            return out
    raise ValueError("Actions run list exceeded bounded pages: duplicate state unknown")


def latest_scope(api, role, branch, head, epoch, revision):
    display = f"scope|{branch}|{head}"
    runs = list_runs(api, SCOPE_WORKFLOW, "event=workflow_run")
    candidates = [r for r in runs
                  if r.get("display_title") == display
                  and r.get("status") == "completed"
                  and r.get("conclusion") == "success"
                  and r.get("event") == "workflow_run"
                  and r.get("head_branch") == "main"
                  and r.get("run_attempt", 0) >= 1]
    for r in sorted(candidates, key=lambda j: j["id"], reverse=True):
        artifacts = api.get(f"actions/runs/{r['id']}/artifacts?per_page=100")
        name = f"central-scope-{r['id']}-{r['run_attempt']}"
        matches = [a for a in artifacts.get("artifacts", [])
                   if a.get("name") == name and not a.get("expired")]
        if len(matches) != 1:
            continue
        context = dict(r, worker_branch=branch, epoch=epoch, revision=revision)
        try:
            receipt = scope_receipt(api.artifact_zip(matches[0]["id"]),
                                    role, head, context)
        except (ValueError, KeyError, zipfile.BadZipFile):
            continue
        return {"scope_run_id": r["id"], "scope_attempt": r["run_attempt"],
                "scope_artifact_id": matches[0]["id"],
                "source_sha": head, "receipt": receipt}
    return None


def request_identity(api, role, head, path):
    encoded = urllib.parse.quote(path, safe="")
    changes = api.get(f"commits?sha={head}&path={encoded}&per_page=1")
    require(len(changes) == 1, "no exact original request commit")
    sha = changes[0]["sha"]
    require(entry.SHA.fullmatch(sha), "invalid request I SHA")
    commit = api.get(f"commits/{sha}?per_page=100")
    require(len(commit.get("parents", [])) == 1, "request I cannot be merge commit")
    changed = commit.get("files", [])
    require(any(item["filename"] == path and
                item["status"] in ("added", "modified")
                for item in changed), "request I did not create/change this exact file")
    require(api.blob(path, sha) == api.blob(path, head),
            "worker request content changed since intent I")
    return sha


def prior_dispatch(api, role, rid, stage):
    title = f"{role}|{rid}|{stage}|{CONTROL_SHA}"
    runs = list_runs(
        api, "worker-component-validation.yml",
        "event=workflow_dispatch&branch=" + urllib.parse.quote(CONTROL_REF, safe=""),
    )
    for run in runs:
        if run.get("display_title") == title and
                run.get("event") == "workflow_dispatch" and
                run.get("head_sha") == CONTROL_SHA:
            return run["id"]
    return None


def plan(api, main_sha):
    require(entry.SHA.fullmatch(main_sha), "not a main SOURCE")
    require(api.get("branches/main")["commit"]["sha"] == main_sha,
            "main moved before dispatch planning")
    require(api.get("branches/" + CONTROL_REF)["commit"]["sha"] == CONTROL_SHA,
            "frozen v5 ref changed: do not dispatch")
    registry = json.loads(api.blob(".governance/registry.json", main_sha))
    g.validate_registry(registry)
    decisions = []
    for role in ROLES:
        matches = [r for r in registry["roles"] if r["id"] == role and
                   r["state"] == "active" and not r["global_writer"]]
        require(len(matches) == 1, f"{role} not uniquely assigned")
        worker = matches[0]
        branch = worker["branch"]
        head = api.get("branches/" + branch)["commit"]["sha"]
        require(entry.SHA.fullmatch(head), "bad worker branch SHA")
        attest = latest_scope(api, role, branch, head, worker["assignment_epoch"],
                              registry["reservation_revision"])
        base = f".governance/workstreams/{role}/requests"
        files = api.get("contents/" + base + "?ref=" + head)
        require(isinstance(files, list), "worker request directory unavailable")
        requests = [f for f in files
                    if f.get("type") == "file" and
                    f.get("name", "").endswith(".json") and
                    REQUEST.fullmatch(f["name"][:-5])]
        require(len(requests) <= 64, "request directory cap exceeded")
        for file in sorted(requests, key=lambda x: x["name"]):
            path = f"{base}/{file['name']}"
            data = json.loads(api.blob(path, head))
            rid = file["name"][:-5]
            if data.get("status") != "PLANNED" or
                    data.get("dispatch_ref") != CONTROL_REF or
                    data.get("control_sha") != CONTROL_SHA or
                    data.get("role_id") != role:
                continue  # Historical/other-control requests are not candidates.
            stage = ("prepare" if data.get("kind") == "functional" else
                     "paired" if data.get("kind") == "performance" else None)
            require(stage is not None, "candidate requests only support two stages")
            require(attest is not None, f"{role} has no exact current G2 PASS for {head}")
            request_ref = request_identity(api, role, head, path)
            raw_config = api.blob(entry.SUITES[role][1], data["harness_sha"])
            data["_request_path"] = path
            # Identical validation as the v5 authorize job, before using
            # an actions:write token. This is an extra gate, not a bypass.
            entry.validate_context(data, role, stage, CONTROL_REF, CONTROL_SHA,
                                   registry, head, request_ref, raw_config)
            for ref in (request_ref, data["source_sha"], data["baseline_sha"],
                        data["harness_sha"]):
                compare = api.get(f"compare/{ref}...{head}?per_page=1")
                require(compare["status"] in ("ahead", "identical"),
                        f"{role} candidate SOURCE/I not reachable from current HEAD")
            existing = prior_dispatch(api, role, rid, stage)
            decision = {"role":role, "request_id":rid, "stage":stage,
                        "request_ref":request_ref, "worker_head":head,
                        "control_ref":CONTROL_REF, "control_sha":CONTROL_SHA,
                        "scope_run_id":attest["scope_run_id"],
                        "scope_artifact_id":attest["scope_artifact_id"],
                        "prior_run_id":existing,
                        "result":"SKIP_ALREADY_DISPATCHED" if existing else "READY"}
            decisions.append(decision)
    require(api.get("branches/main")["commit"]["sha"] == main_sha,
            "main changed during authorizing request batch")
    return decisions


def execute(api, decisions):
    for entry_ in decisions:
        if entry_["result"] != "READY":
            continue
        # Re-read duplicates immediately before write. Dispatch is idempotent
        # by unique role/request/stage/control tuple. A failed execution
        # is never silently retried; worker must create a new request ID.
        prev = prior_dispatch(api, entry_["role"], entry_["request_id"],
                              entry_["stage"])
        if prev is not None:
            entry_["result"] = "SKIP_ALREADY_DISPATCHED"
            entry_["prior_run_id"] = prev
            continue
        payload = {"ref": CONTROL_REF,
                   "inputs": {"role_id":entry_["role"],
                              "stage":entry_["stage"],
                              "request_id":entry_["request_id"],
                              "request_ref":entry_["request_ref"]}}
        api.post("actions/workflows/worker-component-validation.yml/dispatches",
                 payload)
        entry_["result"] = "DISPATCH_ACCEPTED_NOT_QUALIFIED"


def main():
    require(os.environ.get("GITHUB_REPOSITORY") == entry.REPO,
            "not requested repository")
    expected = os.environ["GITHUB_SHA"]
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    require(actual == expected, "runner checkout differs from main source")
    require(os.environ.get("GITHUB_REF") == "refs/heads/main" or
            os.environ.get("GITHUB_EVENT_NAME") == "workflow_run",
            "dispatcher only from main or central scope completion")
    api = API(entry.REPO, os.environ.get("GH_TOKEN"))
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_run":
        trigger = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        run = trigger.get("workflow_run", {})
        require(run.get("name") == "Central worker scope audit" and
                run.get("conclusion") == "success" and
                run.get("event") == "workflow_run" and
                run.get("head_branch") == "main" and
                run.get("head_repository", {}).get("full_name") == entry.REPO,
                "untrusted or unsuccessful central-scope event")
    decisions = plan(api, expected)
    execute(api, decisions)
    Path("out").mkdir(exist_ok=True)
    Path("out/worker-dispatch.json").write_text(json.dumps({
        "schema_version":1,"dispatcher_source_sha":expected,
        "control_ref":CONTROL_REF,"control_sha":CONTROL_SHA,
        "event":os.environ.get("GITHUB_EVENT_NAME"),
        "decisions":decisions,"product":"NOT_RUN","performance":"NOT_RUN",
    }, indent=2)+"\n")
    print(json.dumps(decisions,indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, g.ContractError, urllib.error.HTTPError,
            subprocess.CalledProcessError, zipfile.BadZipFile) as e:
        print("WORKER_DISPATCH_DENIED: "+str(e),file=sys.stderr)
        sys.exit(1)
