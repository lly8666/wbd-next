# M0 2026-10-28 — Native WL variable workload and same-VM A/B

**Intent:** User authorized main integration of flexible WL performance harness and real same-VM Go-steady versus Rust NativeOwner A/B: per direction 150Mbps, 300ms one-way, 0% configured loss, 60s.

This batch source adds independent directional offered/delay/loss/kernel rate/mixed UDP packet weights with canonical scenario SHA. Historical N0/P200 untouched. Existing real signed Npcap/Wintun and Linux raw/TUN, original Go TLS and owned WAL/Stop are reused. A=retained Go Normal steady code with opt-in GITHUB_ACTIONS test flag, B=default Rust NativeOwner; both use one source-built Windows EXE/Rust DLL and the same Linux server/drivers, never simultaneous. Sequential A then Stop then B; independent app/cpu/tc records plus CPU/first-delivered-GB comparison are retained. Source-locked Windows EXE/DLL artifacts uploaded for later runs.

**Feature impact:** none on default Normal, Fixed, Auto, Game or Linux product; this is test-only opt-in. Git source integration is not an Actions, product performance or physical PASS. This A is *retained current-source Go steady*, not a claimed historical precompiled EXE. Dedicated native AEAD/copy/queue stage probes remain NOT_MEASURED until separately implemented and qualified.
