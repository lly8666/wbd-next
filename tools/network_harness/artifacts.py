"""Download a pinned existing build. Verify ZIP digest AND every declared binary."""
import hashlib
import json
import os
import platform
import re
import shutil
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


REQUIRED = {"wbd-v4-client", "wbd-v4-server", "libwbd_engine.so"}


def _elf_and_runner(path, machine):
    with open(path, "rb") as f:
        header = f.read(20)
    if header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != machine:
        raise ValueError(f"ELF architecture mismatch: {path.name}")
    actual = platform.machine().lower()
    allowed = {62: {"x86_64", "amd64"}, 183: {"aarch64", "arm64"}}[machine]
    if actual not in allowed:
        raise ValueError(f"not a native {machine} runner: {actual}")


def _arm_hashes(path):
    hashes = {}
    for line in path.read_text().splitlines():
        # SHA256SUMS is data, not executable shell input. Reject aliases and duplicates.
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match[2] not in REQUIRED or match[2] in hashes:
            raise ValueError("invalid or duplicated ARM64 SHA256SUMS entry")
        hashes[match[2]] = match[1]
    if set(hashes) != REQUIRED:
        raise ValueError("ARM64 SHA256SUMS must cover precisely all three product binaries")
    return hashes


def verify(root, bundle):
    root = Path(root)
    fixed = root / "fixed-kernel-result/manifest.json"
    arm_roots = [r for r in [root, root / "arm64-public-bundle"]
                 if (r / "manifest.json").is_file()]
    if fixed.exists() and arm_roots or len(arm_roots) > 1:
        raise ValueError("ambiguous product artifact format")
    if fixed.exists():
        manifest = json.loads(fixed.read_text())
        if (manifest["source_sha"] != bundle["source"] or manifest["run_id"] != bundle["run_id"]
                or manifest["attempt"] != bundle["attempt"]):
            raise ValueError("x86_64 source/run/attempt mismatch")
        hashes = manifest["binaries_sha256"]
        if not REQUIRED <= hashes.keys():
            raise ValueError("not a public V4 x86_64 CLI bundle")
        binary_root, machine = root / "fixed-build", 62
    elif arm_roots:
        binary_root = arm_roots[0]
        manifest = json.loads((binary_root / "manifest.json").read_text())
        if manifest.get("source") != bundle["source"] or manifest.get("architecture") not in ("aarch64", "arm64"):
            raise ValueError("ARM64 product source or architecture mismatch")
        if "native_fec_acceleration" not in manifest.get("backend_requested", ""):
            raise ValueError("ARM64 acceleration build feature not attested")
        for field in ("go_source", "isa_source"):
            if not re.fullmatch(r"[0-9a-f]{40}", manifest.get(field, "")):
                raise ValueError(f"missing pinned ARM64 {field}")
        origin = root / "_verified-origin.json"
        if not origin.exists():
            raise ValueError("ARM64 requires verified GitHub run/attempt provenance")
        receipt = json.loads(origin.read_text())
        if any(receipt.get(k) != bundle[v] for k, v in
               [("source", "source"), ("run_id", "run_id"), ("attempt", "attempt"), ("artifact_id", "artifact_id")]):
            raise ValueError("ARM64 artifact GitHub run/attempt mismatch")
        if bundle.get("step_attested_failure"):
            if receipt.get("workflow_conclusion") != "failure" or not receipt.get("native_product_build_step_verified"):
                raise ValueError("missing verified recovered product build steps")
        hashes, machine = _arm_hashes(binary_root / "SHA256SUMS"), 183
    else:
        raise ValueError("no supported product artifact manifest")
    for name, digest in hashes.items():
        if Path(name).name != name or "/" in name or "\\" in name or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("unsafe product hash entry")
        path = binary_root / name
        if not path.is_file() or sha(path) != digest:
            raise ValueError(f"binary digest mismatch: {name}")
        _elf_and_runner(path, machine)
        path.chmod(0o700)
        # Normalized path consumed by LinuxExperiment is the original x64 interface.
        normalized = root / "fixed-build" / name
        if machine == 183 and normalized != path and normalized.exists():
            if sha(normalized) != digest:
                raise ValueError(f"normalized ARM64 binary digest mismatch: {name}")
            normalized.chmod(0o700)  # shutil.copyfile strips ELF exec mode.
    return manifest

def attested_recovered_product_build(run, jobs):
    """A narrow, negative default for an already-uploaded native product.

    A failed *post-build* optional unit cannot turn its workflow green. Only
    the original public ARM64 build and upload steps may be marked proven.
    Source/run/attempt/artifact/digest/ELF verification still happens elsewhere.
    """
    if (run.get("path") != ".github/workflows/arm64-public-go-build.yml"
            or run.get("head_branch") != "experiment/network-matrix-tuning"
            or run.get("event") != "push"
            or run.get("status") != "completed"
            or run.get("conclusion") != "failure"
            or jobs.get("total_count") != 2):
        return False
    by_name = {j.get("name"): j for j in jobs.get("jobs", [])}
    if set(by_name) != {"native-go-rust-bundle", "native-linux-netns"}:
        return False
    job = by_name["native-go-rust-bundle"]
    if (job.get("conclusion") != "failure"
            or by_name["native-linux-netns"].get("conclusion") != "skipped"):
        return False
    steps = {s.get("name"): s.get("conclusion") for s in job.get("steps", [])}
    expected = {
        "Exact source native ARM64 original Go and Rust bundle": "success",
        "Verify product parity maximum row 0..19 on native ARM64": "failure",
        "Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02": "success",
    }
    if any(steps.get(name) != outcome for name, outcome in expected.items()):
        return False
    # No unrecognized failing step may be masked.
    return all(outcome != "failure" or name in expected and expected[name] == "failure"
               for name, outcome in steps.items())


