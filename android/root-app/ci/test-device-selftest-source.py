#!/usr/bin/env python3
"""Fail-closed STATIC audit of the exact ARM64 on-device self-test sources.

No host assertion is evidence that real Android16 KSU/TUN/UID routes passed.
The DEBUG-only native C helper is built and ABI-checked by the signed APK CI.
"""
from pathlib import Path

base=Path("android/root-app")
java=(base/"src/org/wbdnext/rootclient/RootDeviceSelfTest.java").read_text()
native=(base/"ci/device-selftest-arm64.c").read_text()
activity=(base/"src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
payload=(base/"src/org/wbdnext/rootclient/NativePayload.java").read_text()
build=(base/"ci/build-source-locked.sh").read_text()

for token in (
    '192.0.2.1/32', 'table 19843', 'pref 9699',
    'uidrange ").append(ownUid)', 'ip -4 route del 192.0.2.1/32',
    "trap cleanup EXIT", 'ROUTE_ROLLBACK_PASS',
    'ROOT_FAIL','GO_ELF_HELP_PASS', 'GO_ELF_SIGSEGV',
    'TUN_PASS', 'RAW_PASS', 'UNDERLAY_PASS','ROUTE_UID_PASS',
    'ROOT_RUN_EXIT_NONZERO','source',
):
    assert token in java,token
assert 'ip -4 route add default' not in java
assert 'ip -4 route replace default' not in java
assert 'route flush' not in java
assert 'iptables' not in java and 'nft ' not in java
assert '--help' in java and 'android-network-handle' in java
assert 'WBD_SELFTEST_' in java
assert 'return "' in java
for token in ("TUNSETIFF","IFF_TUN | IFF_NO_PI", "close(fd)",
              "AF_PACKET", "SOCK_RAW", "SO_BINDTODEVICE", "SIOCGIFINDEX",
              "#error", "__aarch64__"):
    assert token in native,token
for forbidden in ("sendto(", "recvfrom(", "write(fd,", "TUNSETPERSIST",
                  "192.0.2.1", "github.com/lly8666"):
    assert forbidden not in native,forbidden
assert 'runDeviceSelfTest()' in activity
assert 'AlertDialog.Builder(this)' in activity
assert '允许本机测试' in activity
assert 'one-tap' not in activity.lower() or 'selftest' in activity.lower()
assert 'stageDeviceSelfTest' in payload
assert 'device-selftest-sha256.txt' in payload
assert 'aarch64-linux-android28-clang' in build
assert 'device-selftest-arm64.c' in build
assert 'sha256sum "$assets/device-selftest-arm64"' in build
assert '"debug_only_tun_raw_uid_routing_selftest_asset":True' in build
assert '"device_kernel_selftest_execution":"NOT_RUN"' in build
print("ANDROID_ARM64_ONE_TAP_SELFTEST_STATIC_SCOPE_AND_SHA_AUDIT_PASS")
