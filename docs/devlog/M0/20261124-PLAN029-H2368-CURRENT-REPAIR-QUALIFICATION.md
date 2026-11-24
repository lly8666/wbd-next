# H2368 — current Normal-v3 P1 qualification

H2366 45326185486 all seven jobs completed, actual IPv4 LSOv2 ON/OFF/restore. Group a ON 808.464/668.650, OFF 818.089/818.674 Mbps; group b ON 682.030/809.036, OFF 826.710/518.845. ON effect -9.75%/+10.81%, within large runner drift. LSO OFF reaches >800 Mbps on both; missing LSO alone is not an adequate explanation of product gap. No proof of physical hardware execution. No repeated LSO scans.

Restore exact scalar checksum blob from retained H2336 (H2364 lacked whole-product gain). P1 H2294 previously froze pre-repair sources for both platforms; now build exact current Go/Windows Rust and ARM source, same signed NPF/Wintun/TUN, same legacy TX16/64KiB across all three OFF/ON/OFF legs for continuity; no profile-default promotion. Old historical fixtures unaffected unless explicit H2368 selector. Keep real joined stop, FEC off, manifest, driver copied, remote bytes, 160 sparse echo. 1% only this push; 5% workflow updated but not dispatched until first evidence.

```feature-impact
{"kind":"none","ids":[],"reason":"Restore prior equivalent outbound checksum, refresh test-only P1 current-source builds; no wire, feature or product default change."}
```
