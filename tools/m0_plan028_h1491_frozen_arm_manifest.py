#!/usr/bin/env python3
"""Extract one immutable H1484 true ARM64 + native ISA-L Go/Rust SOURCE57B package.

No rebuild, no emulation, no private downloaded source mutations.
"""
import argparse, hashlib, json, pathlib, struct, zipfile

SOURCE="57b0d0cded995cf26b6f8ea43a3d4588e6e61d27"
ARCHIVE_SHA="343b330d2b5f19fd77c8a5bbdd0d70533f51fda1bbbf86cae627d54f244c45cd"
FILES=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")

def extract(src,dest):
    raw=src.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ARCHIVE_SHA, "ARM native ZIP SHA"
    with zipfile.ZipFile(src) as z:
        assert z.testzip() is None,"immutable native ZIP CRC"
        assert set(z.namelist())==set(FILES)|{"manifest.json"}
        m=json.loads(z.read("manifest.json"))
        assert m["source_sha"]==SOURCE
        assert m["original_go_sha"]=="a7a82db31fe736ffedee330795a3234d358f1984"
        assert m["architecture"]=="native_aarch64"
        assert m["native_fec_acceleration"] is True
        assert m["isa_l_source"]=="c387163fcbca62701d646149564c550c78a4f985"
        assert len(m["isa_l_archive_sha256"])==64
        assert set(m["sha256"])==set(FILES)
        assert m["rust_features"].endswith(",native_fec_acceleration")
        dest.mkdir(parents=True,exist_ok=True)
        (dest/"manifest.json").write_bytes(z.read("manifest.json"))
        for n in FILES:
            data=z.read(n)
            assert hashlib.sha256(data).hexdigest()==m["sha256"][n],n
            assert data[:4]==b"\x7fELF" and struct.unpack_from("<H",data,18)[0]==183,n
            p=dest/n
            p.write_bytes(data)
            p.chmod(0o755 if n.startswith("wbd-v4-") else 0o644)
    print("H1491_57B_ARM64_NATIVE_ISAL_BOTH_END_ELF_MANIFEST_SHA_AND_ZIP_CRC_PASS")
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--zip",required=True,type=pathlib.Path)
    ap.add_argument("--out",required=True,type=pathlib.Path)
    a=ap.parse_args();extract(a.zip,a.out)
