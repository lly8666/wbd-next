"""Android typed text adapter for main's official flattened CN snapshot.
Use the shared build-time release downloader/parser; no runtime fetch.
"""
import hashlib
import json
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"r0/go_overlay/assembly"))
import cn_domain_snapshot as shared

out=pathlib.Path(sys.argv[1])
binary=out/"official-cn.dat"
meta=shared.install(binary)
group=next(v for n,v,_ in shared.fields(binary.read_bytes()) if n==1 and isinstance(v,bytes))
rules=set()
for n,domain,_ in shared.fields(group):
    if n!=2 or not isinstance(domain,bytes):continue
    kind=0
    value=None
    for k,v,_ in shared.fields(domain):
        if k==1 and isinstance(v,int):kind=v
        if k==2 and isinstance(v,bytes):value=v.decode("utf-8")
    if value is None or kind not in (0,1,2,3):raise ValueError("invalid upstream domain")
    if kind in (2,3):value=value.rstrip(".").encode("idna").decode("ascii").lower()
    if kind==0:value=value.lower()
    if not value or "\n" in value or "\r" in value:raise ValueError("empty upstream rule")
    rules.add(("keyword","regexp","domain","full")[kind]+":"+value)
if len(rules)<1000:raise ValueError("official CN group too small")
raw=("\n".join(sorted(rules))+"\n").encode()
kinds={}
for line in rules:
    k=line.split(":",1)[0]
    kinds[k]=kinds.get(k,0)+1
result=dict(meta,source=meta["upstream"],source_commit=meta["source_sha"],
            text_sha256=hashlib.sha256(raw).hexdigest(),
            output_distinct_rules=len(rules),kinds=kinds)
(out/"wbd-cn-geosite.txt").write_bytes(raw)
(out/"cn-geosite-provenance.json").write_text(json.dumps(result,indent=2)+"\n")
receipt_path=out/"receipt.json"
receipt=json.loads(receipt_path.read_text())
receipt["active_cn"]=result
receipt_path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("ANDROID_B81_SHARED_OFFICIAL_CN",result)
