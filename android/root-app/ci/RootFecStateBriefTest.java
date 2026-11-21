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
        refused(null);
        System.out.println("ANDROID_B20_FEC_NATIVE_REVISION_STATUS_HOST_PASS");
    }
}
