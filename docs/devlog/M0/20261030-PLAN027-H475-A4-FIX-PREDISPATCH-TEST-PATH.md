# H475 A4 pre-dispatch unit path fix

The source-locked A4 H474 run41006998017 was stopped by Python unit FileNotFoundError for scenarios/tools/m0_wl_netem.py because SCENE.parents[0] is scenarios/, not repository root. No physical A4 test executed; no fabricated success. H475 uses SCENE.parents[1], retains exact product source a61eef334068512b00a1db3137a51f3d0489020c, and re-triggers H474 one-shot. All actual-A4 claims deferred to one uninterrupted native Action report.
