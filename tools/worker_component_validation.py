#!/usr/bin/env python3
"""M0-owned PLAN-009 Linux x64 worker validation adapter (never product qualification).

The control tree supplies one frozen compiler/lock/wrapper. Only one worker
module and its owned fixture are overlaid. No request can run arbitrary shell.
"""
import argparse, base64, hashlib, io, json, os, pathlib, platform, re, resource
import shutil, subprocess, sys, tarfile, time, urllib.parse, urllib.request, zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from tools import governance as g

SHA=re.compile(r"[0-9a-f]{40}\Z")
DIGEST=re.compile(r"[0-9a-f]{64}\Z")
REPO="lly8666/wbd-next"
SUITES={
    "M1":("game015-receive","crates/wbd-engine/tests/m1_game015_same_vm_cost.rs",
           "crates/wbd-engine/src/runtime/game_shared.rs","m1_game015_same_vm_cost",
           "m1_game015_same_vm_game_receive_fixed_scenario"),
    "M3":("fec2-018-native-e4","crates/wbd-codec/tests/fec2_plan008_abba.rs",
           "crates/wbd-codec/src/fec_v2.rs","fec2_plan008_abba",
           "m3_plan008_fec2_e4_old_new_abba"),
}
OFFICIAL_ISAL="c387163fcbca62701d646149564c550c78a4f985"
CONTROL_WORKFLOW=".github/workflows/worker-component-validation.yml"
def need(condition,message):
    if not condition:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def json_bytes(value):return (json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
def save(path,value):
    p=pathlib.Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(json_bytes(value))
def shell(args,cwd=None,env=None,out=None):
    need(isinstance(args,list) and all(isinstance(s,str) for s in args),"command not argv")
    return subprocess.run(args,cwd=cwd,env=env,check=True,stdout=out)
def capture(args,cwd=None):
    return subprocess.check_output(args,cwd=cwd,text=True).strip()
def api(endpoint,token=None,raw=False):
    token=token or os.environ.get("GH_TOKEN")
    need(bool(token),"read-only GitHub token absent")
    uri="https://api.github.com/repos/"+REPO+"/"+endpoint.lstrip("/")
    req=urllib.request.Request(uri,headers={"Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req,timeout=45) as rsp:
        data=rsp.read()
    return data if raw else json.loads(data)
def git_blob(ref,path):
    need(bool(SHA.fullmatch(ref)),"source must be exact 40-char SHA")
    need(g.path_ok(path),"invalid module path")
    return subprocess.check_output(["git","show",ref+":"+path])
def fetch_refs(*refs):
    for ref in set(refs):
        need(bool(SHA.fullmatch(ref)),"not a pinned Git SOURCE")
        shell(["git","fetch","--no-tags","origin",ref,"--depth=1"])
        need(capture(["git","rev-parse","FETCH_HEAD"])==ref,"fetched source drift")
def identify(role,suite,fixture,source):
    need(role in SUITES,"only M1 Game015 and M3 FEC2-018 adapters are published")
    expected=SUITES[role]
    need((suite,fixture)==expected[:2],"unapproved fixture/scenario for role")
    need(bool(SHA.fullmatch(source)),"source not immutable SHA")
def check_abba_lines(lines,clock_ticks):
    need(len(lines)==4,"ABBA fixture must emit exactly four legs")
    parsed=[]
    for i,line in enumerate(lines):
        fields=dict(re.findall(r"([a-z_]+)=([A-Za-z0-9_]+)",line))
        need(fields.get("leg")==str(i) and fields.get("version")==("ABBA"[i]),
             "missing/reordered ABBA leg")
        need(fields.get("backend")=="NativeIsaL" and fields.get("k")=="16" and
             fields.get("r")=="16" and fields.get("e")=="4","scalar or mixed workload")
        for key in ("checksum","recoveries","wall_ns","cpu_ticks"):
            need(fields.get(key,"").isdigit(), "missing numerical fixture field "+key)
        need(int(fields["wall_ns"])>0 and int(fields["recoveries"])>0,
             "empty measurement leg")
        parsed.append(fields)
    need(len({(x["checksum"],x["recoveries"]) for x in parsed})==1,
         "different work/output across A/B legs")
    need(all(int(x["wall_ns"])>=1_000_000_000 and
             int(x["cpu_ticks"])/clock_ticks>=1 for x in parsed),
         "quantized native CPU measurement inconclusive")
    return parsed
def verify_functional_log(data,role):
    # Cargo can return 0 and still print 'test result: ok.'; this is NOT
    # functional evidence. Count actual passed tests, deny failed/zero.
    need(isinstance(data,str) and role in SUITES,"invalid functional log")
    counts=re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;",data)
    need(len(counts)>=1,"incomplete Cargo test result")
    passed=sum(int(p) for p,_,_ in counts)
    need(passed>0 and all(int(f)==0 for _,f,_ in counts),
         "zero functional cases or failed tests")
    if role=="M3":
        need("r1_f2_native_decode_tables_and_workspace_reused_dirty_tail_exact" in data,
             "native M3 workspace dirty-tail test absent")
    return passed

def validate_manifest(m,role,req,control):
    need(m.get("schema_version")==1 and m.get("stage")=="prepare","wrong manifest")
    need(m.get("role_id")==role and m.get("scenario")==req["scenario"] and
         m.get("seed")==req["seed"] and m.get("config_sha256")==req["config_sha256"],
         "prepare scenario identity changed")
    for field in ("source_sha","harness_sha","baseline_sha"):
        need(m.get(field)==req[field],"mixed SOURCE/harness/baseline")
    need(m.get("control_sha")==control,"different control/harness revision")
    need(m.get("platform")=="linux-x86_64" and
         m.get("native_backend")==("official-isal" if role=="M3" else "none"),
         "platform/native downgrade")
    need(m.get("feature")==("native-isal" if role=="M3" else "default"),
         "feature drift")
    need(m.get("functional_result")=="PASS" and
         bool(m.get("binaries_sha256")) and
         all(DIGEST.fullmatch(z) for z in m["binaries_sha256"].values()),
         "no validated build artifact")
    return True
def validate_context(request,role,stage,control_ref,control_sha,registry,
                     branch_head,request_ref,config_raw):
    g.validate_request(request)
    identify(role,request.get("scenario"),request.get("config_path",""),
             request.get("source_sha",""))
    worker=next((z for z in registry["roles"] if z["id"]==role),None)
    need(worker is not None and worker["state"]=="active","role inactive")
    need(request["role_id"]==role and request["task_id"]==worker["assigned_task"] and
         request["assignment_epoch"]==worker["assignment_epoch"] and
         request["reservation_revision"]==registry["reservation_revision"],
         "wrong role/task/epoch/revision")
    need(request["workflow"]==CONTROL_WORKFLOW and
         request["dispatch_ref"]==control_ref and
         request.get("control_sha")==control_sha,
         "unexpected workflow/ref or moved immutable control commit")
    need(request["request_id"]==pathlib.PurePosixPath(
         request.get("_request_path","")).stem,"wrong request identity/path")
    need(role in ("M1","M3") and worker["branch"].startswith("work/"),
         "worker branch not authorized")
    need(request.get("baseline_sha")!=request["source_sha"] and
         all(isinstance(request.get(k),str) and SHA.fullmatch(request[k])
             for k in ("baseline_sha","harness_sha","source_sha")),
         "missing pinned old/new/harness")
    cfg=request["config_path"]
    need(cfg==SUITES[role][1] and any(g.under(cfg,p) for p in worker["allowed_paths"]),
         "out of scope fixture path")
    need(sha(config_raw)==request["config_sha256"],"fixture/config digest drift")
    need(stage in ("prepare","paired"),"unknown stage")
    need(request["kind"]==("functional" if stage=="prepare" else "performance"),
         "wrong stage request kind")
    need(request["measurement_jobs"]==1 and
         request["samples"]==(1 if stage=="prepare" else (2 if role=="M1" else 4)),
         "wrong sample/job count")
    if stage=="paired":
        need(all(z["build_manifest_sha256"]==request["prepare_manifest_sha256"] for z in request["legs"]),
             "request mixes different prepare artifacts")
        need(request["mode"]==("paired_ab" if role=="M1" else "paired_abba"),
             "role requires declared AB or ABBA")
        for label in ("A","B"):
            legs=[leg for leg in request["legs"] if leg["label"]==label]
            need(all(leg["source_sha"]==request[
                "baseline_sha" if label=="A" else "source_sha"] for leg in legs),
                "leg/source mismatch")
        for key in ("prepare_run_id","prepare_run_attempt","prepare_artifact_id"):
            need(g.integer(request.get(key),1),"missing exact build run/artifact")
        need(bool(DIGEST.fullmatch(request.get("prepare_manifest_sha256",""))),
             "missing exact prepare manifest digest")
    need(SHA.fullmatch(control_sha) and SHA.fullmatch(request_ref) and
         SHA.fullmatch(branch_head),"floating control or worker ref")
    return worker
def remote_preflight(args):
    role,reqid=args.role_id,args.request_id
    need(role in SUITES and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,90}",reqid),
         "invalid worker request")
    need(SHA.fullmatch(args.request_ref) and SHA.fullmatch(args.control_sha),
         "request/control must be exact SHA")
    need(args.control_ref=="qualification/worker-ci-v3","not published control ref")
    registry=api("contents/.governance/registry.json?ref=main")
    registry=json.loads(base64.b64decode(registry["content"]))
    worker=next(z for z in registry["roles"] if z["id"]==role)
    request_path=".governance/workstreams/"+role+"/requests/"+reqid+".json"
    blob=api("contents/"+request_path+"?ref="+args.request_ref)
    request=json.loads(base64.b64decode(blob["content"]))
    request["_request_path"]=request_path
    branch=api("branches/"+worker["branch"])
    head=branch["commit"]["sha"]
    for ref in (args.request_ref,request["source_sha"],request["baseline_sha"],
                request["harness_sha"]):
        comparison=api("compare/"+ref+"..."+head+"?per_page=1")
        need(comparison["status"] in ("ahead","identical"),
             "request/source no longer reachable from registered worker branch")
    config_ref=urllib.parse.quote(request["harness_sha"],safe="")
    config_path=urllib.parse.quote(SUITES[role][1],safe="/")
    config_entry=api("contents/"+config_path+"?ref="+config_ref)
    config=base64.b64decode(config_entry["content"])
    validate_context(request,role,args.stage,args.control_ref,args.control_sha,
                     registry,head,args.request_ref,config)
    request["_control_sha"]=args.control_sha
    request["_request_ref"]=args.request_ref
    save(args.output,request)
def source_overlay(role,root,source,harness):
    module=SUITES[role][2];fixture=SUITES[role][1]
    target=root/module;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(git_blob(source,module))
    fixture_target=root/fixture;fixture_target.parent.mkdir(parents=True,exist_ok=True)
    fixture_target.write_bytes(git_blob(harness,fixture))
    if role=="M3":
        support="crates/wbd-codec/tests/support/fec_v2_code8cc.rs"
        (root/support).parent.mkdir(parents=True,exist_ok=True)
        accepted=git_blob(harness,support)
        need(sha(accepted)==sha(git_blob("8cc5b06d6832565a80b60402a5fe2e1078e9ab2e",module)),
             "M3 accepted code snapshot differs from 8cc baseline")
        (root/support).write_bytes(accepted)
        fixture_text=(root/fixture).read_text()
        need('const ACCEPTED_SHA: &str = "8cc5b06d6832565a80b60402a5fe2e1078e9ab2e"' in fixture_text,
             "M3 accepted module identity absent")
        match=re.search(r'const CANDIDATE_SHA: &str = "([0-9a-f]{40})"',fixture_text)
        need(match is not None,"M3 candidate identity absent")
        need(sha(git_blob(match.group(1),module))==sha(git_blob(source,module)),
             "M3 fixture candidate constant differs from actual module")
    return {"module_git_blob":capture(["git","rev-parse",source+":"+module]),
            "fixture_git_blob":capture(["git","rev-parse",harness+":"+fixture])}
def archive_checkout(control,root):
    root.mkdir(parents=True,exist_ok=False)
    archive=subprocess.check_output(["git","archive","--format=tar",control])
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:
        for member in t.getmembers():
            p=pathlib.PurePosixPath(member.name)
            need(not p.is_absolute() and ".." not in p.parts,
                 "unsafe control archive")
        t.extractall(root,filter="data")
def compile_prepare(request,output):
    role=request["role_id"];scenario,fixture,module,test,name=SUITES[role]
    control=request["_control_sha"]
    need(platform.system()=="Linux" and platform.machine()=="x86_64",
         "only native Linux x64 supported")
    work=pathlib.Path("worker-validation-build")
    if work.exists():shutil.rmtree(work)
    work.mkdir()
    fetch_refs(control,request["baseline_sha"],request["source_sha"],
               request["harness_sha"],"8cc5b06d6832565a80b60402a5fe2e1078e9ab2e" if role=="M3" else control)
    binaries={};blobs={};functional={}
    for label in (("A","B") if role=="M1" else ("B",)):
        source=request["baseline_sha" if label=="A" else "source_sha"]
        workspace=work/label;archive_checkout(control,workspace)
        blobs[label]=source_overlay(role,workspace,source,request["harness_sha"])
        env=os.environ.copy();env["CARGO_TARGET_DIR"]=str((workspace/"target").resolve())
        env["CARGO_INCREMENTAL"]="0"
        if role=="M3":
            need((pathlib.Path(env.get("WBD_ISAL_PREFIX",""))/"lib/libisal.a").is_file(),
                 "official ISA-L missing, never scalar fallback")
        args=["cargo","+1.85.1","test","--release","--locked","-p",
              "wbd-engine" if role=="M1" else "wbd-codec"]
        if role=="M3":args+=["--features","native-isal"]
        # Functional tests exercise affected module before any performance.
        focused=(["--lib","game_shared"] if role=="M1" else
                 ["--lib","r1_f2_native_decode_tables_and_workspace_reused_dirty_tail_exact"])
        with (output/("functional-"+label+".log")).open("wb") as log:
            shell(args+focused+["--","--nocapture"],cwd=workspace,env=env,out=log)
        logdata=(output/("functional-"+label+".log")).read_text()
        passed=verify_functional_log(logdata,role)
        functional[label]={"sha256":sha(logdata.encode()),"passed":passed}
        with (output/("compile-"+label+".log")).open("wb") as log:
            shell(args+["--test",test,"--no-run"],cwd=workspace,env=env,out=log)
        artifacts=list((workspace/"target/release/deps").glob(test+"-*"))
        executable=[p for p in artifacts if p.is_file() and os.access(p,os.X_OK) and not p.suffix]
        need(len(executable)==1,"ambiguous compiled Rust fixture")
        name_out="leg-"+label if role=="M1" else "m3-abba"
        shutil.copy2(executable[0],output/name_out)
        binaries[name_out]=sha((output/name_out).read_bytes())
    m={"schema_version":1,"stage":"prepare","role_id":role,
       "source_sha":request["source_sha"],"harness_sha":request["harness_sha"],
       "baseline_sha":request["baseline_sha"],"control_sha":control,
       "control_ref":request["dispatch_ref"],"config_sha256":request["config_sha256"],
       "scenario":scenario,"seed":request["seed"],
       "request_ref":request["_request_ref"],"request_id":request["request_id"],
       "run_id":int(os.environ["GITHUB_RUN_ID"]),"attempt":int(os.environ["GITHUB_RUN_ATTEMPT"]),
       "platform":"linux-x86_64","feature":"native-isal" if role=="M3" else "default",
       "native_backend":"official-isal" if role=="M3" else "none",
       "isal_source_sha":OFFICIAL_ISAL if role=="M3" else None,
       "isal_archive_sha256":sha((pathlib.Path(os.environ["WBD_ISAL_PREFIX"])/"lib/libisal.a").read_bytes()) if role=="M3" else None,
       "rustc":capture(["rustc","+1.85.1","--version"]),
       "cargo_lock_sha256":sha((pathlib.Path("Cargo.lock")).read_bytes()),
       "blobs":blobs,"binaries_sha256":binaries,"functional_log_sha256":functional,
       "functional_result":"PASS","product":"NOT_RUN"}
    save(output/"prepare-manifest.json",m)
    return m
def verify_artifact(request,bundle,control):
    role=request["role_id"]
    run=api("actions/runs/"+str(request["prepare_run_id"]))
    artifact=api("actions/artifacts/"+str(request["prepare_artifact_id"]))
    need(run.get("status")=="completed" and run.get("conclusion")=="success" and
         run.get("run_attempt")==request["prepare_run_attempt"] and
         run.get("head_sha")==control,"build run not a successful frozen control")
    need(artifact.get("workflow_run",{}).get("id")==request["prepare_run_id"] and
         not artifact.get("expired") and
         artifact.get("name")==("worker-prepare-"+str(request["prepare_run_id"])+"-"+
                                str(request["prepare_run_attempt"])),
         "missing/expired/mismatched prepare artifact")
    zip_path=bundle.parent/"prepared.zip"
    # GitHub CLI owns redirects; no freehand API URL or latest artifact search.
    with zip_path.open("wb") as f:
        shell(["gh","api","repos/"+REPO+"/actions/artifacts/"+
               str(request["prepare_artifact_id"])+"/zip"],out=f)
    with zipfile.ZipFile(zip_path) as z:
        for entry in z.infolist():
            name=pathlib.PurePosixPath(entry.filename)
            need(not name.is_absolute() and ".." not in name.parts,
                 "unsafe artifact member")
        z.extractall(bundle)
    raw=(bundle/"prepare-manifest.json").read_bytes()
    need(sha(raw)==request["prepare_manifest_sha256"],"manifest SHA256 drift")
    m=json.loads(raw)
    validate_manifest(m,role,request,control)
    need(m["run_id"]==request["prepare_run_id"] and
         m["attempt"]==request["prepare_run_attempt"],
         "manifest run identity mismatch")
    need(m["cargo_lock_sha256"]==sha(pathlib.Path("Cargo.lock").read_bytes()),
         "shared lockfile changed")
    for name,digest in m["binaries_sha256"].items():
        need(name in ("leg-A","leg-B","m3-abba") and
             (bundle/name).is_file() and sha((bundle/name).read_bytes())==digest,
             "binary missing or modified")
        (bundle/name).chmod(0o755)
    need(all(leg["build_manifest_sha256"]==request["prepare_manifest_sha256"]
             for leg in request["legs"]),"leg pointed to different prepare build")
    return m
def paired_run(request,bundle,out,control):
    m=verify_artifact(request,bundle,control)
    if not os.environ.get("MEASURE_JOB_ID"):
        jobs=api("actions/runs/"+os.environ["GITHUB_RUN_ID"]+"/jobs?per_page=100")
        matches=[j for j in jobs["jobs"] if j.get("name")=="paired"]
        need(len(matches)==1 and matches[0]["run_id"]==int(os.environ["GITHUB_RUN_ID"]),
             "paired job could not be independently identified")
        os.environ["MEASURE_JOB_ID"]=str(matches[0]["id"])
    role=request["role_id"];mode=request["mode"];clock=os.sysconf("SC_CLK_TCK")
    need(clock>0 and platform.system()=="Linux" and platform.machine()=="x86_64",
         "wrong paired host")
    def run_binary(path):
        before=resource.getrusage(resource.RUSAGE_CHILDREN)
        start=time.monotonic_ns()
        p=subprocess.run([str(path.resolve()),"--ignored","--exact",SUITES[role][4],
           "--nocapture","--test-threads=1"],capture_output=True,text=True)
        end=time.monotonic_ns()
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        return p,start,end,(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime)
    log=[];legs=[]
    if role=="M1":
        for item in request["legs"]:
            label=item["label"]
            result,start,end,cpu=run_binary(bundle/("leg-"+label))
            (out/("log-"+str(len(legs))+".txt")).write_text(result.stdout+result.stderr)
            need(result.returncode==0 and "test result: ok." in result.stdout,
                 "M1 fixture failed; no performance PASS")
            match=re.findall(r"M1_GAME015_COST_RESULT[^\n]*",result.stdout)
            need(len(match)==1,"missing M1 fixed-workload receipt")
            fields=dict(re.findall(r"([a-z_]+)=([0-9]+)",match[0]))
            need(int(fields.get("inputs",0))==262144 and int(fields.get("complete",0))>0,
                 "fixture incomplete")
            log.append(fields)
            legs.append(dict(item,job_id=int(os.environ["MEASURE_JOB_ID"]),
                config_sha256=request["config_sha256"],scenario=request["scenario"],
                seed=request["seed"],harness_sha=request["harness_sha"],
                start_monotonic_ns=start,end_monotonic_ns=end,result="PASS",
                cpu_s=cpu,work=int(fields["inputs"]),checksum=fields["checksum"],
                wall_ns=end-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss))
        need(len({(d["inputs"],d["first"],d["duplicate"],d["complete"],d["checksum"]) for d in log})==1,
             "M1 old/new unequal business work")
        need(all(x["cpu_s"]>=1.0 for x in legs),"CPU resolution/volume inconclusive")
    else:
        result,start,end,cpu=run_binary(bundle/"m3-abba")
        (out/"log-abba.txt").write_text(result.stdout+result.stderr)
        need(result.returncode==0 and "test result: ok." in result.stdout,
             "M3 native fixture failed")
        lines=re.findall(r"M3_018_ABBA leg=[^\n]*",result.stdout)
        parsed=check_abba_lines(lines,clock)
        need("M3_018_ABBA_DONE" in result.stdout,"M3 terminal ABBA missing")
        # This existing fixture records in-process CPU ticks/wall but NOT
        # absolute monotonic start/end per leg. Do not fabricate timestamps
        # and falsely promote its CPU ratios through governance receipt.
        for i,(item,fields) in enumerate(zip(request["legs"],parsed)):
            need(item["label"]==fields["version"],"M3 ABBA order mismatch")
            legs.append(dict(item,job_id=int(os.environ["MEASURE_JOB_ID"]),
                config_sha256=request["config_sha256"],scenario=request["scenario"],
                seed=request["seed"],harness_sha=request["harness_sha"],
                result="INCONCLUSIVE",cpu_ticks=int(fields["cpu_ticks"]),
                cpu_s=int(fields["cpu_ticks"])/clock,
                work=int(fields["recoveries"]),checksum=fields["checksum"],
                wall_ns=int(fields["wall_ns"]),start_monotonic_ns=None,
                end_monotonic_ns=None,absolute_window="NOT_INSTRUMENTED"))
    need(len(legs)==len(request["legs"]),"missing observed legs")
    record={k:request[k] for k in ("request_id","role_id","kind","source_sha",
                                  "harness_sha","config_sha256","scenario","seed")}
    record.update(control_sha=control,dispatch_ref=request["dispatch_ref"],
        mode=mode,run_id=int(os.environ["GITHUB_RUN_ID"]),
        run_attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
        result="PASS" if role=="M1" else "INCONCLUSIVE",
        artifact_verified=True,product="NOT_RUN",
        native_backend=m["native_backend"],clock_ticks_per_second=clock,
        same_job_id=int(os.environ["MEASURE_JOB_ID"]),legs=legs,
        host={"node":platform.node(),"kernel":platform.release(),
              "architecture":platform.machine(),
              "cpu_count":os.cpu_count(),
              "cgroup_cpu_max":pathlib.Path("/sys/fs/cgroup/cpu.max").read_text().strip() if pathlib.Path("/sys/fs/cgroup/cpu.max").exists() else "NOT_RUN",
              "pressure_cpu":pathlib.Path("/proc/pressure/cpu").read_text().strip() if pathlib.Path("/proc/pressure/cpu").exists() else "NOT_RUN"},
        limits=["fixture CPU instrumentation only","M3 lacks absolute per-leg monotonic bounds until worker improves fixture"] if role=="M3" else [])
    save(out/"receipt.json",record)
    return record
def main():
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=("preflight","prepare","paired","selftest"))
    p.add_argument("--role-id");p.add_argument("--request-id")
    p.add_argument("--request-ref");p.add_argument("--control-ref")
    p.add_argument("--control-sha");p.add_argument("--output",default="validation/request.json")
    p.add_argument("--request-file",default="validation/request.json")
    p.add_argument("--bundle",default="validation/bundle")
    args=p.parse_args()
    if args.stage=="selftest":
        need(len(SUITES)==2 and sha(b"test")==hashlib.sha256(b"test").hexdigest(),
             "module runner selftest")
        print("WORKER_COMPONENT_VALIDATION_STATIC_PASS")
        return
    if args.stage=="preflight":
        remote_preflight(args);return
    request=json.loads(pathlib.Path(args.request_file).read_text())
    output=pathlib.Path(args.output);output.mkdir(parents=True,exist_ok=True)
    if args.stage=="prepare":
        compile_prepare(request,output)
    else:
        paired_run(request,pathlib.Path(args.bundle),output,request["_control_sha"])
if __name__=="__main__":main()
