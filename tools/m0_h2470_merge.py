"""Merge immutable H2470 observation JSON files without silently replacing results."""
import argparse,json,pathlib
def merge(inputs):
    rows={}
    for path in inputs:
        data=json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
        items=data["observations"] if "observations" in data else [data]
        for row in items:
            key=(str(row["run_id"]),row["source_sha"])
            if key in rows and rows[key]!=row:raise ValueError("conflicting run receipt "+repr(key))
            rows[key]=row
    return {"schema":"m0-machine-rate-database-v1","observations":list(rows.values()),
            "rate_profiles":[],"scope":"Raw evidence; no automatic rate selection. Keep probe duration, software versions and qualification."}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);p.add_argument("inputs",nargs="+")
    a=p.parse_args();pathlib.Path(a.out).write_text(json.dumps(merge(a.inputs),indent=2)+"\n")
