package org.wbdnext.rootclient;

// B34: the real Android Root product's physically bound UDP/53 destination.
// A LOCAL router DNS IPv4 (e.g. 192.168.1.1) is valid when the selected
// physical Android Network can actually reach it. Neither system netd
// resolver nor original TLS server bootstrap is modified by this field.
final class RootPhysicalDNSUpstream {
    static final String DEFAULT="223.5.5.5";
    private RootPhysicalDNSUpstream(){}
    static String canonical(String raw){
        if(raw==null||raw.trim().isEmpty())return DEFAULT;
        String[] items=raw.trim().split("\\.",-1);
        if(items.length!=4)throw new IllegalArgumentException("物理DNS上游必须是IPv4地址");
        int[] parts=new int[4];
        for(int i=0;i<4;i++){
            String x=items[i];
            if(x.isEmpty()||x.length()>3||(x.length()>1&&x.charAt(0)=='0'))
                throw new IllegalArgumentException("IPv4物理DNS数字格式错误");
            int n=0;
            for(int j=0;j<x.length();j++){
                char c=x.charAt(j);
                if(c<'0'||c>'9')throw new IllegalArgumentException("DNS上游不能是域名/IPv6");
                n=n*10+c-'0';
                if(n>255)throw new IllegalArgumentException("物理DNS IPv4分段越界");
            }
            parts[i]=n;
        }
        if(parts[0]==0||parts[0]==127||parts[0]>=224||
           (parts[0]==169&&parts[1]==254))
            throw new IllegalArgumentException("物理DNS需是可路由的IPv4单播");
        return parts[0]+"."+parts[1]+"."+parts[2]+"."+parts[3];
    }
}
