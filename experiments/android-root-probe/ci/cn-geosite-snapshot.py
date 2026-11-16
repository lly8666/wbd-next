#!/usr/bin/env python3
"""Deterministic pinned geolocation-cn importer for Android Root DNS policy.
Reads a ZIP of v2fly/domain-list-community at an EXACT commit, never follows
untrusted source paths or downloads runtime rules on the phone.

Preserves include recursion, direct/affiliated entries, @must/@-ban filtering,
and the four upstream rule types. No silent keyword/regex-to-suffix downgrade.
The build fails closed if the source is missing, cyclic, malformed or implausible.
This is a DNS-domain classification dataset, not proof of Chinese IP locality.
"""
import collections
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

REV="41504eae2a11f305fe88cfc605cf6c105a80bf5a"
if len(sys.argv)!=3:
    raise SystemExit("usage: cn-geosite-snapshot.py <pinned-source-archive.zip> <output-assets-dir>")
archive=Path(sys.argv[1])
out=Path(sys.argv[2])
out.mkdir(parents=True,exist_ok=True)
raw=archive.read_bytes()
if not (300_000<len(raw)<30_000_000):raise SystemExit("upstream zip implausible size")
z=zipfile.ZipFile(archive)
prefix=f"domain-list-community-{REV}/"
assert all(not n.startswith("/") and ".." not in n.split("/") for n in z.namelist())
if not any(n.startswith(prefix+"data/") for n in z.namelist()):
    raise SystemExit("archive does not match expected commit name prefix")
license_data=z.read(prefix+"LICENSE").decode("utf-8")
if "MIT License" not in license_data or "Copyright (c) 2018-2019 V2Ray" not in license_data:
    raise SystemExit("unexpected third-party license")
data={}
for n in z.namelist():
    if not n.startswith(prefix+"data/") or n.endswith("/"):continue
    key=n[len(prefix+"data/"):]
    if "/" in key or not re.fullmatch(r"[a-z0-9_!.-]{1,100}",key):
        raise SystemExit(f"unexpected upstream list filename: {key!r}")
    body=z.read(n)
    if len(body)>600_000:raise SystemExit("one domain list exceeds cap")
    data[key.upper()]=body.decode("utf8")
if len(data)<500:raise SystemExit(f"truncated domain sources: {len(data)}")
# List -> entries (kind,value, frozenset(attrs)) plus include filters.
entries=collections.defaultdict(list)
includes=collections.defaultdict(list)
affiliation_count=0
valid_domain=re.compile(r"(?=.{1,253}$)(?!-)[a-z0-9-]+(?:\.[a-z0-9-]+)*$")
for list_name,body in data.items():
    for line_no,line in enumerate(body.splitlines(),1):
        line=line.split("#",1)[0].strip()
        if not line:continue
        if ":" in line:
            head,rest=line.split(":",1)
            kind=head.lower()
            if kind not in ("include","domain","full","keyword","regexp"):
                raise SystemExit(f"unsupported source syntax {list_name}:{line_no} {kind}")
        else:
            kind,rest="domain",line
        parts=rest.split()
        if not parts:raise SystemExit(f"empty {list_name}:{line_no}")
        word=parts[0]
        if kind=="include":
            incl=word.upper()
            must=set()
            ban=set()
            for a in parts[1:]:
                if not a.startswith("@"):raise SystemExit(f"invalid include tag {list_name}:{line_no}: {a}")
                if a.startswith("@-"):ban.add(a[2:].lower())
                else:must.add(a[1:].lower())
            includes[list_name].append((incl,frozenset(must),frozenset(ban)))
            continue
        word=word.lower() if kind!="regexp" else word
        if kind in ("domain","full"):
            labels=word.split(".")
            if not (valid_domain.fullmatch(word) and
                    all(0<len(k)<=63 and not k.startswith("-") and not k.endswith("-") for k in labels)):
                raise SystemExit(f"invalid domain {list_name}:{line_no}: {word}")
        if kind=="keyword" and not re.fullmatch(r"[a-z0-9.-]+",word):
            raise SystemExit(f"invalid keyword {list_name}:{line_no}: {word}")
        if len(word)>512:raise SystemExit(f"rule too long {list_name}:{line_no}")
        attrs=set()
        affs=[]
        for term in parts[1:]:
            if term.startswith("@"):attrs.add(term[1:].lower())
            elif term.startswith("&"):affs.append(term[1:].upper())
            else:raise SystemExit(f"unknown rule metadata {list_name}:{line_no}: {term}")
        value=(kind,word,frozenset(attrs))
        entries[list_name].append(value)
        for a in affs:
            entries[a].append(value)
            affiliation_count+=1

cache={}
visiting=set()
def resolve(name):
    if name not in data and name not in entries:
        raise SystemExit(f"missing source/affiliated list {name}")
    if name in cache:return cache[name]
    if name in visiting:raise SystemExit(f"circular include at {name}")
    visiting.add(name)
    result=set(entries[name])
    for child,must,ban in includes[name]:
        for e in resolve(child):
            if (not must or must.issubset(e[2])) and not (ban & e[2]):
                result.add(e)
    visiting.remove(name)
    cache[name]=result
    return result
found=resolve("GEOLOCATION-CN")
# Type+value is enough once upstream include attr filters are resolved.
flat=sorted(set((kind,value) for kind,value,_ in found))
counts=dict(collections.Counter(k for k,_ in flat))
if len(flat)<1000 or counts.get("domain",0)<1000:
    raise SystemExit(f"geosite snapshot suspiciously small: {counts}")
if any(k not in ("domain","full","keyword","regexp") for k,_ in flat):
    raise SystemExit("unknown geosite rule after flatten")
serialized="".join(f"{kind}:{value}\n" for kind,value in flat).encode()
if not 10_000<len(serialized)<6_000_000:
    raise SystemExit(f"geosite bytes out of bound: {len(serialized)}")
path=out/"wbd-cn-geosite.txt"
path.write_bytes(serialized)
(out/"wbd-cn-geosite-license.txt").write_text(license_data)
manifest={
    "schema":"wbd-android-cn-domain-geosite/v1",
    "source":"v2fly/domain-list-community",
    "source_repo":"https://github.com/v2fly/domain-list-community",
    "source_commit":REV,
    "source_archive_sha256":hashlib.sha256(raw).hexdigest(),
    "source_license":"MIT; bundled license in APK",
    "list":"geolocation-cn",
    "source_list_count":len(data),
    "resolved_list_count":len(cache),
    "affiliated_entries_seen":affiliation_count,
    "input_entries_with_attributes":len(found),
    "output_distinct_rules":len(flat),
    "kinds":counts,
    "text_sha256":hashlib.sha256(serialized).hexdigest(),
    "android_match_rule":"DNS admission exact/suffix/keyword/compiled regex; ordinary DATA actual real-IP routing",
    "not_ip_geolocation":True,
    "no_fakeip":True,
    "update_policy":"fixed source commit, artifact hashes; no phone background network refresh",
}
(out/"cn-geosite-provenance.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
print(json.dumps(manifest,indent=2,sort_keys=True))
