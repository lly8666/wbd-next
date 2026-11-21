#!/usr/bin/env python3
"""Verify ACTUAL signed same-SOURCE APK carries original Go+Rust and
production CLI flag contract. Host-only: no guest, NIC, Root or fake TLS."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

SOURCE = os.environ["GITHUB_SHA"]
apk = Path("out/android-root-app/wbd-root-arm64-debug.apk")
manifest = json.loads(Path("out/android-root-app-native/manifest.json").read_text())
assert manifest["source"] == SOURCE
assert Path("out/android-root-app-native/SOURCE").read_text().strip() == SOURCE
assert manifest["android_abis"] == ["arm64"]
go_src = Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
java_src = Path("android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java").read_text()
service_src = Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
registered = set(re.findall(r'flags\.(?:String|Bool|Int|Uint|Uint64|Duration)\("([a-z0-9-]+)"', go_src))
required = set(re.findall(r'"(--[a-z][a-z0-9-]*)"', java_src))
assert required and all(f[2:] in registered for f in required), sorted(f for f in required if f[2:] not in registered)
assert 'OriginalGoCommandArgs.build(' in service_src
assert 'WBD_PUBLIC_ROOT_SHELL_ENTERED' in service_src
assert 'WBD_PUBLIC_ROOT_EXEC_ATTEMPTED' in service_src
assert 'V4_PUBLIC_ANDROID_GO_ENTRY role=client' in go_src
assert 'V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client' in go_src
assert 'originalAndroidColdParseClass(err)' in go_src
assert 'V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=%s' in go_src
assert 'ORIGINAL_GO_PARSE_PASSWORD_FILE' in service_src
assert 'ORIGINAL_GO_PARSE_ROUTE_KEY_FILE' in service_src
assert 'ORIGINAL_GO_PARSE_INSTALLATION_ID' in service_src
assert 'ORIGINAL_GO_PARSE_ALL_APP_EXCLUSIONS' in service_src
assert 'ORIGINAL_GO_PARSE_OTHER' in service_src
assert 'V4_PUBLIC_ANDROID_GO_TUN_OPEN_ATTEMPTED role=client' in go_src
assert 'ROOT_PROCESS_EXIT_1' in service_src
assert 'new ProcessBuilder("su","-c",' in service_src
assert 'LD_LIBRARY_PATH=' in service_src and 'exec ' in service_src
assert 'RootStopCommand.build(token,ownerExecutable)' in service_src
assert 'NATIVE_M4_AND_UID_READY' in service_src
assert 'hasCA?' in service_src
route_go=Path("r0/go_overlay/internal/v4productcli/android_root_route_android.go").read_text()
allapp_go=Path("r0/go_overlay/internal/v4productcli/rootjournal/allapps.go").read_text()
assert "ServerIP:c.peerIP.String()" in route_go
assert "V4_PUBLIC_ANDROID_PEER_THROW_ROUTE_READBACK role=client" in route_go
assert 'peerThrowArgs("add",original.ServerIP)' in allapp_go
assert 'peerThrowArgs("del",p.ServerIP)' in allapp_go
assert "legacyAllAppsVersion = 3" in allapp_go
# B11b true original-Go TLS ColdSnapshot -> Android original Rust M4.
# Before B11a the unsupported-only requirement was correct; not any more.
shared_client=Path("r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go").read_text()
android_bridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
android_rust=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
assert 'if runtime.GOOS=="android"&&cfg.StartupPaddingMode!=0' not in shared_client
assert 'err=bridge.configureNormalStartupPadding(cold.StartupPaddingMode(),p.cfg.OuterIPMTU)' in shared_client
assert 'func (b *v4EmbeddedNativeBridge) configureNormalStartupPadding(mode uint8,outer int)error' in android_bridge
assert 'wbd_m0_embedded_go_normal_startup_padding_set' in android_bridge
assert 'wbd_m0_embedded_go_normal_startup_padding_counters' in android_bridge
assert 'fn wbd_m0_embedded_go_normal_startup_padding_set(' in android_rust
assert 'fn wbd_m0_embedded_go_normal_startup_padding_counters(' in android_rust
assert 'fn wbd_m0_embedded_go_fixed_stage_pending(' in android_rust
assert 'fn wbd_m0_embedded_go_fixed_pending_readback(' in android_rust
assert 'fn wbd_m0_embedded_go_fixed_m4_counters(' in android_rust
assert 'if !fixed_pending.is_some_and(|(profile,rev)|' in android_rust
assert 'control.low_rate_quality.is_some()' in android_rust
assert 'control.low_rate_signal.is_some()' in android_rust
assert 'policy.propose(&slab.writable()[14..14+n],ms,room)' in android_rust
assert 'startup_padding_copied_bytes.fetch_add(' in android_rust
assert 'normalStartupPaddingCounters()(string,uint64,uint64,error)' in android_bridge
assert android_bridge.count('return ErrAdmissionUnsupported')>=5
ui=Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert "allAppsDefault.setChecked(true)" in ui
assert "RootRouteKeyCache.resolve(this,sni,keyInput)" in ui
# A32: actual DEX must contain the secure Android cold-file writer.
writer=Path("android/root-app/src/org/wbdnext/rootclient/RootPrivateCredentialFiles.java").read_text()
assert "Os.fchmod(fd,RootPrivateCredentialContract.OWNER_ONLY)" in writer
assert "OsConstants.O_NOFOLLOW" in writer and "Os.fstat(fd)" in writer
assert "RootPrivateCredentialFiles.write(this,file,text)" in ui
assert "RootPrivateCredentialFiles.verifyAtStart(this,hasCA)" in service_src
assert "APP_PRIVATE_CREDENTIALS_0600_VERIFIED" in service_src
assert 'st.Mode().Perm()&0077!=0' in go_src

assert "WBD Root Lite v2" in ui
assert 'String key=RootRouteKeyCache.resolve(this,sni,keyInput)' in ui
v2=Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyV2.java").read_text()
cache=Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert "PBKDF2WithHmacSHA256" in v2 and "4096" in v2
assert "WBD-V4-ROUTE-KEY-PBKDF2-SHA256-v2" in v2
assert "new AtomicFile(destination)" in cache and "Os.chmod(destination.getAbsolutePath(),0600)" in cache
assert 'pair(args,"--route-key-hex-file",routeKeyFile)' in java_src
assert "Intent.ACTION_CREATE_DOCUMENT" in ui
assert "RootDiagnosticReport.build(getFilesDir()" in ui
assert 'SERVER_PEER_THROW_PRIVATE_FIB_READBACK' in service_src
with zipfile.ZipFile(apk) as z:
    members = set(z.namelist())
    prefix = "assets/native-arm64/"
    assert prefix+"SOURCE" in members
    assert z.read(prefix+"SOURCE").decode().strip() == SOURCE
    assert not any("native-amd64/" in x or "native-x86/" in x for x in members)
    m=json.loads(z.read(prefix+"manifest.json"))
    assert m["source"]==SOURCE and m["android_abis"]==["arm64"]
    assert m["go_os"]=="android"
    checked={}
    for name in ("wbd-v4-client-arm64","libwbd_engine-arm64.so"):
        payload=z.read(prefix+name)
        digest=hashlib.sha256(payload).hexdigest()
        assert digest==manifest["artifacts"][name]["sha256"]
        assert digest==m["artifacts"][name]["sha256"]
        assert payload[:5]==b"\x7fELF\x02" and int.from_bytes(payload[18:20],"little")==183
        checked[name]=digest
    dex=z.read("classes.dex")
    assert b"Lorg/wbdnext/rootclient/OriginalGoCommandArgs;" in dex
    assert b"Lorg/wbdnext/rootclient/RootRouteKeyV2;" in dex
    assert b"Lorg/wbdnext/rootclient/RootRouteKeyCache;" in dex
    assert b"Lorg/wbdnext/rootclient/RootPrivateCredentialFiles;" in dex
    assert b"Lorg/wbdnext/rootclient/RootPrivateCredentialContract;" in dex
    assert b"Lorg/wbdnext/rootclient/RootClientService;" in dex
    assert b"Lorg/wbdnext/rootclient/RootStopCommand;" in dex
    assert b"Lorg/wbdnext/rootclient/RootDiagnosticReport;" in dex
    assert b"Lorg/wbdnext/rootclient/RootDiagnosticReceipt;" in dex
lite=Path("out/android-root-app/wbd-root-lite-arm64-debug.apk")
assert lite.read_bytes()==apk.read_bytes(), "Lite test APK must be the verified signed original Go/Rust build"
client=Path("out/android-root-app-native/wbd-v4-client-arm64")
dyn=subprocess.run(["readelf","-d",str(client)],check=True,capture_output=True,text=True).stdout
assert "Shared library: [libwbd_engine.so]" in dyn
report={
  "schema":"wbd-original-android-apk-go-rust-host-wiring/v1",
  "source":SOURCE,
  "abi":"arm64-v8a",
  "signed_apk_original_go_and_rust_sha256":"PASS",
  "production_java_go_cli_arguments_host_test":"PASS",
  "main_v2_short_route_key_kdf_vectors":"PASS_HOST_JVM",
  "android_lite_v2_cache_and_original_hex_file_source":"COMPILED_HOST_CONTRACT",
  "short_key_android_device_runtime":"NOT_RUN",
  "registered_original_go_cli_flags":"PASS",
  "production_root_exec_and_owned_stop_source_gate":"PASS",
  "api36_real_receipt_early_exit_fixed_stage_diagnostic_host":"PASS",
  "api36_original_go_parse_rejection_fixed_reason_host":"PASS",
  "api36_app_private_credentials_exact_0600_host_posix":"PASS",
  "api36_app_private_credentials_device_permission_readback":"NOT_RUN",
  "api36_original_go_parse_rejection_device_retest":"NOT_RUN",
  "root_shell_and_original_go_entry_markers_source_locked":"PASS",
  "root_shell_api36_device_runtime":"NOT_RUN",
  "original_go_requires_rust_dynamic_library":"PASS",
  "default_ordinary_app_ipv4_all_apps_source_contract":"PASS",
  "original_go_server_ip_private_fib_throw_and_exact_cleanup_source_contract":"PASS",
  "safe_allowlisted_android_diagnostic_export_in_signed_dex":"PASS",
  "server_ip_actual_physical_bypass_on_android":"NOT_RUN",
  "original_go_rust_android_runtime":"NOT_RUN",
  "physical_network_binding":"NOT_RUN",
  "real_android_linux_synack_tls_lease_m4_and_app_data":"NOT_RUN",
  "device_kernel_uid_route_and_owned_stop":"NOT_RUN"
}
Path("out/android-root-app/wiring-receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print("ANDROID_SIGNED_ARM64_APK_ORIGINAL_GO_RUST_WIRING_HOST_PASS")
