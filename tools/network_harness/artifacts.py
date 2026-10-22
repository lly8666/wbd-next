"""Download a pinned existing build. Verify ZIP digest AND every declared binary."""
import hashlib
import json
import os
import stat
import urllib.request
import zipfile
from pathlib import Path

REPO = "lly8666/wbd-next"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


def get(path):
    url = "https://api.github.com/repos/" + REPO + path
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
        "User-Agent": "wbd-network-harness", "Authorization": "Bearer " + os.environ["GH_TOKEN"]})
    return urllib.request.build_opener(NoAuthRedirect()).open(req, timeout=90)


def verify(root, bundle):
    manifest = json.loads((root / "fixed-kernel-result/manifest.json").read_text())
    if (manifest["source_sha"] != bundle["source"] or manifest["run_id"] != bundle["run_id"]
            or manifest["attempt"] != bundle["attempt"]):
        raise ValueError("build manifest source/run/attempt mismatch")
    required = {"wbd-v4-client", "wbd-v4-server", "libwbd_engine.so"}
    hashes = manifest["binaries_sha256"]
    if not required <= hashes.keys():
        raise ValueError("not a public V4 CLI bundle")
    for name, digest in hashes.items():
        if Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("unsafe manifest binary name")
        path = root / "fixed-build" / name
        if sha(path) != digest:
            raise ValueError(f"binary digest mismatch: {name}")
        path.chmod(0o700)
    # Reject a wrong platform before executing downloaded code.
    for name in required:
        with open(root / "fixed-build" / name, "rb") as f:
            header = f.read(20)
        if header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != 62:
            raise ValueError("this adapter requires Linux amd64 ELF")
    return manifest


def fetch(bundle, root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    with get(f'/actions/artifacts/{bundle["artifact_id"]}') as f:
        meta = json.load(f)
    if meta["expired"] or meta["workflow_run"]["id"] != bundle["run_id"]:
        raise ValueError("expired or wrong-run artifact")
    if meta.get("digest") and meta["digest"] != "sha256:" + bundle["sha256"]:
        raise ValueError("GitHub artifact digest mismatch")
    archive = root / "artifact.zip"
    with get(f'/actions/artifacts/{bundle["artifact_id"]}/zip') as src, archive.open("wb") as dst:
        total = 0
        while data := src.read(1024 * 1024):
            total += len(data)
            if total > 512 * 1024 * 1024:
                raise ValueError("artifact exceeds 512 MiB bound")
            dst.write(data)
    if sha(archive) != bundle["sha256"]:
        raise ValueError("downloaded artifact ZIP digest mismatch")
    with zipfile.ZipFile(archive) as z:
        expanded = 0
        for item in z.infolist():
            path = Path(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("unsafe ZIP entry")
            # Ignore old test logs. Only consume the declared binaries and manifest.
            if not (item.filename.startswith("fixed-build/") or item.filename == "fixed-kernel-result/manifest.json"):
                continue
            expanded += item.file_size
            if expanded > 512 * 1024 * 1024:
                raise ValueError("expanded bundle exceeds limit")
            z.extract(item, root)
    manifest = verify(root, bundle)
    archive.unlink()
    return {"artifact": meta["id"], "zip_sha256": bundle["sha256"],
            "manifest_sha256": sha(root / "fixed-kernel-result/manifest.json"),
            "manifest": manifest}
