"""Bounded Windows N0 Npcap loss observation from existing 1Hz owner logs.

Never copies payload, turns an unknown counter into zero, or compares snapshots
across process generations. Called once immediately before/after a measurement.
"""
import json
from pathlib import Path

MARKER = "WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "

def latest_counter(path):
    p = Path(path)
    if not p.is_file():
        return None
    for line in reversed(p.read_text(encoding="utf-8", errors="replace").splitlines()):
        if MARKER not in line:
            continue
        try:
            row = json.loads(line.split(MARKER, 1)[1])
            count = row["npcap_ingress_local_drops"]
            if type(count) is int and count >= 0:
                return count
        except (ValueError, KeyError, TypeError):
            continue
    return None

def measured_delta(before, after):
    if before is None or after is None or after < before:
        return None
    return after - before
