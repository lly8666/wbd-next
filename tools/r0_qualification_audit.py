#!/usr/bin/env python3
"""R0 foundation source/evidence audit — static metadata only.

Runs in GitHub Actions, does not compile, execute product/test binaries,
fetch current workflow status, or qualify real network/I/O/crypto performance.
Historical Actions run states must first be verified from their GitHub records.
"""
import hashlib
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(".")
EXPECTED_WORKSPACE = {"wbd-types", "wbd-codec", "wbd-platform", "wbd-engine", "wbd-recovery"}
EXPECTED_GATES = {
    "R0-TYPES": "PASS",
    "R0-GO-GOLDEN": "PASS",
    "R0-GO-TLS": "PASS",
    "R0-GO-CONTROL": "PASS",
    "R0-NATIVE-ABI": "PASS",
    "R0-FAKE-PLATFORM": "PASS",
    "R0-CROSS-ABI": "CROSS_BUILD_PASS",
    "R0-WIRE-CODEC": "PASS",
    "R0-RECORD-FRAMING": "PASS",
    "R0-LINK-FEC-WIRE": "PASS",
}
ALLOWED_MODES = {
    "NATIVE_LINUX_X64_TEST",
    "PINNED_LEGACY_GO_TEST",
    "PINNED_LEGACY_GO_TEST_TLS",
    "PINNED_LEGACY_GO_CONTROL_CLI_TEST",
    "NATIVE_GO_C_RUST_LINUX_X64_SENTINEL",
    "NATIVE_LINUX_X64_RUST_FAKE_DRIVER",
    "CROSS_BUILD_ONLY_NO_TARGET_EXECUTION",
    "NATIVE_LINUX_X64_RUST_WIRE_ONLY",
    "NATIVE_OLD_GO_SEAL_OPEN_AND_RUST_OPAQUE_FRAME",
    "NATIVE_OLD_GO_LINK_FEC_AND_RUST_WIRE_ONLY",
}
EXPECTED_IDS = {
    f"{prefix}{n:02d}"
    for prefix, end in (
        ("B", 4), ("R", 4), ("M", 4), ("I", 4), ("C", 4),
        ("L", 4), ("F", 6), ("A", 6), ("G", 4), ("P", 4)
    )
    for n in range(1, end + 1)
}
PARTIAL_IDS = {"B01", "R01", "I01", "C01"}
PARTIAL_WIRE_IDS = {"L01"}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def read_json(path):
    return json.loads(Path(path).read_text())

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit():
    lock = read_json("r0/source-lock.json")
    m = read_json("r0/qualification-manifest.json")
    project = read_json(".governance/project.json")
    registry = read_json(".governance/registry.json")
    workspace = tomllib.loads(Path("Cargo.toml").read_text())
    packages = tomllib.loads(Path("Cargo.lock").read_text())["package"]
    toolchain = tomllib.loads(Path("rust-toolchain.toml").read_text())["toolchain"]
    members = {p.rsplit("/", 1)[-1] for p in workspace["workspace"]["members"]}
    # Every native/cross gate that consumes this lock MUST retrigger when
    # pinned toolchains/source qualification inputs change.
    for workflow in (
        "r0-build.yml", "r0-go-vectors.yml", "r0-v4-tls.yml",
        "r0-go-control.yml", "r0-native-abi.yml", "r0-platform-fake.yml",
        "r0-codec.yml", "r0-cross-abi.yml",
    ):
        body = Path(".github/workflows", workflow).read_text()
        prefix = body.partition("permissions:")[0]
        require('"r0/source-lock.json"' in prefix,
                f"workflow {workflow} fails to trigger when source-lock changes")
    require(members == EXPECTED_WORKSPACE, "current workspace does not match G2 five-crate bootstrap")
    require(set(lock["rust"]["crates"]) == members == set(m["workspace_expected"]),
            "source-lock/manifest/workspace crates drift")
    package_names = {p["name"] for p in packages}
    require(members.issubset(package_names), "Cargo.lock lost an internal workspace crate")
    externals = [p for p in packages if p["name"] not in members]
    require(len(externals) >= 3, "R1 crypto lock omitted registry dependency closure")
    require(all(p.get("source") == "registry+https://github.com/rust-lang/crates.io-index"
                and len(p.get("checksum", "")) == 64 for p in externals),
            "R1 external Cargo.lock provenance/checksum invalid")
    by_name = {p["name"]: p for p in packages}
    for name, version in (("aws-lc-rs", "1.18.1"), ("chacha20", "0.9.1"), ("aes", "0.8.4")):
        require(by_name[name]["version"] == version, f"unapproved crypto version: {name}")
    workspace_deps = workspace["workspace"].get("dependencies", {})
    for name, version in (("aws-lc-rs", "1.18.1"), ("chacha20", "0.9.1"), ("aes", "0.8.4")):
        require(workspace_deps[name]["version"] == "=" + version, f"crypto manifest pin drift: {name}")
    require(workspace_deps["aws-lc-rs"]["features"] == ["non-fips", "alloc"]
            and workspace_deps["aws-lc-rs"]["default-features"] is False,
            "unexpected aws-lc-rs feature set or FIPS build")
    # Historic R1 cryptography artifact digest is an immutable SOURCE receipt,
    # NOT a promise current Cargo.lock never changes for new scoped M1 packages.
    # Check the historical anchor and every present dependency/version below;
    # Cargo --locked and artifact provenance guard the current graph at build.
    require(lock["rust"]["crypto_dependencies"]["cargo_lock_sha256"] ==
            "4147b1175268099e3f42a98bc23aeb08e762f24fa3d718a1d819322efa683b36",
            "historic crypto Cargo.lock proof anchor changed")
    require(workspace_deps.get("rtrb") == {"version":"=0.3.2"} and
            by_name.get("rtrb",{}).get("version") == "0.3.2" and
            by_name["rtrb"].get("checksum") ==
              "ad8388ea1a9e0ea807e442e8263a699e7edcb320ecbcd21b4fa8ff859acce3ba"
            and not by_name["rtrb"].get("dependencies"),
            "M1 bounded SPSC rtrb version, provenance or transitive closure drift")
    for crate in members:
        c = tomllib.loads(Path(f"crates/{crate}/Cargo.toml").read_text())
        require(c["package"]["name"] == crate, f"crate package mismatch: {crate}")
        deps = set(c.get("dependencies", {}))
        # R1 composition is M0-owned and strictly one-way. Keep every
        # lower-level crate pure types-only and engine as the sole importer.
        expected = (set() if crate=="wbd-types" else
                    {"wbd-types","wbd-codec","wbd-platform","wbd-recovery","rtrb"}
                    if crate=="wbd-engine" else
                    {"wbd-types","aws-lc-rs","chacha20","aes"}
                    if crate=="wbd-codec" else {"wbd-types"})
        require(deps == expected,
                f"crate {crate} dependency is not the locked one-way R1 graph")
        for k,v in c.get("dependencies", {}).items():
            if k in members:
                require(v.get("path") == f"../{k}",
                        f"wrong internal source pin for {crate}->{k}")
            else:
                require(((crate=="wbd-codec" and k in {"aws-lc-rs","chacha20","aes"})
                         or (crate=="wbd-engine" and k=="rtrb"))
                        and v=={"workspace":True},
                        f"unapproved external dependency {crate}->{k}")
    lock_deps={p["name"]:set(p.get("dependencies",[])) for p in packages}
    require(lock_deps["wbd-engine"]==
            {"wbd-types","wbd-codec","wbd-platform","wbd-recovery","rtrb"},
            "Cargo.lock lost R1 engine assembly edges")
    require(lock_deps["wbd-codec"]=={"wbd-types","aws-lc-rs","chacha20","aes"},
            "Cargo.lock codec crypto direct dependencies drift")
    for crate in members - {"wbd-engine", "wbd-codec"}:
        require(lock_deps[crate]==(set() if crate=="wbd-types" else {"wbd-types"}),
                f"Cargo.lock inverted dependency: {crate}")
    require(lock["schema_version"] == m["schema_version"] == 1, "manifest schema mismatch")
    require(lock["phase"] == project["phase"] == "R0_FOUNDATION_IN_PROGRESS", "unexpected phase promotion")
    require(lock["qualification"]["canonical_manifest"] == m["source_lock"].replace("source-lock.json","qualification-manifest.json") ==
            "r0/qualification-manifest.json", "canonical R0 manifest path drift")
    require(lock["legacy"]["source_sha"] == m["expected_legacy_source"] ==
            "a7a82db31fe736ffedee330795a3234d358f1984", "legacy pin changed")
    require(lock["legacy"]["go_toolchain"] == "go1.23.12", "pinned Go compiler changed")
    require(lock["legacy"]["compiled"] is True and "TEST_ONLY" in lock["legacy"]["compiled_scope"],
            "Go compiled test scope missing or claimed product")
    require(lock["rust"]["toolchain"] == toolchain["channel"] == "1.85.1", "Rust toolchain mismatch")
    require(workspace["workspace"]["package"]["rust-version"] == "1.85.1", "Rust MSRV mismatch")
    require(lock["rust"]["target"] == m["native_target"] == "x86_64-unknown-linux-gnu", "native target mismatch")
    expected_cross = {"x86_64-pc-windows-gnu", "aarch64-unknown-linux-gnu"}
    require(set(lock["rust"]["cross_targets"]) == set(m["cross_targets"]) == expected_cross,
            "cross target inventory changed")
    require("NOT_RUN" in lock["rust"]["cross_targets_execution"], "cross target execution overclaimed")
    require(m["production_go_v4"] == "DISABLED_FAIL_CLOSED", "production V4 claimed")
    require(m["capabilities"] == "R0_ABI_SENTINEL_FEATURES_ZERO", "Rust engine falsely advertising capabilities")
    for key in ("product", "performance", "physical", "windows_arm_native_execution"):
        require(lock["qualification"][key] == "NOT_RUN", f"{key} was promoted without real evidence")
    require(lock["qualification"]["rust_business_engine"] == "NOT_IMPLEMENTED", "steady engine false-positive")
    require(project["product_qualification"] == project["physical"] == "NOT_RUN",
            "project qualification was promoted")
    roles={r["id"]:r for r in registry["roles"]}
    require(roles["M0"]["state"]=="active" and roles["M0"]["branch"]=="main" and
            registry["reservation_revision"]==2 and roles["M0"]["assignment_epoch"]==1,
            "M0 integration writer/revision changed")
    expected_worker_paths = {
      "M1": ("work/m1-r1-runtime", ("crates/wbd-engine/src/runtime/","crates/wbd-engine/src/memory/")),
      "M2": ("work/m2-r2-recovery", ("crates/wbd-recovery/",)),
      "M3": ("work/m3-r1-codec", ("crates/wbd-codec/",)),
      "M4": ("work/m4-r1-platform", ("crates/wbd-platform/","r1/go-bridge/")),
    }
    for role,(branch,paths) in expected_worker_paths.items():
        spec = roles[role]
        require(spec["state"]=="active" and spec["branch"]==branch and
                spec["assignment_epoch"]==1 and spec["global_writer"] is False and
                all(p in spec["allowed_paths"] for p in paths) and
                f".governance/workstreams/{role}/cursor.json" in spec["allowed_paths"],
                f"{role} worker scope/epoch/branch drift")
        local_cursor=read_json(f".governance/workstreams/{role}/cursor.json")
        require(local_cursor["role_id"]==role and local_cursor["branch"]==branch and
                local_cursor["reservation_revision"]==2 and local_cursor["assignment_epoch"]==1,
                f"{role} bootstrap cursor identity drift")
    gates = m["evidence_gates"]
    require({g["gate"] for g in gates} == set(EXPECTED_GATES) and len(gates)==len(EXPECTED_GATES),
            "historic gate inventory drift")
    evidence_hashes={}
    gate_sources={}
    for g in gates:
        gate=g["gate"]
        require(g["mode"] in ALLOWED_MODES, "new evidence mode")
        require(g["result_key"] in ("result","test_result"), "unsupported evidence result key")
        require(g["expected"]==EXPECTED_GATES[gate], f"{gate} self-promoted outcome")
        require(g["evidence"].startswith("docs/evidence/M0/R0-") and
                g["evidence"].endswith(".json"), f"{gate} not a supported R0 evidence path")
        p=Path(g["evidence"])
        ev=read_json(p)
        require(ev["source_sha"]==g["source_sha"],f"{gate} evidence SOURCE mismatch")
        actual_run=ev["successful_run"] if gate=="R0-CROSS-ABI" else ev
        actual_id=actual_run.get("id") if gate=="R0-CROSS-ABI" else actual_run["run_id"]
        actual_attempt=actual_run["attempt"] if gate=="R0-CROSS-ABI" else actual_run["run_attempt"]
        require(actual_id==g["run_id"] and actual_attempt==g["run_attempt"]==1,
                f"{gate} historical run identity mismatch")
        require(ev["workflow"]==g["workflow"],f"{gate} workflow mismatch")
        require(ev[g["result_key"]]==g["expected"],f"{gate} proof is not historic PASS")
        if gate=="R0-CROSS-ABI":
            require(all(t["target_native_execution"]=="NOT_RUN"
                       for t in ev["successful_run"]["targets"].values()),
                    "target-native execution falsely claimed")
            require(ev["first_attempt_failure"]["conclusion"]=="failure",
                    "failed first ARM64 attempt improperly hidden")
        source=Path(g["actual_file"]).read_text()
        for anchor in g["require_anchor"]:
            require(anchor in source,f"{gate} code test anchor missing: {anchor}")
        if gate=="R0-RECORD-FRAMING":
            go_oracle=Path("r0/go_overlay/internal/tlsrecord/r0_record_wire_oracle_test.go").read_text()
            fixture=Path("r0/fixtures/legacy-record-wire-v1.txt").read_text()
            for go_test in (
                "TestR0RecordRealPinnedGoSealAndOpenSixFixtures",
                "TestR0RecordRealGoLengthFailClosedWithoutMagicScan",
            ):
                require(go_test in go_oracle,f"pinned Go oracle entrypoint missing: {go_test}")
            require(sum(1 for line in fixture.splitlines() if line and not line.startswith("#"))==6,
                    "six locked Go encrypted wire fixtures missing")
            require(ev["original_go_oracle"]["top_level_passed"]==2 and
                    ev["rust_opaque_frame"]["passed"]==6,
                    "Go real cipher/Rust structural framing test counts overclaimed")
            require(ev["not_qualified"]["rust_aead"]=="NOT_IMPLEMENTED" and
                    ev["not_qualified"]["rust_hp"]=="NOT_IMPLEMENTED",
                    "structural probe falsely claimed real Rust crypto")
        if gate=="R0-LINK-FEC-WIRE":
            fixture=Path("r0/fixtures/legacy-link-fec-wire-v1.txt").read_text()
            require(sum(1 for line in fixture.splitlines() if line and not line.startswith("#"))==6,
                    "six locked original-Go LINK/FEC fixed wire examples missing")
            for file, anchors in (
                ("r0/go_overlay/internal/linkdata/r0_link_wire_oracle_test.go", (
                    "TestR0LinkPinnedRealGoMtu63_64_65Wire",
                    "TestR0LinkPinnedRealGoMagicWFandInvalidLength")),
                ("r0/go_overlay/internal/fec/r0_fec_wire_oracle_test.go", (
                    "TestR0FecPinnedActualStreamingSourceAndFinalParityHeaders",
                    "TestR0FecPinnedRealGoProfilesWireBounds")),
            ):
                body=Path(file).read_text()
                for name in anchors:
                    require(name in body, f"real legacy Go oracle test missing: {name}")
            require(ev["tests"]["rust"]["passed"]==7 and
                    ev["tests"]["go_link"]["passed"]==2 and
                    ev["tests"]["go_fec"]["passed"]==2,
                    "actual Rust and old Go LINK/FEC tests count mismatch")
            require(ev["not_qualified"]["rust_fec_math"]=="NOT_IMPLEMENTED" and
                    ev["r0_case_coverage"]["L01"].startswith("PARTIAL"),
                    "LINK/FEC header falsely claimed full parity or L01")
        gate_sources[gate]=g["source_sha"]
        evidence_hashes[gate]=sha256(p)
    coverage=m["case_coverage"]
    require(len(coverage)==len(EXPECTED_IDS) and
            {x["id"] for x in coverage}==EXPECTED_IDS, "case ID inventory missing/duplicate")
    for x in coverage:
        if x["id"] in PARTIAL_IDS:
            require(x["status"]=="PARTIAL_R0_FAKE_ONLY" and x["gate"]=="R0-FAKE-PLATFORM" and
                    x.get("tests") and x.get("limits"),f"{x['id']}: fake test misrepresented")
            for test in x["tests"]:
                require(test in Path("crates/wbd-platform/src/lib.rs").read_text(),
                        f"unanchored R0 fake case {x['id']}: {test}")
        elif x["id"] in PARTIAL_WIRE_IDS:
            require(x["status"]=="PARTIAL_R0_WIRE_ONLY" and
                    x["gate"]=="R0-LINK-FEC-WIRE" and
                    x.get("tests") and x.get("limits"),
                    f"{x['id']} full L01 improperly promoted")
            for anchor in x["tests"]:
                require(anchor in Path("crates/wbd-codec/src/link_fec_wire.rs").read_text(),
                        "R0 LINK MTU case source anchor missing: "+anchor)
        else:
            require(x["status"]=="NOT_RUN" and x.get("reason"), f"{x['id']} unproved ID marked PASS")
    exit_gate=m["r0_foundation_exit"]
    require(exit_gate["status"]=="BLOCKED_NOT_QUALIFIED" and
            exit_gate["ready_for_worker_allocation"]=="SCOPED_WORKERS_ACTIVATED_UNQUALIFIED" and
            exit_gate.get("activation_decision_ref")=="docs/decisions/M0-G2-worker-activation.md" and
            Path(exit_gate["activation_decision_ref"]).is_file(),
            "R0 exit was promoted by metadata")
    required_blockers={"R0-WIRE-RECORD","R0-LINK-FEC-BOUNDARIES","R0-GO-CONTROL-INTEGRATION",
                       "R0-ENGINE-PLATFORM","R0-NATIVE-MULTI-OS","R0-PRODUCT"}
    require({b["key"] for b in exit_gate["blockers"]}==required_blockers,
            "R0 product/foundation blockers were dropped")
    result={
      "schema_version":1,
      "result":"STATIC_AUDIT_PASS",
      "claim":"R0 foundation source-lock and historic evidence consistency ONLY; no test/product qualification",
      "source_lock_sha256":sha256("r0/source-lock.json"),
      "qualification_manifest_sha256":sha256("r0/qualification-manifest.json"),
      "evidence_sha256_by_gate":evidence_hashes,
      "historical_source_sha_by_gate":gate_sources,
      "case_ids":len(coverage),
      "partial_r0_fake_only_ids":sorted(PARTIAL_IDS),
      "worker_activation": "SCOPED_M1_M4_ACTIVE_BRANCH_CURSOR_METADATA_ONLY",
      "partial_r0_wire_only_ids":sorted(PARTIAL_WIRE_IDS),
      "not_run_case_count":len(EXPECTED_IDS)-len(PARTIAL_IDS)-len(PARTIAL_WIRE_IDS),
      "live_external_run_status":"NOT_CHECKED_IN_THIS_AUDIT",
      "product":"NOT_RUN","performance":"NOT_RUN","physical":"NOT_RUN",
      "windows_arm_target_native_execution":"NOT_RUN",
      "go_production_v4":"DISABLED",
    }
    out=Path("r0-qualification-audit-result")
    out.mkdir(exist_ok=True)
    (out/"audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    try:
        audit()
    except Exception as exc:
        print("R0_STATIC_AUDIT_FAIL:",str(exc),file=sys.stderr)
        sys.exit(1)
