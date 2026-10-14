#!/usr/bin/env python3
"""Exact-SOURCE, fail-closed M0 overlay into pinned original Go callsites.

Overlay applies during Actions, NEVER mutates the public old repository.
Each file's original Git blob SHA-1 and each insertion anchor are checked
before any write. Adds a disabled-but-selectable V4 mode; no feature advertising.
"""
import hashlib
from pathlib import Path
import shutil
import sys

ROOT = Path("legacy")
ORIGINAL_BLOBS = {
    "internal/runtimeentry/lifecycle.go": "f574fe9eb506c1bc66ef27775b1aa313b95b713c",
    "cmd/wbd-client/main_linux.go": "b239b92006504500c76fb9148f735c484a0f011c",
    "cmd/wbd-server/main_linux.go": "930976ec6b2d7fa82f98378c7aa985fb4e8e4363",
}


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_one(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise ValueError(f"{label} expected one original SOURCE anchor; got {count}")
    return src.replace(old, new, 1)


def patch_lifecycle(source):
    source = replace_one(source,
        "type TunnelClientConfig struct {\n",
        "type TunnelClientConfig struct {\n\t// 0 preserves exact legacy direct API behavior; 3 opts explicitly into\n\t// protected V3; 4 is rejected until a real Rust data engine exists.\n\tRequestedRecordVersion uint16\n",
        "TunnelClientConfig",
    )
    source = replace_one(source,
        "func DialTunnelClient(ctx context.Context, cfg TunnelClientConfig) (*TunnelClient, error) {\n",
        "func DialTunnelClient(ctx context.Context, cfg TunnelClientConfig) (*TunnelClient, error) {\n"
        "\t// Must run before opening a raw socket, TUN, lane, or changing routing.\n"
        "\tif _, err := R0EffectiveClientAdmission(cfg.RequestedRecordVersion, cfg.Admission.Policy); err != nil {\n"
        "\t\treturn nil, err\n\t}\n",
        "DialTunnelClient",
    )
    source = replace_one(source,
        "type LifecycleServerConfig struct {\n",
        "type LifecycleServerConfig struct {\n\tRequestedRecordVersion uint16\n",
        "LifecycleServerConfig",
    )
    source = replace_one(source,
        "func NewLifecycleServer(cfg LifecycleServerConfig) (*LifecycleServer, error) {\n",
        "func NewLifecycleServer(cfg LifecycleServerConfig) (*LifecycleServer, error) {\n"
        "\t// Admission mode is checked before listener/TUN/association allocation.\n"
        "\tif _, err := R0EffectiveServerAdmission(cfg.RequestedRecordVersion, cfg.Admission.RequireV3); err != nil {\n"
        "\t\treturn nil, err\n\t}\n",
        "NewLifecycleServer",
    )
    return source


def patch_client(source):
    source = replace_one(source,
        '\t\tconfigPath         = flag.String("config", "", "JSON configuration file; CLI flags override matching keys")',
        '\t\tconfigPath         = flag.String("config", "", "JSON configuration file; CLI flags override matching keys")\n'
        '\t\tadmissionVersion   = flag.Int("admission-version", 3, "requested protected record version; V3 default; V4 unavailable until Rust data plane/ABI is qualified")',
        "client flag",
    )
    source = replace_one(source,
        '\tif *controlPaddingMax < 0 || *controlPaddingMax > 16384 {\n',
        '\t// This runs before loading identities or touching network devices.\n'
        '\tif *admissionVersion == 4 {\n\t\treturn runtimeentry.ErrR0V4DataPlaneUnavailable\n\t}\n'
        '\tif *admissionVersion != 3 {\n\t\treturn runtimeentry.ErrR0AdmissionVersion\n\t}\n'
        '\tif *controlPaddingMax < 0 || *controlPaddingMax > 16384 {\n',
        "client early gate",
    )
    source = replace_one(source,
        '\trequestedPolicy, err := realityfront.PolicyForClientWithInitialAndCipher(*lanes, *fecMode, *fecParity, *fecMinParity, *fecStartParity, suite)\n'
        '\tif err != nil { return err }',
        '\trequestedPolicy, err := realityfront.PolicyForClientWithInitialAndCipher(*lanes, *fecMode, *fecParity, *fecMinParity, *fecStartParity, suite)\n'
        '\tif err != nil { return err }\n'
        '\tif _, err := runtimeentry.R0EffectiveClientAdmission(uint16(*admissionVersion), requestedPolicy); err != nil { return err }',
        "client policy gate",
    )
    source = replace_one(source,
        '\t\tObserveTiming: observeClientStageTiming,\n',
        '\t\tObserveTiming: observeClientStageTiming,\n\t\tRequestedRecordVersion: uint16(*admissionVersion),\n',
        "client real DialTunnelClient callsite",
    )
    return source


def patch_server(source):
    source = replace_one(source,
        '\t\tconfigPath         = flag.String("config", "", "JSON configuration file; CLI flags override matching keys")',
        '\t\tconfigPath         = flag.String("config", "", "JSON configuration file; CLI flags override matching keys")\n'
        '\t\tadmissionVersion   = flag.Int("admission-version", 3, "requested protected record version; V3 default; V4 unavailable until Rust data plane/ABI is qualified")',
        "server flag",
    )
    source = replace_one(source,
        '\tif *controlPaddingMax < 0 || *controlPaddingMax > 16384 {\n',
        '\t// Gate before TLS, network plan, TUN, or socket allocation.\n'
        '\tif *admissionVersion == 4 {\n\t\treturn runtimeentry.ErrR0V4DataPlaneUnavailable\n\t}\n'
        '\tif *admissionVersion != 3 {\n\t\treturn runtimeentry.ErrR0AdmissionVersion\n\t}\n'
        '\tif *controlPaddingMax < 0 || *controlPaddingMax > 16384 {\n',
        "server early gate",
    )
    source = replace_one(source,
        '\t\tout := map[string]string{"derived-inner-tun-mtu": fmt.Sprint(innerMTU)}',
        '\t\tout := map[string]string{\n'
        '\t\t\t"derived-inner-tun-mtu": fmt.Sprint(innerMTU),\n'
        '\t\t\t"effective-admission-version": "3",\n'
        '\t\t\t"v4-capabilities": "not-implemented",\n'
        '\t\t}',
        "server effective --check-config output",
    )
    source = replace_one(source,
        '\tserver, err = runtimeentry.NewLifecycleServer(runtimeentry.LifecycleServerConfig{\n',
        '\tserver, err = runtimeentry.NewLifecycleServer(runtimeentry.LifecycleServerConfig{\n'
        '\t\tRequestedRecordVersion: uint16(*admissionVersion),\n',
        "server real NewLifecycleServer callsite",
    )
    return source


def main():
    patches = {
        "internal/runtimeentry/lifecycle.go": patch_lifecycle,
        "cmd/wbd-client/main_linux.go": patch_client,
        "cmd/wbd-server/main_linux.go": patch_server,
    }
    prepared = {}
    for path, transform in patches.items():
        target = ROOT / path
        source = target.read_bytes()
        if git_blob_sha(source) != ORIGINAL_BLOBS[path]:
            raise ValueError(f"OLD SOURCE drift in {path}: got {git_blob_sha(source)}")
        text = source.decode("utf-8")
        result = transform(text)
        prepared[path] = result
    # All old files checked; only then change files inside transient checkout.
    for path, result in prepared.items():
        target = ROOT / path
        target.write_text(result)
        print(f"patched exact pinned Go callsite: {path}")
    overlays = [
        "internal/realityfront/admission_v4.go",
        "internal/runtimeentry/r0_admission_mode.go",
        "internal/runtimeentry/r0_admission_mode_test.go",
    ]
    for path in overlays:
        source = Path("r0/go_overlay") / path
        shutil.copyfile(source, ROOT / path)
        print(f"installed Go overlay: {path}")


if __name__ == "__main__":
    main()
