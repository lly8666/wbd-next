#!/usr/bin/env python3
"""Install the ONE source-locked public V4 FakeTCP assembly for Linux and ARM64.

The Windows assembly manifest is the sole list of original/result Git blobs.
Never duplicate checked-in SHA constants: doing so previously blocked H968
Linux while the exact same Windows Go source had passed byte-level tests.
Writes happen only after ALL seven original and result blobs pass verification.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"r0/go_overlay/assembly/manifest-plan020-m0.json"
ORIGINAL_SOURCE="a7a82db31fe736ffedee330795a3234d358f1984"
REPLACE=("packet.go","client_association.go","association.go","association_test.go")
CREATE=("public_v4_mss.go","public_v4_mss_test.go","public_v4_mss_byte_test.go")

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\\0"+data).hexdigest()

def expected_rows():
    spec=json.loads(MANIFEST.read_text())
    if spec.get("schema_version")!=1 or spec.get("legacy_source")!=ORIGINAL_SOURCE:
        raise ValueError("V4 shared FakeTCP source manifest provenance mismatch")
    expected=set(REPLACE+CREATE)
    matched={}
    for row in spec["operations"]:
        name=row["path"].removeprefix("internal/faketcp/")
        if name not in expected or row["path"]!="internal/faketcp/"+name:
            continue
        if name in matched:raise ValueError("duplicate shared V4 FakeTCP operation "+name)
        if row.get("kind")!=("replace" if name in REPLACE else "create"):
            raise ValueError("wrong shared V4 FakeTCP operation "+name)
        if row.get("overlay_path")!="r0/go_overlay/internal/faketcp/"+name:
            raise ValueError("cross-source FakeTCP path "+name)
        if row.get("patches") is not None or row.get("donor_blob") is not None:
            raise ValueError("MSS file must be a full pinned copy "+name)
        if name in REPLACE and not row.get("original_blob"):
            raise ValueError("missing original Go blob "+name)
        matched[name]=row
    if set(matched)!=expected:
        raise ValueError("incomplete shared V4 FakeTCP manifest "+repr(expected-set(matched)))
    return matched

def install(where,check_only=False):
    target=Path(where).resolve(strict=True)/"internal"/"faketcp" if where else None
    rows=expected_rows()
    pending=[]
    for name in REPLACE+CREATE:
        row=rows[name]
        content=(ROOT/row["overlay_path"]).read_bytes()
        if blob(content)!=row["result_blob"]:
            raise ValueError("shared MSS overlay SHA changed "+name)
        if target is not None:
            dst=target/name
            if name in REPLACE:
                if blob(dst.read_bytes())!=row["original_blob"]:
                    raise ValueError("original pinned Go SHA changed "+name)
            elif dst.exists():
                raise ValueError("unexpected V4 FakeTCP overlay collision "+name)
            pending.append((dst,content))
    if not check_only:
        if target is None:raise ValueError("original Go destination required")
        for dst,content in pending:dst.write_bytes(content)
    print("V4_ONE_ORIGINAL_GO_FAKETCP_MSS_SOURCE_"+("CHECKED" if check_only else "INSTALLED")+
          " files="+str(len(rows))+" original="+ORIGINAL_SOURCE)

if __name__=="__main__":
    if len(sys.argv)==2 and sys.argv[1]=="--check-only":install(None,True)
    elif len(sys.argv)==2:install(sys.argv[1])
    else:raise SystemExit("usage: m0_install_public_faketcp.py LEGACY_ROOT | --check-only")
