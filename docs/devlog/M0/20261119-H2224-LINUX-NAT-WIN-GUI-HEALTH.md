# H2224 — Linux auto-owned NAT / WinForms native quality and READY / randomized cold Health
Source-locked code **26fd4cd59bc53a97e2991215ad2ec1ddcae8d0f2**; [CI 44564552571](https://github.com/lly8666/wbd-next/actions/runs/44564552571) **2/2 SUCCESS** (Windows original Go/Rust + 426 WinForms checks; Linux ARM64 original Go/Rust netns 3-client NAT/TUN/Stop + exact Go and Rust tests). Artifact digests and explicit NOT_RUN in [evidence](../../evidence/M0/PLAN029-H2224-LINUX-SERVER-NAT-WIN-GUI-COLD-HEALTH-NATIVE-SCOPED-PASS-20261119.json).

- Linux client initial connection already accepts authenticated original TLS and true native Rust M4/OS local readiness without Windows' removed reverse-app condition; no code change. It retains authenticated successor A/B proof before replacing existing A.
- Windows original Go sends real OS Applied then READY; WinForms previously overwrote connected with pending. Now only both receipts for active GUI session grant connected in either order; repeated READY never downgrades. Neither stand-alone marker is a fake OS receipt.
- Normal/Fixed/Auto original native Rust 2s readback, Game 1s existing health/packet tick, emit independent C2S and S2C FEC status and genuine local TX/RX counts. C2S 'applied' only after actual native confirmation; S2C Fixed/Game is 'negotiated', not verified actual per-receive grade; Auto S2C stays unknown. RTT/loss remain unknown unless an authenticated quality producer exists. No extra hot Go packet pump.
- Linux server installs one unique tagged iptables IPv4 POSTROUTING MASQUERADE scoped to own TUN IPv4 subnet and specified underlay, reads it back and removes ONLY the same owned rule on Stop. Fails on command/readback error, does not flush foreign rules, warns (does not set) global ip_forward=0.
- Original Rust Health cold commit stays the same authenticated existing control kind/PN/identity. Only first cold M4 post-TLS sequence repeat count (server 3–5/client 4–7) and subsequent successful-copy spacing (225–575ms) vary, drawn once per accepted control. First copy immediate, original bounded retry and 15s ±10% steady interval unchanged. No change to business timing/TLS framing.

Full Windows public WAN physical, packet capture distribution, bidirectional Auto received-grade readback, long-run CPU/p99 and live service NAT on the operator's physical host **NOT_RUN**. H2220 physical FAIL retained. Do not claim long-term stability or protocol indistinguishability.

## Feature-impact (H2224)

```feature-impact
{"kind":"updated","reason":"H2224 changes WinGUI live native readiness and directional FEC quality, Linux server owned IPv4 NAT and original authenticated cold Health timing without protocol changes.","ids":["gui-config-feedback","linux-raw-tun","tls-auth-multiclient"]}
```

## H2224 H2067 legacy cold regression closure

- [PR49](https://github.com/lly8666/wbd-next/pull/49) repairs only the historical Rust **test** that assumed five cold controls at exactly 400ms; H2224 production requires four to seven authenticated Health controls and 225–575ms random delays with first copy immediate, still before server 5s proof boundary. No executable protocol or product source changed by the test fix.
- Source-locked [Windows owner+Health Action 44574263649](https://github.com/lly8666/wbd-next/actions/runs/44574263649) SUCCESS: 89 Windows original-owner + 14 native Health unit tests, H2067 PASS.
- Broader [Rust library Action 44573389406](https://github.com/lly8666/wbd-next/actions/runs/44573389406) reported 423 PASS / two unrelated R1 standalone fixture/provenance FAIL; no full-library PASS claim. This is separate from H2224 package Action 44571858954 two-job SUCCESS.
- H2224 same product binaries remain the validated Windows GUI ZIP and Linux ARM64 server tar; newest main contains only this #49 test-source change plus documentation relative to those binaries. Physical long-run, full R1 fixture corpus and previous unrelated historical suites remain OPEN/NOT_RUN.

```feature-impact
{"kind":"none","reason":"PR49 adjusts only a historical cfg(test) Windows Rust cold Health timing assertion; no new product, native protocol, user-facing feature or runtime control change.","ids":[]}
```
