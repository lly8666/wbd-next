"""Build-time pinned V2Fly geolocation-cn subset for Go embed; not a runtime download."""
import hashlib
import json
import pathlib
import urllib.request

TAG="20261123144211"
SOURCE="dfa5b1c2258289bdbee70d06352cca23b9bdac7f"
BASE=f"https://github.com/v2fly/domain-list-community/releases/download/{TAG}/"
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"WBD-build"}),timeout=60) as r:
        return r.read()
def varint(data, offset):
    n=0
    for shift in range(0,70,7):
        b=data[offset];offset+=1;n|=(b&127)<<shift
        if not b&128:return n,offset
    raise ValueError("invalid varint")
def fields(data):
    offset=0
    while offset<len(data):
        begin=offset;tag,offset=varint(data,offset)
        if tag&7==0:value,offset=varint(data,offset)
        elif tag&7==2:
            n,offset=varint(data,offset)
            if n>len(data)-offset:raise ValueError("truncated geosite")
            value=data[offset:offset+n];offset+=n
        else:raise ValueError("unsupported wire field")
        yield tag>>3,value,data[begin:offset]
def select(data):
    chosen=[]
    for number,site,wire in fields(data):
        if number!=1 or not isinstance(site,bytes):continue
        parts=list(fields(site))
        if any(n==1 and isinstance(v,bytes) and v.lower()==b"geolocation-cn" for n,v,_ in parts):
            count=sum(n==2 for n,_,_ in parts)
            if count<1000:raise ValueError("unexpectedly small upstream CN group")
            chosen.append((wire,count))
    if len(chosen)!=1:raise ValueError("expected one upstream geolocation-cn")
    return chosen[0]
def install(target):
    raw=get(BASE+"dlc.dat")
    digest=hashlib.sha256(raw).hexdigest()
    expected=get(BASE+"dlc.dat.sha256sum").decode().split()[0].lower()
    if digest!=expected:raise ValueError("official DLC checksum mismatch")
    selected,count=select(raw)
    target.write_bytes(selected)
    result={"upstream":"v2fly/domain-list-community","tag":TAG,"source_sha":SOURCE,
            "group":"geolocation-cn","upstream_sha256":digest,
            "embedded_sha256":hashlib.sha256(selected).hexdigest(),"upstream_entries":count,
            "license":"MIT","scope":"official flattened group with all rule types; runtime offline"}
    target.with_suffix(".json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result
