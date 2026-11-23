package org.wbdnext.rootclient;

/** Exact production native status decoder; no Android guest or network. */
public final class RootFecStateBriefTest {
    private static void contains(String s,String value){
        if(s==null||!s.contains(value))throw new AssertionError(value+": "+s);
    }
    private static void refused(String text){
        if(RootFecStateBrief.fromGoLine(text)!=null)
            throw new AssertionError("unexpected accepted FEC state: "+text);
    }
    public static void main(String[] args){
        String marker="V4_PUBLIC_ANDROID_FEC_STATE role=client ";
        String pending=RootFecStateBrief.fromGoLine(
            "2026/11/22 02:22:01 "+marker+
            "mode=auto requested=2 applied=1 profile=4 pending=true");
        contains(pending,"FEC Auto");
        contains(pending,"请求版本 2");
        contains(pending,"已应用版本 1");
        contains(pending,"档位 4");
        contains(pending,"PENDING");
        String applied=RootFecStateBrief.fromGoLine(marker+
            "mode=auto requested=2 applied=2 profile=4 pending=false");
        contains(applied,"APPLIED");
        contains(applied,"不代表应用端到端");
        contains(RootFecStateBrief.fromGoLine(marker+
            "mode=fixed requested=1 applied=0 profile=6 pending=true"),
            "FEC Fixed");
        refused(marker+"mode=auto requested=2 applied=1 profile=4 pending=false");
        refused(marker+"mode=auto requested=1 applied=2 profile=4 pending=false");
        refused(marker+"mode=auto requested=0 applied=0 profile=4 pending=false");
        refused(marker+"mode=auto requested=1 applied=1 profile=8 pending=false");
        refused(marker+"mode=normal requested=1 applied=1 profile=4 pending=false");
        refused(marker+"mode=auto requested=2 applied=2 profile=4 pending=false injected=1");
        refused("2026/11/22 02:22:01 fake "+marker+
            "mode=fixed requested=1 applied=1 profile=1 pending=false");
        refused("user_password="+marker+
            "mode=fixed requested=1 applied=1 profile=1 pending=false");
        String gm="V4_PUBLIC_ANDROID_GAME2_M4_COUNTERS role=client ";
        String game=RootFecStateBrief.fromGoLine("2026/11/23 12:34:56 "+
            gm+"rawtx=16 rawrx=18 tun=12 rejected=1 dnstx=3 dnsrx=2");
        contains(game,"Game2/off 原Rust M4");
        contains(game,"RAW发送=16");
        contains(game,"隧道DNS请求=3");
        contains(game,"回包=2");
        String physical=RootFecStateBrief.fromGoLine(gm+
            "rawtx=16 rawrx=18 tun=12 rejected=1 dnstx=3 dnsrx=2 "+
            "physicaltx=7 physicalrx=6 physicalerr=1");
        contains(physical,"物理DNS发送=7");
        contains(physical,"回包=6");
        contains(physical,"错误=1");
        refused(gm+"rawtx=16 rawrx=18 tun=12 rejected=1 dnstx=3 dnsrx=2 "+
            "physicaltx=7 physicalrx=-6 physicalerr=1");
        refused(gm+"rawtx=1 rawrx=2 tun=3 rejected=0 dnstx=1 dnsrx=1 junk=x");
        refused(gm+"rawtx=-1 rawrx=2 tun=3 rejected=0 dnstx=1 dnsrx=1");
        String g4="V4_PUBLIC_ANDROID_GAME4_M4_COUNTERS role=client ";
        String four=RootFecStateBrief.fromGoLine(
            "2026/11/23 13:30:00 "+g4+
            "rawtx=40 rawrx=48 tun=12 rejected=0 dnstx=5 dnsrx=4 "+
            "physicaltx=3 physicalrx=3 physicalerr=0");
        contains(four,"Game4/off 原Rust M4");
        contains(four,"RAW发送=40");
        contains(four,"隧道DNS请求=5");
        contains(four,"物理DNS发送=3");
        refused(g4+"rawtx=40 rawrx=48 tun=12 rejected=0 dnstx=5 "+
            "dnsrx=4 physicaltx=3 physicalrx=3 physicalerr=-1");
        refused(null);
        System.out.println("ANDROID_B20_FEC_NATIVE_REVISION_STATUS_HOST_PASS");
    }
}
