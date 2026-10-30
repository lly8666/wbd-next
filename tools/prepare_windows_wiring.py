"""Shared exact-source Windows assembly for cheap compile and native full CI.

No driver installation or product execution. --check-only needs no legacy clone.
The full path uses the same assembler, pinned original Go and bridge file list
that m0-wl-public-normal-full.yml used before preflight/full separation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = "a7a82db31fe736ffedee330795a3234d358f1984"
MANIFEST = "r0/go_overlay/assembly/manifest-plan020-m0.json"
# bridge_v4_windows_fixed_stream.go now lives in the one exact manifest.
# Keep the test bridge in this list; never install the same source twice.
EXTRA_BRIDGES = {
    "realityfront": (
        "admission_v4.go", "bridge_v4_windows_private_owner.go",
        "bridge_v4_windows_game_group.go", "bridge_v4_windows_game_server_group.go",
        "bridge_v4_windows_game_group_test.go",
        "bridge_v4_windows_fec2_abi_status_test.go", "bridge_v4_windows_auto_cohort_test.go",
        "bridge_v4_windows_fec2_owner.go", "bridge_v4_windows_fixed_stream_test.go",
        "bridge_v4_windows_wintun_lease.go", "bridge_v4_windows_wintun_lease_test.go",
        "bridge_v4_windows_scoped_client.go",
        "bridge_v4_windows_m2_batch_preflight_test.go",
        "bridge_v4_windows_open_validated_test.go",
        "bridge_v4_windows_m2_effective_test.go",
    ),
    "windowsownerlease": (
        "created_wintun_windows.go", "scoped_original_tls_native_wintun_windows.go",
    ),
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def check_spec(spec, read_source):
    need(spec["legacy_source"] == ORIGINAL, "original Go SOURCE changed")
    for op in spec["operations"]:
        if op.get("overlay_path"):
            need(blob(read_source(op["overlay_path"])) == op["result_blob"],
                 "assembly blob mismatch: " + op["overlay_path"])


def replace_original_once(data, needle, replacement, path):
    need(data.count(needle) == 1, "frozen Npcap RX buffer anchor changed: " + path)
    return data.replace(needle, replacement)


def install_pinned_npcap_kernel_capture_buffer(root, legacy, output):
    """Patch ONLY the source-frozen Actions checkout, never the original Go repo.

    Npcap pcap_open_live defaults to a 1MiB kernel ring; pcap_setbuff must
    run before the first Go reader or handoff, not while pending M3 is live.
    TX-only cloned handles retain 1MiB via overlay NativeCaptureConfig.
    """
    config = legacy / "internal/faketcp/npcap.go"
    win = legacy / "internal/faketcp/npcap_windows.go"
    for file in (config, win):
        relative = str(file.relative_to(legacy)).replace("\\", "/")
        original = git(legacy, "show", ORIGINAL + ":" + relative)
        need(file.read_bytes() == original, "original Npcap source changed: " + relative)
    config_before = config.read_bytes()
    config_after = replace_original_once(config_before,
        b"\tPersona    PacketPersona\n\tGeneration uint64\n}",
        b"\tPersona    PacketPersona\n\tGeneration uint64\n\tCaptureBufferBytes int // zero=16MiB original RX; TX clone=1MiB\n}",
        "npcap.go")
    win_before = win.read_bytes()
    marker = b"\tif setMinToCopy, err := dll.FindProc(\"pcap_setmintocopy\"); err == nil {"
    injection = (
        b"\t// Before ANY native RX or TLS business packet: enlarge the NPF kernel\n"
        b"\t// capture ring; resetting it after the Go-to-Rust handoff loses M3.\n"
        b"\tcaptureBytes := cfg.CaptureBufferBytes\n"
        b"\tif captureBytes == 0 { captureBytes = 16 << 20 }\n"
        b"\tif captureBytes < 1<<20 || captureBytes > 16<<20 {\n"
        b"\t\treturn nil, fmt.Errorf(\"Npcap kernel capture buffer outside owned bounds: %d\", captureBytes)\n"
        b"\t}\n"
        b"\tsetBuf, err := dll.FindProc(\"pcap_setbuff\")\n"
        b"\tif err != nil { return nil, fmt.Errorf(\"Npcap pcap_setbuff unavailable: %w\", err) }\n"
        b"\tif rc, _, _ := setBuf.Call(handle, uintptr(captureBytes)); int32(rc) != 0 {\n"
        b"\t\treturn nil, fmt.Errorf(\"Npcap pcap_setbuff %d bytes failed: %s\", captureBytes, pcapError(getErr, handle))\n"
        b"\t}\n"
        b"\tfmt.Printf(\"WBD_WINDOWS_NPCAP_KERNEL_BUFFER_ACCEPTED bytes=%d\\n\", captureBytes)\n"
    )
    win_after = replace_original_once(win_before, marker, injection + marker, "npcap_windows.go")
    config.write_bytes(config_after)
    win.write_bytes(win_after)
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"scope":"ACTION_CHECKOUT_ONLY_ORIGINAL_GO_PINNED",
       "original_source":ORIGINAL,
       "pcap_default_ring_bytes":1<<20,"rx_ring_requested_bytes":16<<20,
       "tx_bpf_rejected_clone_ring_bytes":1<<20,
       "api":"Npcap pcap_setbuff before pcap_setmode/BPF/first packet",
       "patched_file_sha256":{
         "internal/faketcp/npcap.go":hashlib.sha256(config_after).hexdigest(),
         "internal/faketcp/npcap_windows.go":hashlib.sha256(win_after).hexdigest()}}
    (output/"windows-npcap-ring-source.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt

def prepare(root, legacy, output, source, spec):
    need(git(legacy, "rev-parse", "HEAD").decode().strip() == ORIGINAL, "legacy checkout SOURCE changed")
    # Normalize bytes from Git just as the original workflow did; Windows
    # checkout newline conversion must not change frozen assembly hashes.
    for op in spec["operations"]:
        if op["kind"] == "replace":
            data = git(legacy, "show", ORIGINAL + ":" + op["path"])
            need(blob(data) == op["original_blob"], "original blob mismatch: " + op["path"])
            target = legacy / op["path"]
            need(target.is_file(), "missing replacement target")
            target.write_bytes(data)
        if op.get("overlay_path"):
            (root / op["overlay_path"]).write_bytes(git(root, "show", source + ":" + op["overlay_path"]))
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([os.sys.executable, str(root / "r0/go_overlay/assembly/assemble.py"),
                    "--legacy-root", str(legacy), "--overlay-root", str(root),
                    "--manifest", str(root / MANIFEST), "--receipt", str(output / "assembly.json")], check=True)
    install_pinned_npcap_kernel_capture_buffer(root, legacy, output)
    for part, names in EXTRA_BRIDGES.items():
        dest = legacy / "internal" / part
        dest.mkdir(parents=True, exist_ok=True)
        for name in names:
            relative = "r0/go_overlay/internal/" + part + "/" + name
            target = dest / name
            need(not target.exists(), "competing original/overlay owner: " + relative)
            data = git(root, "show", source + ":" + relative)
            need(len(data) > 60, "empty bridge: " + relative)
            need(b"package realityfront" in data if name == "admission_v4.go"
                 else data.startswith(b"//go:build windows"), "wrong bridge target: " + relative)
            target.write_bytes(data)
    for path in ("internal/windowsownerlease/original_tls_native_product_windows.go",
                 "internal/windowsclient/native_real_product_service_windows.go",
                 "internal/windowsclient/native_udp_kernel_driver_windows.go"):
        need((legacy / path).is_file(), "product assembly missing: " + path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--legacy-root", type=Path, default=ROOT / "legacy")
    parser.add_argument("--output", type=Path, default=ROOT / "result")
    args = parser.parse_args()
    source = git(ROOT, "rev-parse", "HEAD").decode().strip()
    need(source == os.environ.get("GITHUB_SHA", source), "checkout differs from event SOURCE")
    spec = json.loads(git(ROOT, "show", source + ":" + MANIFEST))
    check_spec(spec, lambda path: git(ROOT, "show", source + ":" + path))
    if not args.check_only:
        prepare(ROOT, args.legacy_root.resolve(), args.output.resolve(), source, spec)
    print(json.dumps({"source": source, "original_go": ORIGINAL,
                      "scope": "manifest_only" if args.check_only else "assembly_only",
                      "result": "PASS", "product_tests": "NOT_RUN"}))


if __name__ == "__main__":
    main()
