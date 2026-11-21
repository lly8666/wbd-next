package org.wbdnext.rootclient;

/**
 * B7 purely local, current-session brief of already allowlisted diagnostic
 * fields. No Android framework, network, Root, logcat or raw native stdout.
 * Never displays IP addresses, DNS QNAMEs, credentials or private UID data.
 */
final class RootDNSStatusBrief {
    private RootDNSStatusBrief(){}
    private static final String[] KEYS={
        "tunnel_dns_live",
        "physical_dns_live",
        "cn_dns_split_native_cold",
        "cn_dns_split_route_copies",
        "cn_dns_split_live",
        "dns_tcp53_passthrough",
        "physical_dns_truncated_reply",
        "system_netd_dns_capture"
    };
    private static final String[] LABELS={
        "隧道DNS实际收发",
        "物理DNS实际收发",
        "CN8503原生模式",
        "CN/非CN发包",
        "双出口TUN回包",
        "TCP53原隧道",
        "物理TC回写",
        "Android系统DNS"
    };
    static String fromReport(String report){
        if(report==null||!report.startsWith(
            "WBD_ANDROID_ROOT_SAFE_DIAGNOSTIC_V1\n"))return "尚无本机有效诊断";
        String[] lines=report.split("\n",-1);
        StringBuilder out=new StringBuilder(550);
        for(int i=0;i<KEYS.length;i++){
            String value="NOT_OBSERVED";
            String prefix=KEYS[i]+"=";
            for(String line:lines){
                if(!line.startsWith(prefix))continue;
                String candidate=line.substring(prefix.length());
                if(candidate.length()<1||candidate.length()>90)continue;
                boolean valid=true;
                for(int j=0;j<candidate.length();j++){
                    char c=candidate.charAt(j);
                    if(!((c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_')){
                        valid=false;break;
                    }
                }
                if(valid)value=candidate;
                break;
            }
            out.append(LABELS[i]).append(": ").append(value).append('\n');
        }
        out.append("只反映本会话原生收据；不代表浏览器DNS、系统netd或手机E2E已通过");
        return out.toString();
    }
}
