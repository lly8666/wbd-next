# PLAN028 H1158 — fix pre-native ARM64 manifest ISA assertion

H1157 [native ARM64 Action41855120789](https://github.com/lly8666/wbd-next/actions/runs/41855120789) FAILURE is **not a native product business failure**. Original Go TLS and Rust M4 both built for real ARM64 ELF183 and Go protected-policy tests passed, but a copied x86 script still asserted `platform.machine()=="x86_64"` inside the Python manifest generator. It failed `<stdin> line 3 AssertionError` before writing manifest or starting the mixed client/UDP scene; artifact13335399622 sha256:ca6f614d06fcc230da7dea86ebd9239553697a1a6f387715d3e994ee06b4700f contains assembly and policy units only. It cannot count toward ARM native platform rotation.

H1158 replaces **only** the erroneous Python check with aarch64 in the same new ARM workflow. Kernel uname and all three ELF machine183 checks remain unchanged. One full new-source ARM64 original Go TLS/Rust build and one genuine Normal+Game2+Game4 shared443 scene will be rerun, no duplicate x86 scene. H1155 x86 PASS stays strictly sourcec44f. No new FEC/AEAD/PN, TLS, packet format, helper dispatcher or Android.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix one pre-native ARM64 workflow ISA verification typo; native product and feature behavior unchanged."}
```
