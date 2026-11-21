package org.wbdnext.rootclient;

import java.io.File;

/**
 * Debug-only one-UID, one-reserved-destination real kernel packet test.
 * Strictly no original Go/Rust TLS, no VPN, no production table19842,
 * no system DNS and no other application's UID. Shell owns all rollback.
 * Pure Java script generation is host-tested before signing into APK.
 */
final class RootUidTunPacketScript {
    private RootUidTunPacketScript(){}
    static final String READY="UID_TUN_SEND_READY";
    static final String PAYLOAD="WBD_A11_TUN_UID";
    static final int PORT=43999;
    static final String DEST="192.0.2.1";
    static final String IFACE="wbdst11";
    static final String ROOT="/data/local/tmp/wbd-next-selftest";
    static final int ROUTE_PREF=9699;
    static final int TABLE=19843;
    static String quote(String v) {
        if(v==null)throw new IllegalArgumentException("missing path");
        return "'"+v.replace("'","'\\''")+"'";
    }
    static String build(File sourceLockedHelper,int ownUid) {
        if(sourceLockedHelper==null||!sourceLockedHelper.isAbsolute()||
           ownUid<10000||ownUid>999999999)
            throw new IllegalArgumentException("invalid diagnostic UID/helper");
        StringBuilder sh=new StringBuilder(8000);
        sh.append("set -u; umask 077; PATH=/system/bin:/system/xbin:/vendor/bin; export PATH; ");
        sh.append("p=").append(quote(ROOT)).append("; ");
        sh.append("if [ \"$(id -u)\" != 0 ]; then echo WBD_A11_ROOT_FAIL; exit 71; fi; ");
        sh.append("if [ -r /data/local/tmp/wbd-next-root/owner.pid ]; then ");
        sh.append("echo WBD_A11_REFUSED; exit 72; fi; ");
        sh.append("if [ -L \"$p\" ] || [ ! -d \"$p\" ] || ");
        sh.append("[ \"$(stat -c %u \"$p\" 2>/dev/null)\" != 0 ] || ");
        sh.append("[ \"$(stat -c %a \"$p\" 2>/dev/null)\" != 700 ]; then ");
        sh.append("echo WBD_A11_REFUSED; exit 73; fi; ");
        sh.append("if ! mkdir \"$p/.uidpacket.lock\" 2>/dev/null; then ");
        sh.append("echo WBD_A11_REFUSED; exit 74; fi; ");
        sh.append("rule=0; route=0; cap_pid=0; ");
        sh.append("cleanup(){ ");
        sh.append("if [ \"$rule\" = 1 ]; then ");
        sh.append("ip -4 rule del pref 9699 uidrange ").append(ownUid).append("-");
        sh.append(ownUid).append(" lookup 19843 >/dev/null 2>&1 || :; fi; ");
        sh.append("if [ \"$route\" = 1 ]; then ");
        sh.append("ip -4 route del 192.0.2.1/32 dev wbdst11 table 19843 >/dev/null 2>&1 || :; fi; ");
        sh.append("if [ \"$cap_pid\" != 0 ]; then ");
        sh.append("kill \"$cap_pid\" >/dev/null 2>&1 || :; ");
        sh.append("wait \"$cap_pid\" 2>/dev/null || :; fi; ");
        sh.append("if ip -4 rule show 2>/dev/null | grep -Eq '^ *9699:' || ");
        sh.append("ip -4 route show table 19843 2>/dev/null | grep -q '[^[:space:]]' || ");
        sh.append("ip link show dev wbdst11 >/dev/null 2>&1; then ");
        sh.append("echo WBD_A11_UID_TUN_ROLLBACK_FAIL; ");
        sh.append("else echo WBD_A11_UID_TUN_ROLLBACK_PASS; fi; ");
        sh.append("rm -f \"$p/.uidready\" \"$p/.uidarmed\" \"$p/.uidcapture\" ");
        sh.append("\"$p/.a12.err\" \"$p/.a12.rules\" \"$p/.a12.routes\"; ");
        sh.append("rmdir \"$p/.uidpacket.lock\" 2>/dev/null || :; }; ");
        sh.append("trap cleanup EXIT; trap 'exit 79' HUP INT TERM; ");
        // No operation can clobber a rule/table/interface from another owner.
        sh.append("if ip -4 rule show 2>/dev/null | grep -Eq '^ *9699:' || ");
        sh.append("ip -4 route show table 19843 2>/dev/null | grep -q '[^[:space:]]' || ");
        sh.append("ip link show dev wbdst11 >/dev/null 2>&1; then ");
        sh.append("echo WBD_A11_UID_TUN_COLLISION; exit 75; fi; ");
        sh.append("rm -f \"$p/.uidready\" \"$p/.uidarmed\" \"$p/.uidcapture\" ");
        sh.append("\"$p/.a12.err\" \"$p/.a12.rules\" \"$p/.a12.routes\"; ");
        sh.append("if ! cp ").append(quote(sourceLockedHelper.getAbsolutePath()));
        sh.append(" \"$p/.uidcapture\"; then echo WBD_A11_REFUSED; exit 76; fi; ");
        sh.append("chmod 700 \"$p/.uidcapture\" || exit 76; ");
        sh.append("\"$p/.uidcapture\" --uid-tun-capture \"$p/.uidready\" ");
        sh.append(">/dev/null 2>&1 & cap_pid=$!; ");
        sh.append("n=0; ");
        sh.append("while [ ! -f \"$p/.uidready\" ] && [ \"$n\" -lt 25 ]; do ");
        sh.append("kill -0 \"$cap_pid\" 2>/dev/null || break; ");
        sh.append("sleep 0.2; n=$((n+1)); done; ");
        sh.append("if [ ! -f \"$p/.uidready\" ] || ");
        sh.append("! ip link show dev wbdst11 >/dev/null 2>&1; then ");
        sh.append("echo WBD_A11_UID_TUN_CREATE_FAIL; exit 77; fi; ");
        // Keep TUN source local to reserved benchmark range; no global
        // default route and no physical address reconfiguration.
        sh.append("if ! ip -4 addr add 198.18.0.1/30 dev wbdst11 >/dev/null 2>&1 || ");
        sh.append("! ip link set dev wbdst11 up >/dev/null 2>&1; then ");
        sh.append("echo WBD_A11_UID_TUN_SETUP_FAIL; exit 77; fi; ");
        // A12: separate failing stage and fixed errno category; never emit
        // raw Android ip stderr, UID ranges or network endpoints.
        sh.append("if ! ip link show dev wbdst11 >/dev/null 2>&1; then ");
        sh.append("echo WBD_A12_TUN_INTERFACE_DISAPPEARED; ");
        sh.append("echo WBD_A11_UID_TUN_ROUTE_FAIL; exit 77; fi; ");
        sh.append("if ! ip -4 route add 192.0.2.1/32 dev wbdst11 table 19843 ");
        sh.append(">/dev/null 2>\"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_TUN_ROUTE_ADD_FAIL; ");
        sh.append("if grep -Eqi 'Invalid argument|Numerical result out of range' \"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_TUN_ROUTE_ERR_EINVAL; ");
        sh.append("elif grep -Eqi 'Operation not permitted|Permission denied' \"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_TUN_ROUTE_ERR_EPERM; ");
        sh.append("elif grep -Eqi 'No such device|Cannot find device|Network is down' \"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_TUN_ROUTE_ERR_DEVICE; ");
        sh.append("elif grep -Eqi 'File exists' \"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_TUN_ROUTE_ERR_EXISTS; ");
        sh.append("else echo WBD_A12_TUN_ROUTE_ERR_OTHER; fi; ");
        sh.append("echo WBD_A11_UID_TUN_ROUTE_FAIL; exit 77; fi; ");
        sh.append("route=1; ");
        sh.append("if ! ip -4 rule add pref 9699 uidrange ").append(ownUid).append("-");
        sh.append(ownUid).append(" lookup 19843 >/dev/null 2>\"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_UID_RULE_ADD_FAIL; ");
        sh.append("if grep -Eqi 'Invalid argument' \"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_UID_RULE_ERR_EINVAL; ");
        sh.append("elif grep -Eqi 'Operation not permitted|Permission denied' \"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_UID_RULE_ERR_EPERM; ");
        sh.append("elif grep -Eqi 'File exists' \"$p/.a12.err\"; then ");
        sh.append("echo WBD_A12_UID_RULE_ERR_EXISTS; ");
        sh.append("else echo WBD_A12_UID_RULE_ERR_OTHER; fi; ");
        sh.append("echo WBD_A11_UID_TUN_ROUTE_FAIL; exit 77; fi; ");
        sh.append("rule=1; ");
        sh.append("if ! ip -4 rule show >\"$p/.a12.rules\" 2>/dev/null; then ");
        sh.append("echo WBD_A12_UID_RULE_SHOW_UNAVAILABLE; ");
        sh.append("echo WBD_A11_UID_TUN_ROUTE_FAIL; exit 77; fi; ");
        sh.append("if ! grep -Eq '^ *9699:' \"$p/.a12.rules\"; then ");
        sh.append("echo WBD_A12_UID_RULE_READBACK_FAIL; ");
        sh.append("echo WBD_A11_UID_TUN_ROUTE_FAIL; exit 77; fi; ");
        sh.append("if ! ip -4 route show table 19843 >\"$p/.a12.routes\" 2>/dev/null; then ");
        sh.append("echo WBD_A12_TUN_ROUTE_SHOW_UNAVAILABLE; ");
        sh.append("echo WBD_A11_UID_TUN_ROUTE_FAIL; exit 77; fi; ");
        sh.append("if ! grep -q '192.0.2.1' \"$p/.a12.routes\"; then ");
        sh.append("echo WBD_A12_TUN_ROUTE_READBACK_FAIL; ");
        sh.append("echo WBD_A11_UID_TUN_ROUTE_FAIL; exit 77; fi; ");
        // No packet is emitted unless kernel UID lookup actually selects
        // THIS ephemeral TUN. Unsupported 'uid' arg -> fail closed.
        sh.append("if ! ip -4 route get 192.0.2.1 uid ").append(ownUid);
        sh.append(" 2>/dev/null | grep -Eq 'dev wbdst11( |$)'; then ");
        sh.append("echo WBD_A11_UID_ROUTE_LOOKUP_FAIL; exit 78; fi; ");
        // Arm capture only after the kernel selects the exact owned UID route.
        sh.append("if ! : > \"$p/.uidarmed\"; then ");
        sh.append("echo WBD_A11_UID_TUN_ROUTE_FAIL; exit 77; fi; ");
        sh.append("echo WBD_A11_UID_TUN_SEND_READY; ");
        // The original APK UID sends exactly one 15-byte test UDP packet.
        // Native helper begins bounded 9.5s capture only after the
        // kernel UID route readback and 0600 arming marker. Shell
        // synchronously joins before exact cleanup.
        sh.append("if wait \"$cap_pid\"; then ");
        sh.append("cap_pid=0; echo WBD_A11_UID_TUN_PACKET_PASS; ");
        sh.append("else cap_pid=0; echo WBD_A11_UID_TUN_PACKET_FAIL; fi; ");
        sh.append("echo WBD_A11_SCRIPT_DONE; ");
        return sh.toString();
    }
}
