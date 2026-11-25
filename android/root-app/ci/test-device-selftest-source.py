#!/usr/bin/env python3
"""Retired A12 standalone debug path is no longer in product APK."""
from pathlib import Path
base=Path("android/root-app")
activity=(base/"src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
payload=(base/"src/org/wbdnext/rootclient/NativePayload.java").read_text()
arm=(base/"ci/build-source-locked.sh").read_text()
x86=(base/"ci/build-x86-ci-locked.sh").read_text()
assert "runDeviceSelfTest()" not in activity and "RootDeviceSelfTest" not in activity
assert "stageDeviceSelfTest" not in payload
for build in (arm,x86):
    assert "! -name 'RootDeviceSelfTest.java'" in build
    assert "! -name 'RootUidTunPacketScript.java'" in build
assert "device-selftest-arm64.c" not in arm
assert '"device_kernel_selftest_execution":"RETIRED"' in arm
assert "诊断与恢复" in activity and "导出诊断" in activity
print("ANDROID_B124_LEGACY_DEBUG_RETIRED_FROM_PRODUCT_APK_PASS")
