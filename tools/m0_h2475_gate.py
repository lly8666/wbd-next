"""H2475: read-only hosted Windows CPU eligibility. Unknown is an explicit skip."""
import json,os,pathlib,re,sys

def eligible(names):
    if isinstance(names,str):names=[names]
    if not isinstance(names,list):return False
    names=[str(n).strip() for n in names if n is not None and str(n).strip()]
    return bool(names) and all(re.search(r"(?<![a-z0-9])9[\s_-]*v[\s_-]*45(?![a-z0-9])",n,re.I) for n in names)

if __name__=="__main__":
    names=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    ok=eligible(names)
    receipt={"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"names":names,
             "eligible":ok,"status":"MATCHED_9V45" if ok else "SKIPPED_CPU"}
    pathlib.Path(sys.argv[2]).write_text(json.dumps(receipt,indent=2)+"\n")
    with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as f:f.write("eligible="+str(ok).lower()+"\n")
    print("H2475_CPU_GATE "+json.dumps(receipt),flush=True)
