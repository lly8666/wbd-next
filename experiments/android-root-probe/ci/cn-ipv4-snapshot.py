#!/usr/bin/env python3
"""Build deterministic CN IPv4 APNIC delegation snapshot for Android split.
Source is *allocation registration*, not definitive geolocation: manual rule
updates and routing validation remain required. Never treat missing data as CN.
"""
import hashlib,ipaddress,json,sys
from pathlib import Path
if len(sys.argv)!=3:raise SystemExit("usage: cn-ipv4-snapshot.py <delegated-APNIC-file> <output-directory>")
source=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
raw=source.read_bytes()
if not (1_000_000<len(raw)<20_000_000):raise SystemExit("APNIC snapshot invalid size")
records=[];observed=0
for line in raw.decode("ascii").splitlines():
 cols=line.split("|")
 if len(cols)<7 or cols[0]!="apnic" or cols[1]!="CN" or cols[2]!="ipv4":
  continue
 if cols[6] not in ("allocated","assigned"):continue
 try:
  start=ipaddress.IPv4Address(cols[3]);total=int(cols[4])
  assert total>0 and int(start)+total-1<=0xffffffff
  spans=list(ipaddress.summarize_address_range(start,ipaddress.IPv4Address(int(start)+total-1)))
 except Exception as e:raise SystemExit(f"malformed APNIC CN entry: {line[:120]}: {e}")
 records.extend(spans);observed+=1
if not (1000<=observed<=10000):
 raise SystemExit(f"APNIC CN record count suspicious: {observed}")
collapsed=list(ipaddress.collapse_addresses(records))
assert len(collapsed)>1000
lines="\n".join(str(x) for x in collapsed)+"\n"
(out/"wbd-cn-ipv4.txt").write_text(lines,encoding="ascii")
report={"schema":"wbd-android-cn-ipv4-apnic-snapshot/v1",
 "source_url":"https://ftp.apnic.net/stats/apnic/delegated-apnic-20261116",
 "source_date_utc":"2026-11-16",
 "source_sha256":hashlib.sha256(raw).hexdigest(),
 "cn_records":observed,
 "cn_collapsed_prefixes":len(collapsed),
 "cidr_sha256":hashlib.sha256(lines.encode()).hexdigest(),
 "meaning":"APNIC CN allocated/assigned IPv4 prefix ownership snapshot, not complete IP geolocation",
 "update_policy":"manual/explicit future signed snapshot only; no auto background refresh",
 "cn_domain_snapshot":"NOT_INCLUDED; .cn suffix + user-provided exact/suffix only"}
(out/"cn-ipv4-provenance.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
