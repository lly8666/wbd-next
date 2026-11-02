#!/usr/bin/env python3
"""Install the SAME exact current V4 FakeTCP sources Windows assembler uses.

Pinned upstream original files verified by Git blob SHA before any write.
No Linux-only handwritten MSS replacements or old-V4 compatibility switches.
"""
from pathlib import Path
import hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
ORIGINAL={"packet.go":"6ac1f9b3d7208278d31078be8d61e2f3a6dbbd3b","client_association.go":"83e85b4871ee59e7ab47ea2b53387bef584898c4","association.go":"779cb74a9719f15615b6315ec548996951ae9138","association_test.go":"1a0180f7c3033b4d0e6980bc351735cf93ef08cc"}
RESULT={"packet.go":"4dd669bedc455596fb9b9da3306cb0a7010246be","client_association.go":"d80b51c69a577a73fcc6494ff3cf554dd44ba162","association.go":"aa584980df88e0f034049c6a83cb1e4409f8a7d9","association_test.go":"de20ef1d172e4c432546c69b89ac701944821074"}
CREATED={"public_v4_mss.go":"f31c4ca427cee864e499d1c201c56070358d0c10","public_v4_mss_test.go":"20678052954fca4f849362dd3174abd20cfb1cb7","public_v4_mss_byte_test.go":"5ec59832eafafba158054fe4a0bea10671cf28c8"}
def blob(content):
 return hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()
def install(where):
 target=Path(where).resolve(strict=True)/"internal"/"faketcp"
 pending=[]
 for name,sha in ORIGINAL.items():
  dst=target/name
  if blob(dst.read_bytes())!=sha:raise ValueError("original Go SHA changed "+name)
  data=(ROOT/"r0"/"go_overlay"/"internal"/"faketcp"/name).read_bytes()
  if blob(data)!=RESULT[name]:raise ValueError("shared MSS overlay SHA changed "+name)
  pending.append((dst,data))
 for name,sha in CREATED.items():
  dst=target/name
  if dst.exists():raise ValueError("unexpected fake TCP overlay collision "+name)
  data=(ROOT/"r0"/"go_overlay"/"internal"/"faketcp"/name).read_bytes()
  if blob(data)!=sha:raise ValueError("shared MSS new source SHA changed "+name)
  pending.append((dst,data))
 for dst,data in pending:dst.write_bytes(data)
 print("V4_ONE_ORIGINAL_GO_FAKETCP_MSS_SOURCE_INSTALLED files="+str(len(pending)))
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("usage: m0_install_public_faketcp.py LEGACY_ROOT")
 install(sys.argv[1])
