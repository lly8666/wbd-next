package org.wbdnext.rootclient;

/**
 * Read-only recent packet counters from the EXISTING original Rust M4
 * allowlisted numeric diagnostic, never an extra TUN/RAW reader.
 * No IP addresses, ports, usernames, DNS names or packet bytes displayed.
 */
final class RootM4TrafficBrief {
    private RootM4TrafficBrief(){}
    private static final String MARKER="|NATIVE_M4_DIAG ";
    private static String counter(String[] tokens,String name){
        String prefix=name+"=";
        for(String token:tokens)if(token.startsWith(prefix))
            return token.substring(prefix.length());
        return null;
    }
    static String fromReport(String report){
        if(report==null||!report.startsWith(
            "WBD_ANDROID_ROOT_SAFE_DIAGNOSTIC_V1\n"))
            return "尚无有效本机内核诊断";
        String latest=null;
        // Select only kind=m4, not kind=rx (the latter has numeric IP/ports).
        int start=report.indexOf("native_m4_numeric_debug_samples:\n");
        if(start<0)return "尚未观察到原生M4收发";
        String[] lines=report.substring(start).split("\n");
        for(String line:lines){
            int i=line.indexOf(MARKER);
            if(i<0)continue;
            String payload=line.substring(i+MARKER.length());
            if(!payload.startsWith("kind=m4 "))continue;
            if(!RootDiagnosticReceipt.safeNativeSnapshot(
                "V4_PUBLIC_ANDROID_M4_DIAG role=client "+payload))continue;
            latest=payload;
        }
        if(latest==null)return "尚未观察到原生M4收发";
        String[] tokens=latest.split(" ");
        String tun=counter(tokens,"tun");
        String tcp=counter(tokens,"tcp");
        String udp=counter(tokens,"udp");
        String raw=counter(tokens,"rawtx");
        String authenticated=counter(tokens,"auth");
        String reverse=counter(tokens,"rtun");
        if(tun==null||tcp==null||udp==null||raw==null||
           authenticated==null||reverse==null)
            return "原生M4收据不完整";
        return "最近一次真实 Rust M4 内核收据：\n"+
            "TUN入站="+tun+"（TCP="+tcp+"，UDP="+udp+"）\n"+
            "原 RAW 已复制="+raw+"\n"+
            "M3 认证记录="+authenticated+"\n"+
            "反向 TUN 已写入="+reverse+"\n"+
            "可能来自刚结束的会话；不是应用端到端送达、FEC生效或性能证明";
    }
}
