#!/usr/bin/env python3
"""Fetch two immutable native product pairs by GitHub artifact ID, never by ambiguous name.
Runs on same Windows VM before four A/B/B/A process lifetimes. No packet data/credentials.
"""
import hashlib,json,os,pathlib,subprocess,sys,zipfile

REPO="lly8666/wbd-next"
PAIRS={
 "A":{"source":"7fc38591c501ff4a06e1862c7b08d5d3dbc1be95","run":40693430836,
      "windows":(12817869276,"d8af30124287896614a6cf8793817c9f3b025bd5e4dce9f8eeaa9d3855ae0561"),
      "linux":(12818806001,"1343c954e1532cad22d98a44eaba01efd6fefb8a2643b269190b24e8b1f28975")},
 "B":{"source":"e6be9358d2272d7e1960a935be7fe772885bb034","run":40697876014,
      "windows":(12821761652,"21f11d1329f11f07edb942d6b7bed6548deed201d832279b30b63eeb242b74e9"),
      "linux":(12820257191,"0e8b911b25eb42f0f50c6e7fec7c101a9c99a5578bfbbb8a35bd8a2ad12481aa")}
}
PRODUCT_FILES=("wbd-client-embedded.exe","wbd_engine.dll","wbd-v4-server","wbd-v4-client","libwbd_engine.so")
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for part in iter(lambda:f.read(1048576),b""):h.update(part)
 return h.hexdigest()
def gh_json(api):
 p=subprocess.run(["gh","api",api],capture_output=True,check=True)
 return json.loads(p.stdout)
def fetch_zip(artifact_id,expected,target):
 target.parent.mkdir(parents=True,exist_ok=True)
 with target.open("wb") as f:
  subprocess.run(["gh","api",f"repos/{REPO}/actions/artifacts/{artifact_id}/zip"],
                 stdout=f,check=True)
 if sha(target)!=expected:raise RuntimeError(f"ZIP digest mismatch artifact {artifact_id}")
def unzip_safe(zip_path,dest):
 dest.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(zip_path) as z:
  for entry in z.infolist():
   p=pathlib.PurePosixPath(entry.filename)
   if p.is_absolute() or ".." in p.parts or entry.is_dir() and p.name=="":
    raise RuntimeError("Unsafe artifact ZIP member")
   if (entry.external_attr>>16)&0o170000==0o120000:
    raise RuntimeError("Symbolic links prohibited in artifact")
   out=(dest/pathlib.Path(*p.parts)).resolve()
   if not out.is_relative_to(dest.resolve()):raise RuntimeError("artifact path traversal")
  z.extractall(dest)
def verify_pairs(root):
 for label,v in PAIRS.items():
  w=root/label/"windows";l=root/label/"linux"
  wm=json.loads((w/"windows-binary-manifest.json").read_text())
  lm=json.loads((l/"manifest.json").read_text())
  if wm.get("source_sha")!=v["source"] or lm.get("source_sha")!=v["source"]:
   raise RuntimeError(label+" source mismatch")
  if wm.get("features")!="m0_v4_embedded_go,fec2_product_record":
   raise RuntimeError(label+" compiled features mismatch")
  if lm.get("binary_qualification")!="BUILD_ONLY_NOT_PRODUCT":
   raise RuntimeError(label+" Linux build identity")
  if lm.get("original_go_sha")!="a7a82db31fe736ffedee330795a3234d358f1984":
   raise RuntimeError(label+" original TLS source")
  for fn,key in (("wbd-client-embedded.exe","exe"),("wbd_engine.dll","dll")):
   p=w/fn
   if p.stat().st_size<100000 or sha(p)!=wm["sha256"][key]:
    raise RuntimeError(label+" Windows binary mismatch "+fn)
  for fn in ("wbd-v4-server","wbd-v4-client","libwbd_engine.so"):
   p=l/fn
   if p.stat().st_size<100000 or sha(p)!=lm["sha256"][fn]:
    raise RuntimeError(label+" Linux binary mismatch "+fn)
 return {label:{"source_sha":v["source"],"run_id":v["run"],
               "sha256":{name:sha(root/label/("windows" if name.endswith((".exe",".dll")) else "linux")/name)
                         for name in PRODUCT_FILES}}
         for label,v in PAIRS.items()}
def main():
 root=pathlib.Path("result/wl-public/abba-bin")
 # Exact same build manifests for all legs, no file mixing.
 for label,v in PAIRS.items():
  run=gh_json(f"repos/{REPO}/actions/runs/{v['run']}")
  if run["repository"]["full_name"]!=REPO or run["head_sha"]!=v["source"] or run["status"]!="completed":
   raise RuntimeError(label+" untrusted source run")
  for kind in ("windows","linux"):
   art_id,digest=v[kind]
   meta=gh_json(f"repos/{REPO}/actions/artifacts/{art_id}")
   if meta["workflow_run"]["id"]!=v["run"] or meta["name"]!=(
       f"m0-wl-windows-product-binaries-{v['source']}" if kind=="windows" else "m0-plan024-linux-product"):
    raise RuntimeError(label+" wrong ZIP artifact identity "+kind)
   if meta.get("digest") and meta["digest"]!="sha256:"+digest:
    raise RuntimeError(label+" changed artifact digest")
   zip_path=root/label/(kind+".zip")
   fetch_zip(art_id,digest,zip_path)
   unzip_safe(zip_path,root/label/kind)
   zip_path.unlink()
 manifest=verify_pairs(root)
 (root/"verified-source-pairs.json").write_text(json.dumps(manifest,indent=2)+"\n")
 print("WL_RUST_ABBA_EXACT_COMPILATION_SHA_BOTH_PRODUCTS_VERIFIED",flush=True)
if __name__=="__main__":main()
