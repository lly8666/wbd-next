# H2527 candidate — high-RTT measured receive-window growth

## Baseline that motivated the candidate

Three-runner run 46105447669 measured the old pre-DRS A=a99be828 against B=7cc6742 (runtime identical to db76055), not the authorized db76055 baseline. It completed 1GiB ABBA at 400ms and zero injected netem loss, with about 2.5% retired inner TCP retransmission; throughput/capacity and eight-tap packet identity still require review. See docs/evidence/M0/20261128-L2-THREE-RUNNER-BASELINE-RESULT.json. The exact-source candidate comparison must use db76055's ARM build artifact from run 46102235913 as A.

## Candidate change

In `RcvSpace::adjust_linux`, preserve the measured input: minimum of consumed bytes and distinct retained arrivals, normalized to receiver RTT. Preserve the dynamic doubled measured window, OFO span, and existing sub-1ms growth behavior. For high RTT, remove only the additional extrapolation based on the ratio of current measured consumption to the previous `space`; the previous high-RTT growth term compounds credit-release bursts beyond the measured supply.

This is not a fixed window/rate ceiling: a larger real measured supply still grows the window. A stable measured supply does not repeatedly amplify itself. No new controller, feedback message, queue, cross-flow HOL, outer record, TLS-like/TCP-like change, or repair change.

Unit coverage changes the 400ms expected window to twice measured consumption plus OFO, preserves the existing 500us result, checks that stable supply does not grow again, and checks that a real supply increase still grows the dynamic window.

## Exact-source test binding

Both `tools/m0_dual_rust_tcp_local.py` and `tools/m0_dual_tcp_arm_linux_parity.py` bind A to `db760553eaf5b20e01d1c9c6452ab45281cc3812`; both workflows download `dual-tcp-native-build-aarch64` from run 46102235913 and verify the manifest. B is the candidate's exact `GITHUB_SHA`. Preserve original native dual-ISA qualification, same-host 0.5% weak ABBA, and three-runner ARM64 clean ABBA (A/B/B/A, 1GiB, 600Mbps offered, 400ms, Normal, repair on, MTU1160, eight taps and bare brackets).

Candidate has no runtime test result yet. It is not a performance PASS until the exact-source native, local weak, and three-runner artifacts are reviewed together. The earlier a99be828→7cc run remains historical evidence and is not substituted for the new A.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Add a narrowly isolated high-RTT measured-growth candidate and bind all existing local/three-runner ABBA tests to exact db76055 baseline artifacts."}
```
