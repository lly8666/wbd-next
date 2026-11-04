# PLAN028 H1115 — independent native fixture narrow corrections

Initial x86 Game4FEC6 sibling Action 41802289354 FAIL after original TLS second generation had already committed and old Rust stopped, because `GAME_DELAY_S=.5` on a Bash function was not passed through the later `sudo ip netns exec env` boundary. Bob sent all 32 packets before the source4 change, so the rigorous actual clock bracket assertion correctly rejected it. Propagate only the scoped `GAME_DELAY_S` to the existing inner UDP app; default zero means all old tests retain behavior. No Go/Rust product change; same frozen SOURCE0e47 ELF/hash reused. No fake or manually injected successful markers.

Windows Hyper-V owned NIC preflight Action 41802074389 FAIL, with owned internal vSwitch created and cleaned up and real source-selection guard rejecting initial immediate `Find-NetRoute` result. Wait only for Windows OS selected route readback, preserve source and IP state diagnostics on failure; do not weaken Npcap/TLS requirement or touch runner management uplink. This is environment preflight, not a Windows product PASS. Run the two independent Actions separately, one scenario each; m0-plan012 historical matrix is explicitly skipped via existing `[game-overlap-cold]` guard. H998 limited FAIL and other NOT_RUN preserved.

```feature-impact
{"kind":"none","ids":[],"reason":"H1115 only fixes two independent test-only native fixture expectations; product source unchanged."}
```
