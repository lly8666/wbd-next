#!/usr/bin/env python3
"""PLAN028 focused SOURCE-frozen Normal FEC path tests only.

Do not modify the tracked mature netns harness or product binaries: create
an ephemeral extension only in this job to add real underlay switching for
Normal Fixed and Auto, with the correct old+new UDP echo accounting.
"""
from pathlib import Path
import hashlib
import sys

source = Path("tools/m0-v4-public-real-linux-netns.sh")
raw = source.read_text(encoding="utf-8")
updates = (
    (
        'if [[ "$AUTO_IP" == 1 && "$MODE" != normal && "$MODE" != game4 && "$MODE" != game2 ]];then\n'
        '  echo "PLAN028 auto-IP fixture supports Normal, Game2 and Game4" >&2;exit 2\nfi',
        'if [[ "$AUTO_IP" == 1 && "$MODE" != normal && "$MODE" != fec-fixed && "$MODE" != fec-auto && "$MODE" != game4 && "$MODE" != game2 ]];then\n'
        '  echo "PLAN028 source-locked auto-IP fixture requires Normal/Fixed/Auto/Game2/Game4" >&2;exit 2\nfi',
    ),
    (
        'ECHO_PACKETS="$PACKETS"\nif [[ "$PATH_SWITCH" == 1 ]];then ECHO_PACKETS=10;fi',
        '# For original Normal FEC Fixed/Auto, first phase offers 64 real UDP.\n'
        '# A later A-to-B switch must not close the echo app after 10.\n'
        'ECHO_PACKETS="$PACKETS"\nif [[ "$PATH_SWITCH" == 1 ]];then ECHO_PACKETS=$((PACKETS+5));fi',
    ),
    (
        'READER_MIN_PACKETS="$PACKETS"\n  if [[ "$PATH_SWITCH" == 1 ]];then READER_MIN_PACKETS=10;fi',
        'READER_MIN_PACKETS="$PACKETS"\n  if [[ "$PATH_SWITCH" == 1 ]];then READER_MIN_PACKETS=$((PACKETS+5));fi',
    ),
    (
        """  python3 - "$TMP" "$MODE" <<'PY'
import pathlib,re,sys
root=pathlib.Path(sys.argv[1]);selected=sys.argv[2]
mode={"fec-fixed":"fixed","fec-auto":"auto"}[selected]
for role in ("client","server"):""",
        """  python3 - "$TMP" "$MODE" "$AUTO_IP" <<'PY'
import pathlib,re,sys
root=pathlib.Path(sys.argv[1]);selected=sys.argv[2]
mode={"fec-fixed":"fixed","fec-auto":"auto"}[selected]
# The original multi-session server owns shared Rust TUN and emits
# per-session Stop, not a bogus singleton per-role FEC policy readback.
# Its real 69 packets / single reader / precise Stop are asserted below.
roles=("client",) if sys.argv[3]=="1" else ("client","server")
for role in roles:""",
    ),
)
for before, after in updates:
    if raw.count(before) != 1:
        raise RuntimeError("frozen original netns harness changed: required anchor missing/duplicated")
    raw = raw.replace(before, after, 1)
out = Path(sys.argv[1])
out.write_text(raw, encoding="utf-8")
out.chmod(0o700)
print(
    "M0_PLAN028_FEC_PATH_EPHEMERAL_FIXTURE_READY",
    "sha256=" + hashlib.sha256(out.read_bytes()).hexdigest(),
    "base_original_unchanged=1",
    flush=True,
)
