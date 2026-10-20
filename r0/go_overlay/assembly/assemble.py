#!/usr/bin/env python3
"""PLAN-008 exact old-Go product overlay assembler (no network, no fallback).
This runs *only* against a separate pinned legacy checkout in Actions.
The output remains the original Go module: no duplicate parameter catalog,
GUI implementation, TLS, owner, routing, lifecycle or DATAPATH clone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def git_head(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def within(root: Path, name: str) -> Path:
    if (not name or name.startswith("/") or "\\" in name or
            any(part in ("", ".", "..") for part in name.split("/"))):
        raise ValueError("invalid relative assembly path")
    resolved = root.joinpath(*name.split("/"))
    if not resolved.resolve(strict=False).is_relative_to(root.resolve()):
        raise ValueError("path outside staging root")
    cursor = resolved.parent
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError("symbolic parent disallowed")
        cursor = cursor.parent
    if resolved.is_symlink():
        raise ValueError("symbolic source disallowed")
    return resolved


def plan(legacy: Path, overlay: Path, spec: dict) -> tuple[list, dict]:
    if spec.get("schema_version") != 1 or spec.get("legacy_source") != git_head(legacy):
        raise ValueError("legacy SOURCE not pinned")
    if not (overlay / "r0" / "source-lock.json").is_file():
        raise ValueError("not a wbd-next overlay checkout")
    actual = git_head(overlay)
    if len(actual) != 40:
        raise ValueError("invalid overlay SOURCE")
    # One pinned donor batch; keep donor provenance distinct from the
    # worker's final overlay blob. This does not repin the original Go tree.
    donor = spec.get("windows_donor_source")
    donor_rows = [e for e in spec["operations"] if "donor_blob" in e]
    if donor is not None:
        if not isinstance(donor,str) or len(donor)!=40 or len(donor_rows)!=12:
            raise ValueError("exact Windows donor source/12-file batch missing")
        if len({e["path"] for e in donor_rows})!=12 or any(
            not e["path"].startswith("internal/windowsclient/")
            or e.get("overlay_path")!="r0/go_overlay/"+e["path"]
            or e.get("donor_source")!=donor for e in donor_rows
        ):
            raise ValueError("Windows donor paths/source must be exact original subset")
    elif donor_rows:
        raise ValueError("unreviewed donor file without source")
    seen = set()
    staged = []
    receipts = []
    for e in spec["operations"]:
        target = e["path"]
        if target in seen:
            raise ValueError("duplicate assembly target: " + target)
        seen.add(target)
        dst = within(legacy, target)
        if e["kind"] == "create":
            if dst.exists() or dst.is_symlink():
                raise ValueError("create target already exists: " + target)
            src = within(overlay, e["overlay_path"])
            data = src.read_bytes()
            if len(data) > 1048576:
                raise ValueError("oversized overlay file")
            prior = None
            result = data
        elif e["kind"] == "replace":
            if not dst.is_file():
                raise ValueError("replace target missing: " + target)
            data = dst.read_bytes()
            prior = blob_sha(data)
            if prior != e["original_blob"]:
                raise ValueError("original blob mismatch: " + target)
            if "overlay_path" in e:
                # Windows donor exact full-file replacement. Both the
                # ORIGINAL Git blob and donor/final bytes must match.
                if e.get("patches") is not None:
                    raise ValueError("donor full file cannot also use patches")
                src = within(overlay, e["overlay_path"])
                result = src.read_bytes()
                if len(result) > 1048576:
                    raise ValueError("oversized replacement overlay")
            else:
                text = data.decode("utf-8")
                for item in e["patches"]:
                    before, after = item["find"], item["replace"]
                    if text.count(before) != item.get("count", 1):
                        raise ValueError("non-exact replacement anchor in: " + target)
                    text = text.replace(before, after)
                result = text.encode("utf-8")
        else:
            raise ValueError("unknown manifest operation")
        got = blob_sha(result)
        if "donor_blob" in e and got != e["donor_blob"]:
            raise ValueError("Windows exact pinned donor blob mismatch: " + target)
        if got != e["result_blob"]:
            raise ValueError("overlay result blob mismatch: " + target)
        staged.append((dst, result))
        receipts.append(dict(path=target, kind=e["kind"], original_blob=prior,
                             result_blob=got, bytes=len(result),
                             donor_blob=e.get("donor_blob")))
    return staged, dict(schema_version=1, legacy_source=spec["legacy_source"],
                        overlay_source=actual, rust_source=spec["rust_source"],
                        rust_source_note="reference_only_not_actual_linked_ABI",
                        windows_donor_source=donor,
                        donor_file_count=len(donor_rows),
                        effective_catalog="docs/PARAMETERS.json", result="VALIDATED",
                        files=receipts, actual_product_engine="NOT_WIRED",
                        physical="NOT_RUN")


def assemble(legacy: Path, overlay: Path, manifest: Path, receipt: Path, dry_run=False):
    legacy, overlay = legacy.resolve(strict=True), overlay.resolve(strict=True)
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    writes, result = plan(legacy, overlay, spec)  # all-or-nothing preflight
    if not dry_run:
        for dst, data in writes:
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(dst.name + ".fec2-staging")
            if tmp.exists():
                raise ValueError("leftover temporary assembly file")
            with tmp.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, dst)
        result["result"] = "APPLIED_TO_PINNED_TEMP_CLONE"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--legacy-root", type=Path, required=True)
    p.add_argument("--overlay-root", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    try:
        assemble(a.legacy_root, a.overlay_root, a.manifest, a.receipt, a.dry_run)
    except (ValueError, OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        print("FEC2_ASSEMBLY_REJECTED: " + str(exc), file=sys.stderr)
        sys.exit(2)
