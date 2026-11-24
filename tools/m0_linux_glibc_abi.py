#!/usr/bin/env python3
"""Inspect actual ELF version needs, not compiler claims; build/CI only."""
import json, pathlib, re, subprocess, sys
bundle=pathlib.Path(sys.argv[1])
limit=tuple(map(int,sys.argv[2].split("."))) if len(sys.argv)>2 else None
report={}
for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
    p=bundle/name
    version=subprocess.check_output(["readelf","--version-info","--wide",str(p)],text=True)
    needs=version.split("Version needs section")
    assert len(needs)>1, name
    versions=sorted({tuple(map(int,v.split("."))) for v in re.findall(r"Name: GLIBC_(\d+(?:\.\d+)+)",needs[-1])})
    assert versions, name
    dynamic=subprocess.check_output(["readelf","-dW",str(p)],text=True)
    needed=re.findall(r"\(NEEDED\).*?\[(.*?)\]",dynamic)
    assert "GLIBC_PRIVATE" not in needs[-1], name
    report[name]={"max_glibc":".".join(map(str,versions[-1])),"needed":needed}
    if limit is not None:
        assert versions[-1]<=limit,(name,versions[-1],limit)
(bundle/"glibc-abi.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,sort_keys=True))
