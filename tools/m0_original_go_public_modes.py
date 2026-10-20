#!/usr/bin/env python3
"""Adapt pinned original-Go real 5-netns two-process app to public V3 modes.

Only adjust real public CLI flags, app duration and optional kernel tc netem.
No mock transport or test-only Go build. Original exact source remains pinned.
"""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--original", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--mode", choices=["fixed", "auto", "game2", "game4"], required=True)
p.add_argument("--expected-sha256", required=True)
args = p.parse_args()
source = args.original.read_bytes()
got = hashlib.sha256(source).hexdigest()
if got != args.expected_sha256:
    p.error("pinned original-GO real process fixture SHA changed")
s = source.decode()
lanes = {"fixed": 1, "auto": 1, "game2": 2, "game4": 4}[args.mode]
parity = {"fixed": 4, "auto": 20, "game2": 0, "game4": 0}[args.mode]
loss = 1 if args.mode in ("fixed", "auto") else 0
def exactly_once(before, after):
    global s
    if s.count(before) != 1:
        p.error("original public client/server fixture anchor changed: " + before[:70])
    s = s.replace(before, after)
exactly_once("start_traffic main 8 .03 .03", "start_traffic main 14 .08 .08")
for side in ("server", "client"):
    original_lines = [line for line in s.splitlines()
        if side + '_args+=(--config "$ART/' + side + '-config.json"' in line]
    if len(original_lines) != 1 or not original_lines[0].endswith(")"):
        p.error("original formal Go " + side + " CLI config anchor changed")
    old = original_lines[0]
    new = old[:-1] + ' --lanes "$LANES"'
    if args.mode == "auto" and side == "client":
        # V3 policy requires client auto parity=0; server provides max=20.
        # Keep original per-peer two-sided CLI FEC contract intact.
        if new.count('--fec-parity "$FEC"') != 1:
            p.error("original client parity CLI anchor changed")
        new = new.replace('--fec-parity "$FEC"', "--fec-parity 0")
        new += " --fec-mode auto"
    new += ")"
    exactly_once(old, new)
if loss:
    for dev in ("rsrv", "rcli"):
        before = "tc qdisc add dev " + dev + " root netem limit 50000 delay 50ms"
        exactly_once(before, before + " loss 1%")
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(s)
args.output.chmod(0o700)
identity = {
    "original_fixture_sha256": got,
    "executed_fixture_sha256": hashlib.sha256(s.encode()).hexdigest(),
    "mode": args.mode, "lanes": lanes, "parity": parity, "loss": loss,
    "build_tags": [], "product_runtime": "old-Go-V3",
    "V4_Rust_FEC2_Game": "NOT_CONNECTED",
}
(args.output.parent / "source-lock.json").write_text(json.dumps(identity, indent=2) + "\n")
print("M0_FORMAL_OLD_GO_MODE_FIXTURE_SOURCE_LOCK " + json.dumps(identity))
