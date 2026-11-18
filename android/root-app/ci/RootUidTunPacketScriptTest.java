package org.wbdnext.rootclient;
import java.io.File;
public final class RootUidTunPacketScriptTest {
    public static void main(String[] args) {
        final String s=RootUidTunPacketScript.build(
            new File("/data/user/0/org.wbdnext.rootclient/no_backup/probe"),10234);
        for(String required:new String[]{
            "192.0.2.1/32 dev wbdst11 table 19843",
            "pref 9699 uidrange 10234-10234 lookup 19843",
            "ip -4 route get 192.0.2.1 uid 10234",
            "dev wbdst11( |$)",
            "WBD_A11_UID_TUN_SEND_READY",
            "--uid-tun-capture",
            "trap cleanup EXIT",
            "WBD_A11_UID_TUN_ROLLBACK_PASS",
            "WBD_A11_UID_TUN_ROLLBACK_FAIL",
            "WBD_A11_UID_TUN_PACKET_PASS",
            "cap_pid=$!",
            "wait \"$cap_pid\"",
            "/data/local/tmp/wbd-next-selftest",
            "[ -r /data/local/tmp/wbd-next-root/owner.pid ]",
            "ip link show dev wbdst11",
            "192.0.2.1/32 dev wbdst11 table 19843"
        })if(!s.contains(required))throw new AssertionError("missing: "+required);
        // A12: keep A11 route error explicit AND distinguish all four real
        // kernel stages. Never carry raw dynamic ip stderr into Java/logcat.
        for(String stage:new String[]{
            "WBD_A12_TUN_ROUTE_ADD_FAIL",
            "WBD_A12_TUN_ROUTE_ERR_EINVAL",
            "WBD_A12_TUN_ROUTE_ERR_EPERM",
            "WBD_A12_TUN_ROUTE_ERR_DEVICE",
            "WBD_A12_TUN_ROUTE_ERR_EXISTS",
            "WBD_A12_TUN_ROUTE_ERR_OTHER",
            "WBD_A12_UID_RULE_ADD_FAIL",
            "WBD_A12_UID_RULE_ERR_EINVAL",
            "WBD_A12_UID_RULE_ERR_EPERM",
            "WBD_A12_UID_RULE_ERR_EXISTS",
            "WBD_A12_UID_RULE_ERR_OTHER",
            "WBD_A12_UID_RULE_SHOW_UNAVAILABLE",
            "WBD_A12_UID_RULE_READBACK_FAIL",
            "WBD_A12_TUN_ROUTE_SHOW_UNAVAILABLE",
            "WBD_A12_TUN_ROUTE_READBACK_FAIL",
            "WBD_A12_TUN_INTERFACE_DISAPPEARED"
        })if(!s.contains(stage))throw new AssertionError("missing fixed A12 stage "+stage);
        int routeAdd=s.indexOf("if ! ip -4 route add 192.0.2.1/32");
        int ruleAdd=s.indexOf("if ! ip -4 rule add pref 9699");
        int ruleRead=s.indexOf("if ! ip -4 rule show >");
        int routeRead=s.indexOf("if ! ip -4 route show table 19843 >");
        int kernelLookup=s.indexOf("if ! ip -4 route get 192.0.2.1 uid");
        if(routeAdd<0||ruleAdd<routeAdd||ruleRead<ruleAdd||
           routeRead<ruleRead||kernelLookup<routeRead)
            throw new AssertionError("incorrect gated kernel stage order");
        if(s.indexOf("WBD_A12_TUN_ROUTE_ADD_FAIL")>s.indexOf("route=1;")||
           s.indexOf("WBD_A12_UID_RULE_ADD_FAIL")>s.indexOf("rule=1;"))
            throw new AssertionError("ownership tracking must follow success");
        if(!s.contains("rm -f")||
           !s.contains(".a12.err")||
           !s.contains(".a12.rules")||
           !s.contains(".a12.routes"))
            throw new AssertionError("temporary errno/output buffers not cleaned");
        if(s.contains("ip -4 route add default")||
           s.contains("ip route replace default")||
           s.contains("ip -4 rule flush")||
           s.contains("ip route flush")||
           s.contains("iptables ")||s.contains("nft ")||
           s.contains("uidrange 1000-")||
           s.contains("table 19842")||
           s.contains("pref 9600 ")||
           s.contains("--tcp53")||s.contains("su 0"))
            throw new AssertionError("debug packet harness unsafe scope");
        if(!RootUidTunPacketScript.PAYLOAD.equals("WBD_A11_TUN_UID")||
           RootUidTunPacketScript.PORT!=43999||
           !RootUidTunPacketScript.DEST.equals("192.0.2.1"))
            throw new AssertionError("diagnostic packet identity changed");
        int guard=s.indexOf("if ! ip -4 route get 192.0.2.1 uid");
        int emit=s.indexOf("echo WBD_A11_UID_TUN_SEND_READY");
        int arm=s.indexOf(": > \"$p/.uidarmed\"");
        if(arm<=guard||arm>=emit)
            throw new AssertionError("native FD must arm only after UID lookup");
        if(s.split("\\.uidarmed",-1).length!=4)
            throw new AssertionError("arming must have start/final cleanup");
        int join=s.indexOf("if wait \"$cap_pid\"");
        if(guard<0||emit<guard||join<emit)
            throw new AssertionError("flow must be gated by exact UID kernel route");
        try{
            RootUidTunPacketScript.build(new File("relative"),10234);
            throw new AssertionError("relative helper accepted");
        }catch(IllegalArgumentException expected){}
        try{
            RootUidTunPacketScript.build(new File("/tmp/secret"),999);
            throw new AssertionError("system UID accepted");
        }catch(IllegalArgumentException expected){}
        String escaped=RootUidTunPacketScript.quote("abc'xyz");
        if(!escaped.equals("'abc'\\''xyz'"))
            throw new AssertionError("POSIX injection quote failure");
        System.out.println("ANDROID_ARM64_A11_REAL_UID_TUN_PACKET_SCRIPT_HOST_PASS");
    }
}
