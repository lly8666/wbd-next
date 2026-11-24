#!/usr/bin/env python3
"""Build the PLAN030 portable server package from the existing exact native bundle."""
import hashlib,json,os,pathlib,platform,shutil,tarfile
root=pathlib.Path.cwd()
bundle=root/"linux-plan029-public-bundle"
m=json.loads((bundle/"manifest.json").read_text())
assert m["source_sha"]==os.environ["GITHUB_SHA"]
assert m["architecture"]==platform.machine()
for name,checksum in m["sha256"].items():
    assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==checksum
out=root/"plan030-package"
out.mkdir(exist_ok=False)
for name in ("wbd-v4-server","libwbd_engine.so"):
    shutil.copy2(bundle/name,out/name)
shutil.copy2(root/"deploy/plan030/wbd-next",out/"wbd-next")
(out/"wbd-next").chmod(0o755)
(out/"README.txt").write_text("WBD Next PLAN030\n解压后 sudo ./wbd-next；首次安装按菜单设置账号。\n自动化：sudo ./wbd-next install --config /path/server.json\n启动后 sudo wbd-next status / clients；sudo wbd-next uninstall --yes。\nSOURCE及架构见manifest.json。尚未通过相应功能测试的包不作正式交付。\n")
names=("wbd-next","wbd-v4-server","libwbd_engine.so","README.txt")
m["sha256"]={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in names}
m["scope"]="PLAN030_NATIVE_SERVER_PACKAGE_CANDIDATE"
(out/"manifest.json").write_text(json.dumps(m,indent=2)+"\n")
(out/"SHA256SUMS").write_text("".join(f"{hashlib.sha256((out/n).read_bytes()).hexdigest()}  {n}\n" for n in (*names,"manifest.json")))
with tarfile.open(root/"wbd-next-plan030-server.tar.gz","w:gz") as t:
    t.add(out,arcname="wbd-next")
