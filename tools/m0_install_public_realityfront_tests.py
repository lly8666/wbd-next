#!/usr/bin/env python3
"""Install exactly two pinned, test-only current V4 Realityfront MSS adapters.

Never replace any original production Go source. Both original Git blobs and
current overlay blobs must match the SAME authoritative Windows manifest.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"r0/go_overlay/assembly/manifest-plan020-m0.json"
FILES={"tls_test.go":(("faketcp.DefaultMSS","faketcp.PublicV4AdvertisedMSS()"),),
       "wire_qualification_test.go":(
        ("faketcp.DefaultMSS","faketcp.PublicV4AdvertisedMSS()"),
        ("len(seg.Payload) > faketcp.PublicV4AdvertisedMSS()",
         "len(seg.Payload) > int(faketcp.PublicV4AdvertisedMSS())"))}
SOURCE="a7a82db31fe736ffedee330795a3234d358f1984"
def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def manifest_rows():
    manifest=json.loads(MANIFEST.read_text())
    if manifest.get("legacy_source")!=SOURCE or manifest.get("schema_version")!=1:
        raise ValueError("MSS Realityfront pinned original source changed")
    entries={}
    for e in manifest["operations"]:
        if e.get("path") in ("internal/realityfront/"+n for n in FILES):
            name=e["path"].rsplit("/",1)[1]
            if name in entries or e.get("kind")!="replace" or e.get("overlay_path")!="r0/go_overlay/internal/realityfront/"+name or "patches" in e:
                raise ValueError("ambiguous test-only Realityfront source "+name)
            entries[name]=e
    if set(entries)!=set(FILES):raise ValueError("incomplete current V4 Realityfront MSS test sources")
    return entries
def install(legacy=None):
    rows=manifest_rows()
    pending=[]
    for name,changes in FILES.items():
        entry=rows[name]
        src=ROOT/entry["overlay_path"]
        new=src.read_bytes()
        if blob(new)!=entry["result_blob"]:raise ValueError("Realityfront test overlay blob drift "+name)
        if legacy is not None:
            dest=Path(legacy)/"internal/realityfront"/name
            previous=dest.read_bytes()
            if blob(previous)!=entry["original_blob"]:
                raise ValueError("refused overwrite nonoriginal Go Realityfront "+name)
            expected=previous
            for old,replacement in changes:
                old=old.encode();replacement=replacement.encode()
                if expected.count(old)!=1:raise ValueError("missing uniquely pinned test-only anchor "+name)
                expected=expected.replace(old,replacement,1)
            if expected!=new:raise ValueError("unexpected V4 Realityfront test-only mutation "+name)
            pending.append((dest,new))
    for dest,data in pending:dest.write_bytes(data)
    print("V4_REALITYFRONT_MSS_TESTS_"+("CHECKED" if legacy is None else "INSTALLED")+" files=2 source="+SOURCE)
if __name__=="__main__":
    if len(sys.argv)==2 and sys.argv[1]=="--check-only":install()
    elif len(sys.argv)==2:install(sys.argv[1])
    else:raise SystemExit("usage: m0_install_public_realityfront_tests.py LEGACY_ROOT | --check-only")
