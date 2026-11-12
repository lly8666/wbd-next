"""Select whether a push needs the expensive original Windows/WSL2 native smoke.

The parent workflow still runs cheap compile/unit checks for every relevant push.
An unknown/empty diff is treated as requiring the native smoke, not as a skip.
"""
from __future__ import annotations

import argparse
from pathlib import Path

# Actual native OS/packet ownership and protected data-plane code.
# Cold DNS bootstrap, GUI/config, standalone split-policy logic and test-only
# edits should use their scoped tests rather than a whole Windows/WSL2 run.
NATIVE_PREFIXES = (
    "r0/go_overlay/internal/windowsownerlease/",
    "r0/go_overlay/internal/realityfront/bridge_v4_windows_",
)
NATIVE_EXACT = frozenset({
    "r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go",
    "r0/go_overlay/cmd/wbd-client/m0_native_v4_game_windows.go",
    "r0/go_overlay/cmd/wbd-client/m0_native_v4_peer_windows.go",
    "r0/go_overlay/cmd/wbd-client/m0_native_v4_game_rust_peer_windows.go",
    "r0/go_overlay/cmd/wbd-client/m0_native_v4_rust_peer_windows.go",
    "r0/go_overlay/cmd/wbd-client/m0_native_v4_dispatch_windows.go",
    "r0/go_overlay/internal/windowsclient/native_rust_wintun_loan_windows.go",
    "r0/go_overlay/internal/faketcp/npcap_native_handoff_windows.go",
    "crates/wbd-platform/src/windows_native_io.rs",
    "crates/wbd-platform/src/ipv4_tcp.rs",
    "crates/wbd-engine/src/lib.rs",
    "crates/wbd-engine/src/v4_owner_crypto.rs",
    "crates/wbd-engine/src/v4_embedded_go.rs",
})
NATIVE_RUST_PREFIXES = (
    "crates/wbd-engine/src/v4_windows_",
    "crates/wbd-engine/src/v4_game_",
    "crates/wbd-engine/src/v4_fixed_",
)
EXPLICIT_NATIVE_MARKERS = (
    "[wiring-full]", "[m0-native-smoke]", "[m0-real-game-fec]",
    "[plan025-", "[plan026-", "[plan027-", "[plan028-",
)


def is_native_path(path: str) -> bool:
    path = path.strip().replace("\\", "/")
    if not path or path.endswith("_test.go") or path.endswith("_tests.rs"):
        return False
    return (
        path in NATIVE_EXACT
        or any(path.startswith(prefix) for prefix in NATIVE_PREFIXES)
        or any(path.startswith(prefix) and path.endswith(".rs") for prefix in NATIVE_RUST_PREFIXES)
        or path.startswith("r0/go_overlay/internal/windowsclient/native_unified_")
        or path.startswith("r0/go_overlay/internal/windowsclient/native_original_kernel_")
    )


def requires_native_smoke(event: str, changed_paths: list[str], message: str = "") -> bool:
    if event == "workflow_dispatch":
        return True
    if event != "push":
        return True  # Unexpected events never silently suppress native tests.
    if any(marker in message.lower() for marker in EXPLICIT_NATIVE_MARKERS):
        return True
    if not changed_paths:
        return True  # A missing diff is not evidence that native code is unchanged.
    return any(is_native_path(path) for path in changed_paths)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--files", type=Path, required=True)
    parser.add_argument("--message", default="")
    args = parser.parse_args()
    paths = args.files.read_text(encoding="utf-8").splitlines()
    result = requires_native_smoke(args.event, paths, args.message)
    print(f"native_smoke={'true' if result else 'false'}")


if __name__ == "__main__":
    main()
