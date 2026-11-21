package org.wbdnext.rootclient;

/** Test production parser using only the existing M4 numeric wire receipt. */
public final class RootM4TrafficBriefTest {
    private static void contains(String s,String text){
        if(s==null||!s.contains(text))throw new AssertionError("expected "+text+" in "+s);
    }
    private static String m4(long tun,long raw,long rev){
        return "kind=m4 poll=2 parse_fail=0 parsed=20 auth=18 rejected=2"+
            " writefail=0 tun="+tun+" trej=0 rawtx="+raw+" rtun="+rev+
            " tcp=2 udp=3 icmp=0 dnsudp=0 dnstcp=0 dnsraw=0 dnsrtun=0"+
            " dnsptx=0 dnsprx=0 dnsperr=0 rxerr=0 txerr=0 health=1";
    }
    public static void main(String[] args){
        String prefix="WBD_ANDROID_ROOT_SAFE_DIAGNOSTIC_V1\n"+
            "native_m4_numeric_debug_samples:\n";
        String r=prefix+"1770000000000|NATIVE_M4_DIAG "+m4(8,7,5)+"\n"+
            "1770000000300|NATIVE_M4_DIAG "+m4(11,10,9)+"\n"+
            "native_dns_b6_numeric_debug_count=0\n";
        String view=RootM4TrafficBrief.fromReport(r);
        contains(view,"TUN入站=11");
        contains(view,"原 RAW 已复制=10");
        contains(view,"M3 认证记录=18");
        contains(view,"反向 TUN 已写入=9");
        contains(view,"不是应用端到端");
        if(view.contains("198.51.100.")||view.contains("password"))
            throw new AssertionError("raw endpoints leaked");
        String invalid=prefix+
            "1770000000300|NATIVE_M4_DIAG "+m4(11,10,9)+" password=SECRET\n";
        contains(RootM4TrafficBrief.fromReport(invalid),"尚未观察到");
        contains(RootM4TrafficBrief.fromReport("not a report"),"尚无有效");
        contains(RootM4TrafficBrief.fromReport(prefix),"尚未观察到");
        System.out.println("ANDROID_B21_M4_REAL_PACKET_RECEIPT_BRIEF_HOST_PASS");
    }
}
