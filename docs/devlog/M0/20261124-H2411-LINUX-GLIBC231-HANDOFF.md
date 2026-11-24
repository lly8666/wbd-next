# M0 H2411 Linux glibc 2.31 dual ISA WIP handoff

Intent: docs/decisions/M0-LINUX-GLIBC231-20261124.md. Branch experiment/m0-linux-glibc231, Draft PR #76. First source 23a73e8c23e289d5f5c898faf15560c97a761dac run 45411561914 failed both native ISAs during Docker dependency installation (retired Debian bullseye-security packages HTTP404, before WBD compile). No compatible artifacts and no performance result from first run. Fix f38cfc218926b4aea206d88a5ecf2a836ce7be88 uses signed archive + final snapshot; push auto-created run 45411847411. Observed jobs:
```json
[
  {
    "id": 138507449273,
    "name": "native (x86_64)",
    "status": "in_progress",
    "conclusion": null,
    "steps": [
      {
        "name": "Set up job",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "name": "Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "name": "Run actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "name": "Native same-source prerequisites",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "name": "Build glibc 2.31 original Go Rust ISA-L products",
        "status": "in_progress",
        "conclusion": null
      }
    ]
  },
  {
    "id": 138507449765,
    "name": "native (aarch64)",
    "status": "in_progress",
    "conclusion": null,
    "steps": [
      {
        "name": "Set up job",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "name": "Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "name": "Run actions/setup-go@d35c59abb061a4a6fb18e82ac0862c26744d6ab5",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "name": "Native same-source prerequisites",
        "status": "completed",
        "conclusion": "success"
      },
      {
        "name": "Build glibc 2.31 original Go Rust ISA-L products",
        "status": "in_progress",
        "conclusion": null
      }
    ]
  }
]
```

Next: harvest this run without redispatch. Confirm all three actual ELF max GLIBC <=2.31 for each ISA, actual focal userland product/Stop, same host sequential A/B/A receiver bytes and CPU/GiB; only then decide integration. Governance/feature gate remains red (45411847512); prior main structure failure not erased. No physical kernel 5.4 qualification, no hot-path changes or physical deployment. Do not treat WIP as delivery.
