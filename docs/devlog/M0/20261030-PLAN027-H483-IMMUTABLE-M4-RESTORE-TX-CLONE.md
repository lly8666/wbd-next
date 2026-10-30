# H483: preserve immutable M4 overlay and current PLAN020 assembly manifest

H482 feature+cheap native checks pass, but governance-maintenance Action41011442947 correctly rejected modified r0/go_overlay/internal/faketcp/npcap_native_handoff_windows.go because M4 frozen inventory pins Git blob 2901f24535e369046845802aede6eac3db77c5d1. Do not change or suppress that historical audit. Restore exact overlay and manifest source bytes. H483 patches only the **assembled** original-Go Actions checkout after pinned manifest assembly and before Go compiler: source-validated cloned TX Npcap NativeCaptureConfig asks1MiB via new source added CaptureBufferBytes, original RX asks16MiB in the cloned original pinned faketcp/npcap_windows.go on initial open. All three actual staged-file hashes retained; source frozen with true product build required. This is a scoped exception during CI assembly and does not mutate user original Go repository or any frozen Git overlay bytes. Source C100 outcome still NOT MEASURED for new binary.

```feature-impact
{"kind":"none","ids":[],"reason":"Scope Windows NPF capture ring allocation in build assembly only, restoring frozen historical M4 Git blob; no feature controls or FEC policy changed."}
```
