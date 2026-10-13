"""Small, read-only governance checks. Product implementation is deliberately absent."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
PROGRESS = {"planned", "in_progress", "partial", "verifying", "ready_for_integration",
            "blocked", "paused", "superseded"}
RESULTS = {"PASS", "FAIL", "INVALID", "CAPACITY_LIMITED", "UNSUPPORTED", "NOT_RUN", "INCONCLUSIVE"}
PROTECTED = ("AGENTS.md", "PROJECT_CHARTER.md", ".github/", ".governance/project.json",
             ".governance/policy.json", ".governance/registry.json", "tools/", "tests/")


class ContractError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise ContractError(message)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def text(value):
    return isinstance(value, str) and bool(value.strip())


def path_ok(value):
    return (isinstance(value, str) and bool(value) and "\\" not in value
            and ":" not in value and not value.startswith("/")
            and ".." not in value.split("/") and "." not in value.split("/")
            and "//" not in value and not value.startswith("-"))


def under(path, prefix):
    return prefix == "*" or path == prefix or (prefix.endswith("/") and path.startswith(prefix))


def overlap(a, b):
    return under(a, b) or under(b, a)


def read_json(root, path):
    need(path_ok(path), f"unsafe path: {path!r}")
    root = Path(root).resolve()
    target = root / path
    need(target.resolve().is_relative_to(root), f"path escapes repository: {path}")
    need(target.is_file() and not target.is_symlink(), f"missing/nonregular file: {path}")
    value = json.loads(target.read_text(encoding="utf-8"))
    need(isinstance(value, dict), f"object required: {path}")
    need(value.get("schema_version") == 1, f"unknown schema: {path}")
    return value


def validate_registry(registry):
    need(integer(registry.get("reservation_revision"), 1), "invalid reservation revision")
    roles = registry.get("roles")
    need(isinstance(roles, list) and 0 < len(roles) <= 16, "invalid roles")
    ids, semantics, branches, active = set(), set(), set(), []
    for role in roles:
        rid = role.get("id", "")
        need(bool(IDENT.fullmatch(rid)) and rid not in ids, "duplicate/invalid role")
        ids.add(rid)
        need(role.get("state") in {"active", "reserved", "integrated", "closed"}, "invalid role state")
        need(type(role.get("global_writer")) is bool, "global_writer must be boolean")
        need(path_ok(role.get("prompt")), "invalid prompt path")
        need(text(role.get("goal")) and text(role.get("done_when")), "missing bounded role goal")
        prefixes = role.get("allowed_paths")
        need(isinstance(prefixes, list), "allowed_paths must be list")
        need(all(p == "*" or path_ok(p) for p in prefixes), "unsafe write prefix")
        if not role["global_writer"]:
            need("*" not in prefixes, "worker cannot own wildcard")
            need(not any(overlap(p, q) for p in prefixes for q in PROTECTED), "worker claims control plane")
        if role["state"] != "active":
            continue
        need(integer(role.get("assignment_epoch"), 1), "active role needs epoch")
        need(path_ok(role.get("branch")), "active role needs safe branch")
        need(role["branch"] not in branches, "active branches must be single-writer")
        branches.add(role["branch"])
        need(role.get("cursor") == f".governance/workstreams/{rid}/cursor.json", "wrong cursor owner")
        need(bool(prefixes), "active role needs scope")
        owned = role.get("owned_semantics")
        need(isinstance(owned, list) and all(text(s) for s in owned), "invalid semantic ownership")
        need(not semantics.intersection(owned) and len(owned) == len(set(owned)), "duplicate semantic owner")
        semantics.update(owned)
        active.append(role)
    need(sum(r["global_writer"] for r in active) <= 1, "only one serial integrator")
    workers = [r for r in active if not r["global_writer"]]
    for i, role in enumerate(workers):
        for other in workers[i + 1:]:
            need(not any(overlap(a, b) for a in role["allowed_paths"] for b in other["allowed_paths"]),
                 "overlapping worker scopes")
    return roles


def validate_cursor(cursor, role, revision, max_refs=8):
    need(cursor.get("role_id") == role["id"], "cursor role mismatch")
    need(cursor.get("branch") == role["branch"], "cursor branch mismatch")
    need(cursor.get("assignment_epoch") == role["assignment_epoch"], "stale writer epoch")
    need(cursor.get("reservation_revision") == revision, "stale reservation revision")
    need(integer(cursor.get("sequence")), "invalid cursor sequence")
    checkpoint = cursor.get("checkpoint_sha")
    need((checkpoint is None and cursor["sequence"] == 0) or
         (isinstance(checkpoint, str) and SHA.fullmatch(checkpoint)), "invalid checkpoint SHA")
    need(cursor.get("progress") in PROGRESS, "invalid progress state")
    for key in ("task_id", "current_task", "why_now", "done_when", "next_action"):
        need(text(cursor.get(key)), f"missing {key}")
    need(type(cursor.get("unverified")) is bool, "unverified must be explicit boolean")
    tested = cursor.get("last_tested_source")
    need(tested is None or (isinstance(tested, str) and SHA.fullmatch(tested)), "invalid tested SOURCE")
    for key in ("evidence_refs", "open_requests", "context_refs"):
        refs = cursor.get(key)
        need(isinstance(refs, list) and len(refs) <= max_refs, f"unbounded {key}")
        need(len(refs) == len(set(refs)) and all(path_ok(p) for p in refs), f"invalid {key}")
    if not cursor["unverified"]:
        need(tested is not None and bool(cursor["evidence_refs"]), "verified claim lacks exact evidence")
    if cursor["unverified"] or cursor["progress"] == "partial":
        need(text(cursor.get("partial_summary")), "partial/unverified needs explanation")
    need(cursor["progress"] != "ready_for_integration" or not cursor["unverified"],
         "unverified work cannot be ready for integration")


def validate_request(request):
    for key in ("request_id", "role_id", "task_id"):
        need(isinstance(request.get(key), str) and IDENT.fullmatch(request[key]), f"invalid {key}")
    for key in ("source_sha", "harness_sha"):
        need(isinstance(request.get(key), str) and SHA.fullmatch(request[key]), f"invalid {key}")
    need(isinstance(request.get("config_sha256"), str) and DIGEST.fullmatch(request["config_sha256"]),
         "invalid config digest")
    need(request.get("kind") in {"governance", "functional", "performance"}, "invalid request kind")
    need(request.get("status") in {"PLANNED", "DISPATCHED", "RECORDED"}, "invalid request status")
    need(integer(request.get("assignment_epoch"), 1) and integer(request.get("reservation_revision"), 1),
         "request must identify the assignment")
    need(path_ok(request.get("dispatch_ref")), "request needs a frozen dispatch ref")
    need(text(request.get("scenario")) and integer(request.get("seed")), "one scenario and seed required")
    need(path_ok(request.get("workflow")) and request["workflow"].startswith(".github/workflows/"),
         "invalid workflow")
    need(integer(request.get("samples"), 1) and integer(request.get("measurement_jobs"), 1), "invalid samples/jobs")
    if request["kind"] == "performance":
        mode = request.get("mode", "single")
        need(mode in {"single", "paired_ab"}, "unknown performance mode")
        need(request["measurement_jobs"] == 1, "one measurement job/VM per Action")
        if mode == "single":
            need(request["samples"] == 1 and not request.get("legs"), "single mode needs one sample")
        else:
            legs = request.get("legs")
            need(request["samples"] == 2 and isinstance(legs, list) and len(legs) == 2,
                 "paired_ab needs exactly two sequential legs")
            need(all(isinstance(leg, dict) for leg in legs), "invalid paired legs")
            need([leg.get("label") for leg in legs] in (["A", "B"], ["B", "A"]), "order must be AB or BA")
            for leg in legs:
                need(isinstance(leg.get("source_sha"), str) and SHA.fullmatch(leg["source_sha"]), "invalid leg SOURCE")
                need(isinstance(leg.get("build_manifest_sha256"), str)
                     and DIGEST.fullmatch(leg["build_manifest_sha256"]), "missing pinned leg build")
            need(legs[0]["source_sha"] != legs[1]["source_sha"], "comparison needs distinct sources")
            need(next(leg for leg in legs if leg["label"] == "B")["source_sha"] == request["source_sha"],
                 "request SOURCE must identify candidate B")
    previous = request.get("supersedes_request")
    need(previous is None or (isinstance(previous, str) and IDENT.fullmatch(previous)
                             and previous != request["request_id"]), "invalid supersession")


def verify_receipt(request, receipt, run, jobs=None):
    """Match exact provenance; a self-authored JSON PASS alone is never sufficient."""
    validate_request(request)
    for key in ("request_id", "role_id", "kind", "source_sha", "harness_sha", "config_sha256", "scenario", "seed"):
        need(receipt.get(key) == request[key], f"receipt mismatch: {key}")
    need(receipt.get("result") in RESULTS, "invalid receipt result")
    need(integer(receipt.get("run_id"), 1) and integer(receipt.get("run_attempt"), 1), "missing run identity")
    need(run.get("id") == receipt["run_id"] and run.get("run_attempt") == receipt["run_attempt"], "wrong run/attempt")
    need(run.get("head_sha") == receipt["harness_sha"], "wrong workflow checkout")
    need(run.get("path", "").split("@")[0] == request["workflow"], "wrong workflow identity")
    if receipt["result"] == "PASS":
        need(run.get("status") == "completed" and run.get("conclusion") == "success", "unfinished/failed run is not PASS")
        need(receipt.get("artifact_verified") is True, "PASS requires artifact verification")
    if request["kind"] == "performance" and request.get("mode") == "paired_ab":
        need(receipt.get("mode") == "paired_ab", "receipt lost paired identity")
        legs = receipt.get("legs")
        need(isinstance(legs, list) and len(legs) == 2 and all(isinstance(leg, dict) for leg in legs),
             "missing observed paired legs")
        need(isinstance(jobs, list), "paired receipt requires independently fetched GitHub jobs")
        need(integer(legs[0].get("job_id"), 1) and legs[0].get("job_id") == legs[1].get("job_id"),
             "comparison must run on one GitHub job")
        matched = [job for job in jobs if job.get("id") == legs[0]["job_id"]]
        need(len(matched) == 1 and matched[0].get("run_id") == run["id"]
             and matched[0].get("run_attempt") == run["run_attempt"], "job does not belong to this run/attempt")
        previous_end = None
        for expected, actual in zip(request["legs"], legs):
            for key in ("label", "source_sha", "build_manifest_sha256"):
                need(actual.get(key) == expected[key], f"paired leg mismatch: {key}")
            for key in ("config_sha256", "scenario", "seed", "harness_sha"):
                need(actual.get(key) == request[key], f"paired leg changed common {key}")
            start, end = actual.get("start_monotonic_ns"), actual.get("end_monotonic_ns")
            need(integer(start) and integer(end) and start < end, "invalid leg interval")
            need(previous_end is None or previous_end <= start, "paired legs overlap or reverse time")
            previous_end = end
            need(actual.get("result") in RESULTS, "unknown leg result")
            if receipt["result"] == "PASS":
                need(actual["result"] == "PASS", "failed/unrun leg cannot become paired PASS")
        if receipt["result"] == "PASS":
            need(matched[0].get("status") == "completed" and matched[0].get("conclusion") == "success",
                 "paired measurement job is not successful")
    return True


def discover_request_runs(request, runs, complete=True):
    need(complete, "run query incomplete; do not redispatch")
    prefix = f"{request['role_id']}|{request['request_id']}|"
    matches = [r for r in runs if r.get("display_title", "").startswith(prefix)
               and r.get("path", "").split("@")[0] == request["workflow"]]
    need(len(matches) <= 1, "duplicate request executions; preserve both results")
    return matches


def classify_continuity(role, revision, cursor, commits, *, ancestry=True, complete=True,
                        max_commits=64, max_paths=256, max_total=1024, previous_sequence=None):
    try:
        validate_cursor(cursor, role, revision)
        need(role["state"] == "active", "role is not assigned")
        need(ancestry and complete, "ancestry/query incomplete or divergent")
        need(len(commits) <= max_commits, "commit audit bound exceeded")
        if cursor["checkpoint_sha"] is None:
            return {"state": "RECOVERY_REQUIRED", "reason": "bootstrap needs first S/H checkpoint"}
        if previous_sequence is not None and commits:
            need(cursor["sequence"] > previous_sequence, "cursor sequence did not advance beyond checkpoint")
        substantive, paths_seen = [], 0
        for commit in commits:
            need(commit.get("parents", 1) == 1, "unacknowledged merge needs explicit review")
            paths = commit.get("paths")
            need(isinstance(paths, list) and len(paths) <= max_paths, "path audit bound exceeded")
            paths_seen += len(paths)
            need(paths_seen <= max_total, "total path audit bound exceeded")
            need(all(path_ok(p) for p in paths), "unsafe path in delta")
            need(all(any(under(p, prefix) for prefix in role["allowed_paths"]) for p in paths), "out-of-scope delta")
            if any(p != role["cursor"] for p in paths):
                substantive.append(commit["sha"])
        if substantive:
            return {"state": "RECOVERY_REQUIRED", "reason": "unacknowledged substantive commits", "commits": substantive}
        return {"state": "CLEAN", "reason": "only cursor acknowledgements after checkpoint; not a product PASS"}
    except (ContractError, KeyError, TypeError) as exc:
        return {"state": "BLOCKED", "reason": str(exc)}


def validate_repo(root):
    root = Path(root)
    project = read_json(root, ".governance/project.json")
    policy = read_json(root, ".governance/policy.json")
    registry = read_json(root, ".governance/registry.json")
    roles = validate_registry(registry)
    need(project.get("repository") == "lly8666/wbd-next", "wrong project repository")
    need(project.get("product_qualification") == "NOT_RUN" or project.get("product_design") != "PENDING_DISCUSSION",
         "pending product design cannot claim qualification")
    hot = project.get("hot_read_set")
    need(isinstance(hot, list) and len(hot) <= policy["max_hot_files"], "invalid hot read set")
    need(len(hot) == len(set(hot)), "duplicate hot file")
    all_ids = set()
    for role in roles:
        need((root / role["prompt"]).is_file(), "missing fixed prompt")
        if role["state"] != "active":
            continue
        cursor = read_json(root, role["cursor"])
        validate_cursor(cursor, role, registry["reservation_revision"], policy["max_cursor_refs"])
        need((root / role["cursor"]).stat().st_size <= policy["max_cursor_bytes"], "cursor too large")
        read_set = list(dict.fromkeys(hot + [role["prompt"], role["cursor"]]))
        need(len(read_set) <= policy["max_hot_files"], "combined hot file budget exceeded")
        total = 0
        for path in read_set:
            need(path_ok(path) and (root / path).is_file(), "missing/unsafe hot file")
            total += (root / path).stat().st_size
        need(total <= policy["max_hot_bytes"], f"combined hot byte budget exceeded: {total}")
        for key in ("evidence_refs", "open_requests", "context_refs"):
            for path in cursor[key]:
                need((root / path).is_file(), f"missing cursor reference: {path}")
        for path in cursor["evidence_refs"]:
            evidence = read_json(root, path)
            need(evidence.get("source_sha") == cursor["last_tested_source"], "evidence is for a different SOURCE")
            if not cursor["unverified"]:
                need(evidence.get("result") == "PASS" and evidence.get("artifact_verified") is True,
                     "verified cursor lacks reviewed PASS evidence")
        requests = list((root / f".governance/workstreams/{role['id']}/requests").glob("*.json"))
        need(len(requests) <= policy["max_live_requests_per_role"], "live request budget exceeded")
        for path in requests:
            request = read_json(root, path.relative_to(root).as_posix())
            validate_request(request)
            need(request["role_id"] == role["id"], "request wrong owner")
            need(request["request_id"] not in all_ids, "duplicate request ID")
            all_ids.add(request["request_id"])
    if project["product_design"] == "PENDING_DISCUSSION" or project.get("product_implementation") == "NOT_STARTED":
        for prefix in policy["product_paths_pending_design"]:
            need(not (root / prefix).exists(), f"product development not assigned: {prefix}")
    return {"result": "PASS", "scope": "governance_structure_only", "roles": len(roles),
            "product": "NOT_RUN", "physical": "NOT_RUN"}


class GitHub:
    def __init__(self, repository):
        need(bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)), "invalid repository")
        self.repository = repository

    def get(self, suffix):
        url = f"https://api.github.com/repos/{self.repository}/{suffix}"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "wbd-next-governance"}
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise ContractError(f"GitHub read failed HTTP {exc.code}: {suffix.split('?')[0]}") from None

    def file(self, path, ref):
        need(path_ok(path) and SHA.fullmatch(ref), "unsafe remote file/ref")
        data = self.get(f"contents/{urllib.parse.quote(path, safe='/')}?ref={ref}")
        need(data.get("type") == "file" and data.get("encoding") == "base64", "remote file missing or too large")
        return json.loads(base64.b64decode(data["content"]).decode("utf-8"))

    def head(self, branch):
        need(path_ok(branch), "unsafe branch")
        return self.get(f"git/ref/heads/{urllib.parse.quote(branch, safe='/')}")["object"]["sha"]


def commit_delta(api, sha, limit):
    """GitHub caps per_page at 100; never mistake the first page for all paths."""
    files, parents = [], None
    for page in range(1, limit // 100 + 2):
        detail = api.get(f"commits/{sha}?per_page=100&page={page}")
        chunk = detail.get("files", [])
        need(isinstance(chunk, list), "invalid commit files response")
        if parents is None:
            parents = len(detail["parents"])
        files.extend(chunk)
        need(len(files) <= limit, "remote file pagination exceeds bound")
        if len(chunk) < 100:
            paths = {f["filename"] for f in files}
            paths.update(f["previous_filename"] for f in files if f.get("previous_filename"))
            need(len(paths) <= limit, "rename paths exceed audit bound")
            return {"sha": sha, "paths": sorted(paths), "parents": parents}
    raise ContractError("commit file query incomplete")


def audit_remote(api, role_id):
    control = api.head("main")
    registry = api.file(".governance/registry.json", control)
    policy = api.file(".governance/policy.json", control)
    roles = validate_registry(registry)
    selected = [r for r in roles if r["id"] == role_id]
    need(len(selected) == 1 and selected[0]["state"] == "active", "role is not active")
    role = selected[0]
    head = api.head(role["branch"])
    cursor = api.file(role["cursor"], head)
    validate_cursor(cursor, role, registry["reservation_revision"])
    checkpoint = cursor["checkpoint_sha"]
    edges = []
    previous_sequence = None
    if checkpoint:
        prior = api.file(role["cursor"], checkpoint)
        previous_sequence = prior.get("sequence")
        need(integer(previous_sequence), "checkpoint lacks cursor sequence")
        compare = api.get(f"compare/{checkpoint}...{head}?per_page={policy['max_delta_commits'] + 1}")
        need(compare.get("status") in {"ahead", "identical"}, "checkpoint not an ancestor")
        need(compare.get("total_commits", 0) <= policy["max_delta_commits"], "remote delta exceeds bound")
        need(len(compare.get("commits", [])) == compare.get("total_commits", 0), "incomplete commit pagination")
        for commit in compare.get("commits", []):
            edges.append(commit_delta(api, commit["sha"], policy["max_paths_per_commit"]))
    result = classify_continuity(role, registry["reservation_revision"], cursor, edges,
                                 max_commits=policy["max_delta_commits"], max_paths=policy["max_paths_per_commit"],
                                 max_total=policy["max_total_delta_paths"], previous_sequence=previous_sequence)
    pending = []
    for path in cursor["open_requests"]:
        request = api.file(path, head)
        validate_request(request)
        workflow = urllib.parse.quote(PurePosixPath(request["workflow"]).name, safe="")
        query = api.get(f"actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=100")
        runs = discover_request_runs(request, query.get("workflow_runs", []), complete=query.get("total_count", 0) <= 100)
        pending.append({"request_id": request["request_id"], "runs": [r["id"] for r in runs],
                        "action": "READ_EXISTING_RUN" if runs else "VERIFY_NOT_DISPATCHED"})
    if pending and result["state"] == "CLEAN":
        result = {"state": "RECOVERY_REQUIRED", "reason": "open external intents require reconciliation"}
    need(api.head("main") == control and api.head(role["branch"]) == head, "remote ref moved during audit; refresh")
    result.update({"role": role_id, "control_sha": control, "worker_sha": head,
                   "checkpoint_sha": checkpoint, "open_requests": pending,
                   "qualification": "NOT_EVALUATED_BY_CONTINUITY_AUDIT"})
    return result


def make_receipt(result, output):
    need(result in {"PASS", "FAIL"}, "invalid observed checks result")
    source = os.environ.get("GITHUB_SHA", "")
    need(bool(SHA.fullmatch(source)) and os.environ.get("GITHUB_ACTIONS") == "true", "receipt must be generated in Actions")
    run_id = int(os.environ["GITHUB_RUN_ID"])
    request_id = os.environ.get("WBD_REQUEST_ID") or f"event-{run_id}"
    role = os.environ.get("WBD_ROLE_ID") or "M0"
    need(bool(IDENT.fullmatch(request_id)) and bool(IDENT.fullmatch(role)), "invalid request identity")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config = {"scenario": "governance-selftest", "product": False}
    receipt = {"schema_version": 1, "role_id": role, "request_id": request_id,
               "kind": "governance", "scope": "governance", "scenario": config["scenario"], "seed": 0,
               "source_sha": source, "harness_sha": source,
               "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
               "run_id": run_id, "run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
               "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"), "job": os.environ.get("GITHUB_JOB"),
               "request_ref": os.environ.get("WBD_REQUEST_REF") or None,
               "result": result, "artifact_verified": False,
               "note": "Step observation only: verify final GitHub conclusion and downloaded manifest before promotion.",
               "environment": {"os": os.environ.get("RUNNER_OS"), "arch": os.environ.get("RUNNER_ARCH"),
                               "python": sys.version.split()[0]},
               "product": "NOT_RUN", "physical": "NOT_RUN", "fresh_chat_drill": "NOT_RUN"}
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "config.json").write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
    files = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            raw = path.read_bytes()
            files.append({"path": path.relative_to(output).as_posix(), "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    manifest = {"schema_version": 1, "source_sha": source, "run_id": run_id,
                "run_attempt": receipt["run_attempt"], "files": files}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--root", default=".")
    audit = sub.add_parser("audit")
    audit.add_argument("--role", required=True)
    audit.add_argument("--repository", default="lly8666/wbd-next")
    receipt = sub.add_parser("receipt")
    receipt.add_argument("--result", choices=["PASS", "FAIL"], required=True)
    receipt.add_argument("--output", default="out")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            result = validate_repo(args.root)
        elif args.command == "audit":
            result = audit_remote(GitHub(args.repository), args.role)
        else:
            result = make_receipt(args.result, args.output)
    except (ContractError, KeyError, ValueError, TypeError, OSError) as exc:
        result = {"state": "BLOCKED", "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"CLEAN": 0, "RECOVERY_REQUIRED": 1, "BLOCKED": 2}.get(result.get("state"), 0)


if __name__ == "__main__":
    raise SystemExit(main())
