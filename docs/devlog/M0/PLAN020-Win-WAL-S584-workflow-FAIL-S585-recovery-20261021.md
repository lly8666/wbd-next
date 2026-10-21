# M0 S585 — preserve Windows WAL Actions configuration FAIL
- SOURCE `62f4f1b4dc37e82779e85be3edba28e8d97a433f`, run 39555998587/1, conclusion **FAIL**, jobs empty: YAML `run-name` accidentally contained a literal backslash before the GitHub ${{ github.sha }} expression. Governance run39556000103 passed; native OS WAL test was **NOT_RUN**.
- Repair exact workflow line only. New push triggers a new immutable SOURCE and real Windows2022 Go test. No host-wide WFP/default-route mutation is authorized by this correction. Keep this failure.
