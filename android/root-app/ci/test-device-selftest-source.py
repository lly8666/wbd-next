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
    'ROOT_RUN_EXIT_NONZERO','SOURCE_AND_APK_ASSET_SHA=PASS',
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
for forbidden in ("sendto(", "recvfrom(", "write(fd,", "ioctl(fd, TUNSETPERSIST",
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

# A11 is a true, single kernel-routed app-UID UDP packet, never mocked TLS.
# The Android app process sends the packet; ROOT/NDK only captures it.
packet=(base/"src/org/wbdnext/rootclient/RootUidTunPacketScript.java").read_text()
for token in ("192.0.2.1/32 dev wbdst11 table 19843",
              "pref 9699 uidrange ",
              "ip -4 route get 192.0.2.1 uid ",
              "dev wbdst11( |$)",
              "WBD_A11_UID_TUN_SEND_READY",
              "WBD_A11_UID_TUN_PACKET_PASS",
              "WBD_A11_UID_TUN_ROLLBACK_PASS",
              "trap cleanup EXIT",
              "if wait",
              "cap_pid=$!",
              "198.18.0.1/30",
              "WBD_A11_TUN_UID"):
    assert token in packet,token
for forbidden in ("route add default", "route replace default",
                  "table 19842", "pref 9600", "iptables ",
                  "nft ", "netd", "--server", "tcpdump"):
    assert forbidden not in packet,forbidden
selftest=java
for token in ("new DatagramSocket()",
              "new DatagramPacket(",
              "InetAddress.getByAddress(reserved)",
              "RootUidTunPacketScript.PAYLOAD.getBytes(",
              "RootUidTunPacketScript.build(",
              "UID_TUN_PACKET_PASS",
              "UID_TUN_ROLLBACK_PASS",
              "REAL_APP_UID_TO_TEMP_TUN_PACKET=PASS"):
    assert token in selftest,token
assert selftest.index("nativeCaptureConfirmed&&sendAttempted&&cleanupConfirmed")>0
for token in ("--uid-tun-capture", "poll(&pfd, 1, 9500)",
              "192 && packet[17] == 0", "packet[ihl+3]) == 43999",
              "memcmp(packet + ihl + 8, payload, sizeof(payload)-1)",
              "close(fd)", "O_EXCL", "O_NOFOLLOW"):
    assert token in native,token
assert 'sendto(' not in native and 'TUNSETPERSIST, &ifr' not in native
assert 'device-selftest-arm64.c' in build
# A12: disaggregate the real device's A11_UID_TUN_ROUTE_FAIL into
# exact stage and bounded errno categories, retaining the original
# fail-closed no-send guard and exact owned-resource cleanup.
for token in (
    "WBD_A12_TUN_ROUTE_ADD_FAIL", "WBD_A12_TUN_ROUTE_ERR_EINVAL",
    "WBD_A12_TUN_ROUTE_ERR_EPERM", "WBD_A12_TUN_ROUTE_ERR_DEVICE",
    "WBD_A12_TUN_ROUTE_ERR_EXISTS", "WBD_A12_TUN_ROUTE_ERR_OTHER",
    "WBD_A12_UID_RULE_ADD_FAIL", "WBD_A12_UID_RULE_ERR_EINVAL",
    "WBD_A12_UID_RULE_ERR_EPERM", "WBD_A12_UID_RULE_ERR_OTHER",
    "WBD_A12_UID_RULE_READBACK_FAIL",
    "WBD_A12_TUN_ROUTE_READBACK_FAIL",
    "WBD_A12_TUN_INTERFACE_DISAPPEARED",
    '.a12.err', "rm -f", '.a12.rules', '.a12.routes'
):
    assert token in packet, token
for token in ("UID_PACKET_DIAG_EVENTS", 'line.startsWith("WBD_A12_")',
              "allowedUidPacketDiag(diagnostic)", 'events.add("A12_"+diagnostic)'):
    assert token in selftest, token
assert 'echo "$p/.a12.err"' not in packet
assert "WBD_A11_UID_TUN_SEND_READY" in packet
print("ANDROID_ARM64_A12_GRANULAR_ROUTE_FAILURE_DIAG_AUDIT_PASS")
print("ANDROID_ARM64_A11_ACTUAL_UID_TO_TUN_PACKET_SCOPE_AUDIT_PASS")
print("ANDROID_ARM64_ONE_TAP_SELFTEST_STATIC_SCOPE_AND_SHA_AUDIT_PASS")
