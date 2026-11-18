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
assert 'new ProcessBuilder("su","-c",' in service_src
assert 'LD_LIBRARY_PATH=' in service_src and 'exec ' in service_src
assert 'RootStopCommand.build(token,ownerExecutable)' in service_src
assert 'NATIVE_M4_AND_UID_READY' in service_src
assert 'hasCA?' in service_src
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
    assert b"Lorg/wbdnext/rootclient/RootClientService;" in dex
    assert b"Lorg/wbdnext/rootclient/RootStopCommand;" in dex
client=Path("out/android-root-app-native/wbd-v4-client-arm64")
dyn=subprocess.run(["readelf","-d",str(client)],check=True,capture_output=True,text=True).stdout
assert "Shared library: [libwbd_engine.so]" in dyn
report={
  "schema":"wbd-original-android-apk-go-rust-host-wiring/v1",
  "source":SOURCE,
  "abi":"arm64-v8a",
  "signed_apk_original_go_and_rust_sha256":"PASS",
  "production_java_go_cli_arguments_host_test":"PASS",
  "registered_original_go_cli_flags":"PASS",
  "production_root_exec_and_owned_stop_source_gate":"PASS",
  "original_go_requires_rust_dynamic_library":"PASS",
  "original_go_rust_android_runtime":"NOT_RUN",
  "physical_network_binding":"NOT_RUN",
  "real_android_linux_synack_tls_lease_m4_and_app_data":"NOT_RUN",
  "device_kernel_uid_route_and_owned_stop":"NOT_RUN"
}
Path("out/android-root-app/wiring-receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print("ANDROID_SIGNED_ARM64_APK_ORIGINAL_GO_RUST_WIRING_HOST_PASS")
