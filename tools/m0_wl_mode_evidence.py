"""Source-locked per-mode Windows↔Linux evidence, no credentials or launch scripts.

Only an explicit allowlist may leave the live result directory; authentication
material, TLS keys, WAL blobs and launch commands cannot enter mode artifacts.
"""
from __future__ import annotations
import json
import pathlib
import re
import hashlib

LOGS=(
 "client.log","server.log","native-link-tcp443.log",
 "windows-app.log","linux-app.log","windows-tcp-app.log","linux-tcp-app.log",
 "auto-adaptive-windows-udp.log","auto-adaptive-linux-udp.log",
 "auto-revision-windows-udp.log","auto-revision-linux-udp.log",
 "wl-n0-windows-app.log","wl-n0-linux-app.log",
 "native-windows-npf.log","native-windows-npf-stderr.log",
)
MEASUREMENTS=("windows-original-go-rust-process-1hz.jsonl",
 "wl-n0-windows-app.json","wl-n0-linux-app.json",
 "wl-n0-netem-after.json","wl-n0-netem-owned.json")
PRIVATE_KEYS=re.compile(r"""(?i)(--(?:password|route-key-hex|tls-key|tls-cert|username|token)[=\s]+)[^\s"']+""")
JSON_SECRETS=re.compile(r"""(?i)("(?:password|route_key_hex|token|secret|private_key)"\s*:\s*")[^"]+(")""")
def redact(text:str)->str:
 text=PRIVATE_KEYS.sub(lambda m:m.group(1)+"[REDACTED]",text)
 return JSON_SECRETS.sub(lambda m:m.group(1)+"[REDACTED]"+m.group(2),text)
# Global native WSL/NPF probes are long-lived while the seven modes
# run sequentially on one VM. Only their mode-time suffix belongs to
# the current result, even when their output file is opened for append.
LIVE_LOGS=frozenset(("native-link-tcp443.log",
 "native-windows-npf.log","native-windows-npf-stderr.log",
 "windows-original-go-rust-process-1hz.jsonl"))
def capture_mode_evidence_baseline(out:pathlib.Path)->dict:
 baseline={}
 for name in LOGS+MEASUREMENTS:
  path=out/name
  if path.is_symlink():
   raise ValueError("refuse symlink evidence file "+name)
  if not path.is_file():continue
  with path.open("rb") as f:
   prefix=f.read(256)
  stat=path.stat()
  baseline[name]=(stat.st_size,stat.st_mtime_ns,stat.st_ino,
                  hashlib.sha256(prefix).hexdigest())
 return baseline

def archive_mode_evidence(out:pathlib.Path, mode:str, source:str,
 result:dict,exit_code:int,baseline:dict|None=None)->pathlib.Path:
 if mode not in ("normal","fixed","auto","game2","game4",
                 "game2-fec","game4-fec","auto-revision","auto-adaptive"):
  raise ValueError("unknown public mode")
 if not re.fullmatch(r"[0-9a-f]{40}",source):
  raise ValueError("missing exact SOURCE")
 target=out/"mode-results"/mode
 target.mkdir(parents=True,exist_ok=True)
 written=[]
 missing=[]
 stale=[]
 # Archive only files changed after the per-mode baseline, not an old
 # mode's shared pathname. When no baseline was supplied (unit/legacy
 # callers), preserve the earlier copy semantics for compatibility.
 # Stable named witness, even when first failure prevented product READY.
 (target/"report.json").write_text(json.dumps(result,indent=2)+"\n")
 written.append("report.json")
 for name in LOGS+MEASUREMENTS:
  path=out/name
  if path.is_symlink():raise ValueError("refuse symlink artifact "+name)
  if not path.is_file():
   missing.append(name)
   continue
  if baseline is not None and name in baseline:
   old_size,old_mtime,old_inode,old_hash=baseline[name]
   stat=path.stat()
   if stat.st_size==old_size and stat.st_mtime_ns==old_mtime:
    stale.append(name)
    continue
   with path.open("rb") as f:
    # Use the original baseline's prefix width. Reading a full 256B
    # after a short (<256B) log is appended would include NEW data in
    # the digest, incorrectly treating append as a replacement.
    prefix=f.read(min(256,old_size))
    same_prefix=hashlib.sha256(prefix).hexdigest()==old_hash
    # Preserve only NEW WSL/NPF/telemetry bytes appended to the
    # original open file; truncated/rotated files use their whole
    # current contents. Non-live logs are produced afresh per mode.
    if (name in LIVE_LOGS and stat.st_ino==old_inode and
        stat.st_size>old_size and same_prefix):
     f.seek(old_size)
    else:
     f.seek(0)
    data=f.read().decode("utf-8","replace")
  else:
   data=path.read_text(encoding="utf-8",errors="replace")
  if not data:
   stale.append(name)
   continue
  (target/name).write_text(redact(data),encoding="utf-8")
  written.append(name)
 summary={"source":source,"mode":mode,
          "exit_code":exit_code,"product_pass":exit_code==0 and
          result.get("mode_public","").startswith("PASS_ACTUAL_"),
          "preserved_allowlist":written,"unavailable":missing,
          "unchanged_from_previous_mode":stale,
          "scope":"SAME_SOURCE_ONE_MODE_REAL_BUSINESS_NOT_PERFORMANCE"}
 manifest=target/"artifact-manifest.json"
 manifest.write_text(json.dumps(summary,indent=2)+"\n")
 return manifest
