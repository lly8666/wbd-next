# PLAN027 H526 — original two-OS frozen source7a A/B coverage without build repeats

H525 no-loss gate [41064405693](https://github.com/lly8666/wbd-next/actions/runs/41064405693) PASS and launched four independent 50M/150ms/1–30% Actions [41064427699](https://github.com/lly8666/wbd-next/actions/runs/41064427699), [41064431346](https://github.com/lly8666/wbd-next/actions/runs/41064431346), [41064435483](https://github.com/lly8666/wbd-next/actions/runs/41064435483), [41064438830](https://github.com/lly8666/wbd-next/actions/runs/41064438830). Not complete at H526 freeze. H525 governance [41064405551](https://github.com/lly8666/wbd-next/actions/runs/41064405551) success. Preserve failures.

New independent H526 preflight verifies H520 original signed Windows/Linux source `7a5d7e83823e96539d2a904a8193a85ec18df30d` and both binary artifact names, plus successful H525 proof before dispatch. Each **separate** product Action runs exactly one scene; A5 uses same hosted VM sequential Go/Rust A/B inside one Action. Seven scenes: normal scenarios/plan027-a2-normal-10m-250ms-0loss-60s.json AB=false; normal scenarios/wl-outer-repair-10m-250ms-loss30-60s.json AB=false; fixed scenarios/wl-outer-repair-fixed-10m-250ms-loss30-60s.json AB=false; auto scenarios/plan027-a4-auto-10m-staged-240s.json AB=false; game2-fec scenarios/wl-game2-fixed6-10m-75ms-loss15-20s.json AB=false; game4-fec scenarios/wl-game4-fixed6-10m-75ms-loss30-20s.json AB=false; normal scenarios/plan027-c-normal-10m-25ms-loss0-60s.json AB=true. Reuse binaries from build/run `41060763175`, not recompile per scenario. Different Actions have independent hosted runners; same VM never simultaneously runs multiple measurement controllers. H526 dispatch is not a test PASS. The prior GameFEC cancellations and A5 Go failure remain until new real run evidence.

B Windows lifecycle, broader C capacity/weaknet/Game4 gated 20M and 5-minute representative are still required; do not read readiness from one gate.

```feature-impact
{"kind":"none","ids":[],"reason":"Source-locked one-test-per-Action orchestration, cursor and devlog only; frozen source7a production/config/cards unchanged."}
```
