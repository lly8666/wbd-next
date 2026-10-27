"""Source-locked per-mode Windows↔Linux evidence, no credentials or launch scripts.

Only an explicit allowlist may leave the live result directory; authentication
material, TLS keys, WAL blobs and launch commands cannot enter mode artifacts.
"""
from __future__ import annotations
import json
import pathlib
import re

LOGS=(
 "client.log","server.log","native-link-tcp443.log",
 "windows-app.log","linux-app.log","windows-tcp-app.log","linux-tcp-app.log",
 "auto-adaptive-windows-udp.log","auto-adaptive-linux-udp.log",
 "auto-revision-windows-udp.log","auto-revision-linux-udp.log",
 "wl-n0-windows-app.log","wl-n0-linux-app.log",
)
MEASUREMENTS=("windows-original-go-rust-process-1hz.jsonl",
 "wl-n0-windows-app.json","wl-n0-linux-app.json",
 "wl-n0-netem-after.json","wl-n0-netem-owned.json")
PRIVATE_KEYS=re.compile(r"""(?i)(--(?:password|route-key-hex|tls-key|tls-cert|username|token)[=\s]+)[^\s"']+""")
JSON_SECRETS=re.compile(r"""(?i)("(?:password|route_key_hex|token|secret|private_key)"\s*:\s*")[^"]+(")""")
def redact(text:str)->str:
 text=PRIVATE_KEYS.sub(lambda m:m.group(1)+"[REDACTED]",text)
 return JSON_SECRETS.sub(lambda m:m.group(1)+"[REDACTED]"+m.group(2),text)
def archive_mode_evidence(out:pathlib.Path, mode:str, source:str,
 result:dict,exit_code:int)->pathlib.Path:
 if mode not in ("normal","fixed","auto","game2","game4",
                 "game2-fec","game4-fec","auto-revision","auto-adaptive"):
  raise ValueError("unknown public mode")
 if not re.fullmatch(r"[0-9a-f]{40}",source):
  raise ValueError("missing exact SOURCE")
 target=out/"mode-results"/mode
 target.mkdir(parents=True,exist_ok=True)
 written=[]
 missing=[]
 # Stable named witness, even when first failure prevented product READY.
 (target/"report.json").write_text(json.dumps(result,indent=2)+"\n")
 written.append("report.json")
 for name in LOGS+MEASUREMENTS:
  path=out/name
  if not path.is_file():
   missing.append(name)
   continue
  data=path.read_text(encoding="utf-8",errors="replace")
  (target/name).write_text(redact(data),encoding="utf-8")
  written.append(name)
 summary={"source":source,"mode":mode,
          "exit_code":exit_code,"product_pass":exit_code==0 and
          result.get("mode_public","").startswith("PASS_ACTUAL_"),
          "preserved_allowlist":written,"unavailable":missing,
          "scope":"SAME_SOURCE_ONE_MODE_REAL_BUSINESS_NOT_PERFORMANCE"}
 manifest=target/"artifact-manifest.json"
 manifest.write_text(json.dumps(summary,indent=2)+"\n")
 return manifest
