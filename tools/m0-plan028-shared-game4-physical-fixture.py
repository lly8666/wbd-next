#!/usr/bin/env python3
"""PLAN028 H1160 — switch one qualified original two-Game-cohort fixture
to the NEW shared Normal/Game server entry, leaving clients and physical
switch assertions unchanged. This is an ephemeral single-scene fixture."""
from pathlib import Path
import sys

source = Path("tools/m0-plan028-game-two-groups-real-linux-netns.sh").read_text()
def exactly(old: str, new: str, expected: int = 1) -> None:
    global source
    got = source.count(old)
    if got != expected:
        raise RuntimeError(f"frozen Game4 physical fixture changed: {old[:95]!r}, count={got}, expected={expected}")
    source = source.replace(old, new)

exactly("--tls-cert '$TMP/cert.pem' --tls-key '$TMP/key.pem' --mode \"$MODE\" --game-fec \"$GAME_FEC\"",
        "--tls-cert '$TMP/cert.pem' --tls-key '$TMP/key.pem' --mode shared")
exactly("V4_PUBLIC_GAME_MULTI_SERVER_READY role=server port=443 lanes_per_group=$LANES",
        "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443", 2)
# Existing client Game4 fixed6, original TLS, RTNL source4 switch, physical
# MTU and Bob's continuous 32 UDP, Alice new 64 UDP, and FEC native counters
# are the real unchanged proof. Do NOT fake/replace their markers.
out = Path(sys.argv[1])
out.write_text(source)
out.chmod(0o700)
print("M0_PLAN028_H1160_SHARED_ONE443_GAME4_REAL_PHYSICAL_FIXTURE_READY")
