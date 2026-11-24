#!/usr/bin/env python3
"""Only in an ephemeral pinned Go checkout: migrate obsolete *tests* from 1360.

The seven production FakeTCP Go files are manifest-verified by
m0_install_public_faketcp.py. This file NEVER touches their compiled sources.
It replaces the old donor tests' removed faketcp.DefaultMSS symbol with a
named 1460-outside/1420-SYN fixture, then initializes the one current FakeTCP
MSS owner for those tests. No legacy/modern mode or production fallback.
"""
from pathlib import Path
import sys

FIXTURE = "m0CurrentV4MSSFixture"
# Exact number of references is part of the pinned source contract. A new
# caller of DefaultMSS cannot be silently accepted by a mass replace.
EXPECTED = {
    # Admission V4 fixture now directly pins 1460 outer / MSS1420.
    "bridge_v4_probe_linux_test.go": 7,
    "tls_test.go": 1,
    "wire_qualification_test.go": 2,
}
REMOVED = "faketcp.DefaultMSS"
FILE = "m0_current_v4_mss_fixture_test.go"
FIXTURE_SOURCE = """package realityfront

import "github.com/lly8666/wobuzhidao/internal/faketcp"

// Explicit test vector only: complete outer IPv4 1460 -> SYN MSS 1420.
// Production reads the Rust cold-budget result before first SYN/SYNACK.
const m0CurrentV4MSSFixture = 1420

func init() {
 if err := faketcp.SetPublicV4AdvertisedMSS(m0CurrentV4MSSFixture); err != nil {
  panic(err)
 }
}
"""

def prepare(root: Path) -> None:
    target = root / "internal" / "realityfront"
    if not target.is_dir():
        raise ValueError("expected pinned Go realityfront checkout")
    if (target / FILE).exists():
        raise ValueError("unexpected existing MSS fixture collision")
    changed = {}
    for name, count in EXPECTED.items():
        file = target / name
        source = file.read_text(encoding="utf-8")
        if source.count(REMOVED) != count:
            raise ValueError(f"frozen original Go MSS test reference count changed: {name}")
        changed[file] = source.replace(REMOVED, FIXTURE)
    # Refuse unknown references in the SAME tested package. No production
    # Go file or any other package is rewritten to preserve a legacy format.
    for file in target.glob("*_test.go"):
        if file.name not in EXPECTED and REMOVED in file.read_text(encoding="utf-8"):
            raise ValueError("unreviewed old MSS reference in test "+file.name)
    for file, content in changed.items():
        file.write_text(content, encoding="utf-8")
    (target / FILE).write_text(FIXTURE_SOURCE, encoding="utf-8")
    print("H984_ORIGINAL_GO_TEST_ONLY_1460_OUTER_MSS1420_MIGRATION_PASS"+
          " exact_files="+str(len(changed))+
          " exact_references="+str(sum(EXPECTED.values())))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: m0_prepare_original_go_mss_test_fixtures.py PINNED_GO_CHECKOUT")
    prepare(Path(sys.argv[1]))