def fetch(bundle, root):
    root = Path(root)
    # GitHub-hosted Actions can download an exact cross-run artifact through
    # the first-party artifact transport. This avoids the public ZIP redirect
    # egress gateway, while preserving signed run metadata and every ELF hash.
    prefetched = root / "arm64-public-bundle/manifest.json"
    if root.exists():
        if not root.is_dir() or not prefetched.is_file():
            raise ValueError("unexpected pre-existing artifact directory")
    else:
        root.mkdir(parents=True)
    with get(f'/actions/artifacts/{bundle["artifact_id"]}') as f:
        meta = json.load(f)
    if meta["expired"] or meta["workflow_run"]["id"] != bundle["run_id"]:
        raise ValueError("expired or wrong-run artifact")
    if meta["workflow_run"].get("head_sha") != bundle["source"]:
        raise ValueError("artifact workflow head SHA != product SOURCE")
    with get(f'/actions/runs/{bundle["run_id"]}') as f:
        run = json.load(f)
    if (run.get("head_sha") != bundle["source"] or run.get("run_attempt") != bundle["attempt"]
            or run.get("status") != "completed"):
        raise ValueError("GitHub build run SHA/attempt/status mismatch")
    recovered = bundle.get("step_attested_failure", False)
    if recovered:
        if run.get("conclusion") != "failure":
            raise ValueError("step-attested exception requires actual failed workflow")
        with get(f'/actions/runs/{bundle["run_id"]}/jobs?per_page=100') as f:
            jobs = json.load(f)
        if not attested_recovered_product_build(run, jobs):
            raise ValueError("failed build has no exact step-level product attestation")
    elif run.get("conclusion") != "success":
        raise ValueError("GitHub build run SHA/attempt/status mismatch")
    (root / "_verified-origin.json").write_text(json.dumps({
        "source": bundle["source"], "run_id": run["id"], "attempt": run["run_attempt"],
        "artifact_id": meta["id"], "workflow_conclusion": run["conclusion"],
        "native_product_build_step_verified": bool(recovered or run["conclusion"] == "success")}) + "\n")
    if meta.get("digest") and meta["digest"] != "sha256:" + bundle["sha256"]:
        raise ValueError("GitHub artifact digest mismatch")
    # In the first-party prefetched mode, actions/download-artifact has
    # already transferred and verified the GitHub artifact. We independently
    # pin its published ZIP digest above, exact workflow/source, manifest and
    # all extracted binary hashes below; do not pretend we hashed the ZIP
    # ourselves in this mode.
    if prefetched.is_file():
        manifest = verify(root, bundle)
        arm_root = root / "arm64-public-bundle"
        (root / "fixed-build").mkdir(exist_ok=True)
        for name in REQUIRED:
            destination = root / "fixed-build" / name
            shutil.copyfile(arm_root / name, destination)
            destination.chmod(0o700)
        verify(root, bundle)
        manifest_path = arm_root / "manifest.json"
        return {"artifact": meta["id"], "zip_sha256": bundle["sha256"],
                "zip_hash_proof": "github_digest_plus_first_party_download_action",
                "manifest_sha256": sha(manifest_path),
                "layout": "arm64-sha256sums-first-party-prefetch",
                "run_attempt_verified": True, "manifest": manifest,
                "workflow_conclusion": run["conclusion"],
                "step_attested_failure": bool(recovered)}
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
            if not (item.filename.startswith("fixed-build/") or item.filename == "fixed-kernel-result/manifest.json"
                    or item.filename in ("manifest.json", "SHA256SUMS", *REQUIRED)
                    or item.filename in tuple("arm64-public-bundle/" + n for n in
                         (*REQUIRED, "manifest.json", "SHA256SUMS"))):
                continue
            expanded += item.file_size
            if expanded > 512 * 1024 * 1024:
                raise ValueError("expanded bundle exceeds limit")
            z.extract(item, root)
    manifest = verify(root, bundle)
    arm_root = root if (root / "manifest.json").exists() else root / "arm64-public-bundle"
    if (arm_root / "manifest.json").exists():
        (root / "fixed-build").mkdir(exist_ok=True)
        for name in REQUIRED:
            destination = root / "fixed-build" / name
            shutil.copyfile(arm_root / name, destination)
            destination.chmod(0o700)  # Verified ARM CLI must be executable after normalization.
        verify(root, bundle)  # Same hashes and native ELF after normalization.
        manifest_path = arm_root / "manifest.json"
        layout = "arm64-sha256sums"
    else:
        manifest_path = root / "fixed-kernel-result/manifest.json"
        layout = "fixed-amd64"
    archive.unlink()
    return {"artifact": meta["id"], "zip_sha256": bundle["sha256"],
            "manifest_sha256": sha(manifest_path), "layout": layout,
            "run_attempt_verified": True, "manifest": manifest,
            "workflow_conclusion": run["conclusion"],
            "step_attested_failure": bool(recovered)}
