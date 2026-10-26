# PN-XOR full-equivalent optimization: native x86 + ARM results

**COMPLETE, two native CI SUCCESS; main untouched.** Research branch: experiment/lan-pnxor-optimized, based on previous experiment SHA 9efbd288ae25182c6f6b182188750a8a683f7070.

## Benchmark method

1,345-byte original synthetic IPv4/TCP/TLS13-looking inner packet, protected mode bit + 63-bit PN in existing 8B field, 5B TLS-like outer header, 1B kind, XOR-masked payload. Identical AES128 header protection block used per send and receive across every variant. Exactly 100 original packets per benchmark iteration; each iteration seals and opens all 100. Go compiler same within each architecture, native GitHub hosted x86_64 or ARM64, GOMAXPROCS=1, 5 x 1-second Go benchmarking replicates, all scratch/wire buffers preallocated. Measurements are Go wall ns/100; not production Rust or full WBD CPU.

Benchmark code: tools/lan_pnxor_opt_test.go. Six variants:
- FullBaseline: current experimental 64-bit LittleEndian public PN-XOR word loop, full 1346B kind+inner.
- FullUnroll4: four unrolled 64-bit XOR steps per 32B, complete exact network-wire compatibility.
- FullSubtleXOR: expand the repeated 8B PN mask in reused buffer and call Go crypto/subtle.XORBytes on all 1346B; complete exact network-wire compatibility.
- Prefix64, Prefix128, Prefix256: modify only first 64B, 128B, or 256B of kind+inner, leaving all the remaining payload literally unchanged, **not compatible on wire and weakens even obfuscation; NOT a production suggestion**.

Real native tests passed 1,000 roundtrips of all variants plus edge-case PN checks 0,1,7,42,0x100000001,2^63-1; test asserts wire bytes from two full variants are EXACTLY equal to FullBaseline; test also explicitly asserts prefix variants leave plaintext tail unchanged on wire. All modes: 0B/op, 0 heap allocations/op.

## Measured mean ns per 100 encode+decode operations (5 replicates each)

| Method | x86_64 ns/100 | ARM64 ns/100 | x86 improvement | ARM improvement |
|---|---:|---:|---:|---:|
| FullBaseline | 42,845.4 | 34,906.8 | reference | reference |
| FullUnroll4 | 37,449.2 | 32,679.6 | 12.59% faster | 6.38% faster |
| FullSubtleXOR, SAME WIRE | **25,478.4** | **29,821.2** | **40.53% faster** | **14.57% faster** |
| Prefix64 (exposes original tail) | 10,034.4 | 11,718.2 | 76.58% faster | 66.43% faster |
| Prefix128 (exposes original tail) | 11,759.6 | 12,805.4 | 72.55% faster | 63.32% faster |
| Prefix256 (exposes original tail) | 14,767.8 | 15,344.2 | 65.53% faster | 56.04% faster |

Raw x86:
FullBaseline [42841,42748,42862,42809,42967];
FullUnroll4 [37061,36917,39363,36993,36912];
FullSubtleXOR [25472,25507,25470,25462,25481];
Prefix64 [10030,10051,10030,10032,10029];
Prefix128 [11754,11763,11755,11772,11754];
Prefix256 [14743,14775,14773,14772,14776].

Raw ARM:
FullBaseline [34970,34873,35009,34886,34796];
FullUnroll4 [32714,32671,32670,32660,32683];
FullSubtleXOR [29858,29811,29828,29805,29804];
Prefix64 [11778,11707,11690,11720,11696];
Prefix128 [12812,12807,12810,12793,12805];
Prefix256 [15321,15325,15327,15388,15360].

Native x86 GitHub CI success [run 40259222110](https://github.com/lly8666/wbd-next/actions/runs/40259222110); archived artifact 12624151131.
Native ARM CI success [run 40259225987](https://github.com/lly8666/wbd-next/actions/runs/40259225987); archived artifact 12624166057.

## Limitations

- Public PN-XOR is publicly invertible, not cryptographic confidentiality, not message integrity, not replay protection. Hiding the mode bit behind AES HP does not alter these deficiencies.
- Prefix-only variants expose all packet payload bytes after the protected prefix. No independent TLS1.3 app-data classifier, session admission, authentication or deployment safeguards were implemented in this study.
- Do not compare these absolute elapsed times directly to a different test fixture/run; compare variants within this native CI only.
- Rust production WBD uses preexisting independent suite-specific HP on 8B protected PN, and currently standard AES-GCM/ChaCha20-Poly1305 AEAD for record payload; no public PN-XOR in main.
- To integrate a hidden mode bit in Rust requires a negotiated record format change, authenticated security state, associated data, PN lifecycle, and a secured fast-mode design. This Go prototype is not that integration.

## Engineering conclusion

When retaining full-byte PN-XOR, bulk XORBytes provided major CPU reduction with exactly unchanged record bytes, no new record fields, and no extra heap allocation. It is the correct **performance optimization candidate** in this research comparison, not the unsafe prefix variants. Benchmark Rust SIMD/portable equivalent separately; do not ship unauthenticated fast paths.
