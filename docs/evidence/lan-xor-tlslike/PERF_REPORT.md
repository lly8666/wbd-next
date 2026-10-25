# LAN TLS-like XOR versus AEAD — native paired CPU cost (2026-10-25)

## Decision: fixed XOR fast; current rolling XOR much slower than AES-GCM

This is record-only evidence, NOT product throughput or security qualification. Branch experiment/lan-xor-tlslike, independent of completed selective-AAD negative experiment. Production main, authenticated codec, Go cold/control, config and deployment unchanged.

Native same-host source pin and results:

- x86_64 release Actions [40175257396](https://github.com/lly8666/wbd-next/actions/runs/40175257396), job 121114417612, SUCCESS, SOURCE **2057148a527ede7abb21665b622011efe8c618f6**, artifact **12591593605**, artifact ZIP SHA256 **4f3ce2572f67f4177c59582f549d56fedc506ae9990e1c4f4ab82768c3d40079**.
- ARM64 native release Actions [40175259608](https://github.com/lly8666/wbd-next/actions/runs/40175259608), job 121114423842, SUCCESS, SOURCE **f9d47e9ba7988cf5b0aeb207f95d704c6689cc16**, artifact **12591533829**, artifact ZIP SHA256 **352dca881c1ffdeae3a3c13e150382f74bb3741b5551c6c346ff997a4cac4c6c**.
- Both jobs compiled the same original Rust benchmark source, introduced at **beb15bfbfd6a61a03252792c9d65f35a194a0e49**, and same Cargo.lock. The only difference in trigger commits was CI workflow and not the codec. Original standalone Rust XOR fixture had 5 tests passed, 0 failed, 0 ignored on each host. Benchmark executed and analyzed successfully on both.
- Benchmark: crates/wbd-codec/examples/lan_xor_record_cost.rs; analysis tools/lan_xor_perf_analyze.py. The code reuses actual XOR mask function from tools/lan_xor_tlslike_lab.rs and existing WBD wbd_codec::record_crypto library's native AWS-LC-RS AES128-GCM / ChaCha20-Poly1305.
- Both modes pass a byte-exact preflight: reuse-buffer XOR wire equals the previously captured standalone fixture's sealed wire for identical packet and PN, then roundtrip; AES/ChaCha full record seal+authenticated open roundtrip.

## Contract of measurement

Same 1345-byte deterministic IPv4/TCP original complete packet in all legs, preallocated reusable buffers, single CPU thread, 0.7s warmup and 6s measurement per leg. Ten-leg symmetric order on each **single VM**: AES128, ChaCha20, fixed XOR, rolling XOR, clear, clear, rolling XOR, fixed XOR, ChaCha20, AES128. CPU nanos read from Linux /proc/thread-self/schedstat, normalized by actual bytes of original inner packet. Includes full record seal + open, header/length structure, copy restored plaintext into reusable output, black-box wire/output, but excludes any socket, TLS handshake, Go/TUN, route, packet queue, scheduling, actual network transmission or dynamic allocations in a complete client. No cross-VM A/B arithmetic.

Clear/fixed/rolling TLS-like record has 15B framing overhead (1360B per 1345B packet). Actual existing AES128/ChaCha AEAD record has 31B overhead (1376B per 1345B). XOR modes provide ZERO cryptographic confidentiality, authenticity or replay protection. The AES/ChaCha modes check an actual AEAD tag and apply HP, so these modes do **not** provide equivalent security; they are only record CPU cost comparisons.

## Measured record seal+open CPU

Units: **CPU ns per original inner byte**, lower is better, mean of two symmetric same-VM 6s legs.

| Mode | x86_64 ns/B | ARM64 ns/B | x86 saving vs AES | ARM saving vs AES | wire bytes |
|---|---:|---:|---:|---:|---:|
| Clear TLS-like frame | **0.031981** | **0.034764** | 95.878% | 95.394% | 1360 |
| Fixed XOR | **0.083282** | **0.079119** | **89.266%** | **89.518%** | 1360 |
| AES-128-GCM full AEAD | **0.775876** | **0.754786** | reference | reference | 1376 |
| ChaCha20-Poly1305 full AEAD | **1.440781** | **2.677998** | -85.697% | -254.802% | 1376 |
| Current rolling XOR, per-8B PRNG | **3.315261** | **3.126752** | **-327.292%** | **-314.257%** | 1360 |

Interpretation: fixed XOR needs ~9.32x less record CPU than AES on x86 and ~9.54x less on ARM. The current rolling XOR needs ~4.27x MORE record CPU than AES on x86 and ~4.14x MORE on ARM. The per-8-byte noncryptographic xorshift state generation and full two-pass masking dominate this implementation. This is NOT proof that every conceivable rolling mask is slower than hardware AES.

Forward/reverse percent spread (absolute difference between both ns/B legs divided by their mean):
- x86_64: clear 0.0596%, fixed 0.0947%, AES 0.0219%, ChaCha20 0.1059%, rolling 0.0476%.
- ARM64: clear 0.0704%, fixed 0.0469%, AES 0.0081%, ChaCha20 0.0038%, rolling 0.0445%.

Ten raw leg logs, actual packet counts, actual offered wire bytes, CPU/wall clocks, CPU host manifest and machine-checked summary are retained as per-Action artifacts. No extrapolation to 500Mbps product throughput, p99, queue/drop, cycles or actual user first-delivery. No CPU measurements were mixed between machines.

## Relation to earlier wire evidence and next action

Earlier loopback and actual TLS13-handoff captures proved fixed XOR repeats identical 64B/128B across different new outer TCP sequence positions, while changing-PN rolling XOR did not repeat the specific chosen windows. This performance follow-up demonstrates a **negative cost** for that particular rolling mask: its appearance advantage costs more CPU than full AES-GCM. Fixed XOR is fast but retains clear repeat leaks and no message integrity/replay protection.

These TLS-like 0x17 0x03 0x03 records are *not* valid independently authenticated TLS 1.3 ciphertext records after raw handoff. A preceding mutually authenticated TLS handshake does not secure later raw XOR bytes. Neither an end-to-end product A/B nor Windows/Android, optimized mask alternatives, live inner kernel retransmit, or realistic app mixes were measured.

Scoped measurement is COMPLETE, no product integration approved by this cost data. A future optimized rolling mask should get new explicitly pinned SOURCE, A/B cost AND appearance evidence rather than silently reusing these old receipts. Do not merge or enable any insecure XOR in production by default.
