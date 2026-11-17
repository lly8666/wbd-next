# Android CN geosite / real isolated DNS UDP/53 initial kernel response rejection (2026-11-17)

SOURCE `bd3109b0e9d3d84f7dc46a39476492c404c790b4`, [real KSU Android16 Action43985292694](https://github.com/lly8666/wbd-next/actions/runs/43985292694), overall **FAIL**. Artifact **14285691055**, ZIP SHA256 `42605b93fb2c70855fa98e5577ab4433ef5d88d3078bcd240e75bb2667b2b509`. This is not retroactively called PASS.

What passed: x86_64/aarch64 Bionic NDK build, full 8,503-rule CN geolocation snapshot in a signed targetSdk37 APK with pinned source SHA and text digest; ordinary Android App → authorized KernelSU UID0; legacy TUN/raw/IPv6 policy routing, actual legacy DNS/TLS, multi-downstream synthetic NAT, manual restore; 10/10 real UID kernel policy checks. New `onWindowFocusChanged` fix worked: actual foreground SplitSettings one-tap DNS button on screen, actual App config saved, and `splitvalidate` executed with a verified independent `CLONE_NEWNET` (different inode, `global_changes=false`). Native output `status=FAIL`, `dns_udp_gate.reason="DNS UDP response wrong transaction/answer/route"`. The rest of the 6-case DNS gate was not completed.

Root cause isolated in `dns_udp_gate::attempt_case`: `socket.recv_from(&mut response)` returns `got` actual payload bytes, but `!response.ends_with(&ANSWER)` checked the entire 4096-byte destination buffer, including unreceived zero padding. Correct validation is `response[..got].ends_with(&ANSWER)`. Preserve source, QNAME, received length, full response equality, transaction ID and DNS answer count checks; return per-case detailed field booleans on failure to avoid ambiguous future errors.

An ordinary Rust unit regression now proves that the same padded buffer fails an incorrect full-buffer trailing-A test but passes the actual received slice test. Re-run the identical real KSU full workflow on the new SOURCE; must get 6/6 isolated kernel UDP/53 query+response checks (4 synthetic Direct, 2 synthetic Tunnel), original global rules/routes exact unchanged, App native JSON success. Live 223.5.5.5/1.1.1.1, system DNS interception, physical hotspot/USB, production WBD TLS, and DirtyFrag temporary root remain **NOT_RUN**, even if this test passes.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix DNS UDP/53 synthetic kernel response validation to use actual recv_from length rather than zero-padded 4096-byte buffer; add regression and detailed failure flags."}
```
