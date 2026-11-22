#!/usr/bin/env python3
"""Exact old Go tests-only MSS compatibility after installing new pinned FakeTCP.

These two legacy Go _test.go fixtures referenced an obsolete 1360 constant.
Keep the *same* numeric expected value only in the tests, not in product
sources or runtime: public SYN MSS remains current Rust-selected state.
The old original source bytes must match the exact immutable legacy commit.
"""
from pathlib import Path
import hashlib
import sys

FROZEN={
    "tls_test.go":("81c0fe570790a9652732032085ce6b38ade946c1",1),
    "wire_qualification_test.go":("16ec82491d4ae869724b506e0d33e5e84f196930",2),
}
OLD=b"faketcp.DefaultMSS"
# This is the old test oracle's historical expected value. The new production
# FakeTCP explicitly has no DefaultMSS and fails closed until Rust supplies it.
NEW=b"1360 /* pinned old-test expected SYN MSS, no runtime fallback */"

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def rewrite(name:str,data:bytes)->bytes:
    sha,count=FROZEN[name]
    if blob(data)!=sha or data.count(OLD)!=count:
        raise ValueError("pinned original Go test-only MSS fixture changed: "+name)
    return data.replace(OLD,NEW)

def install(where:Path):
    root=Path(where).resolve(strict=True)
    folder=root/"internal"/"realityfront"
    pending=[]
    for name in FROZEN:
        target=folder/name
        pending.append((target,rewrite(name,target.read_bytes())))
    # Verify ALL originals before touching even one source file.
    for target,content in pending:
        target.write_bytes(content)
    print("M0_PINNED_ORIGINAL_GO_TEST_ONLY_MSS_EXPECTATIONS_PRESERVED count=3 actual_runtime_mss_unchanged=1")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: m0_legacy_test_mss_compat.py LEGACY_ROOT")
    install(Path(sys.argv[1]))
