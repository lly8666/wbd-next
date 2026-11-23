package org.wbdnext.rootclient;

/** One explicit user-initiated cold Network switch, no background Root grant. */
final class RootColdNetworkSwitch {
    private boolean armed;
    private long handle;
    private String iface,local;
    private int index,mtu;
    void arm(long h,String n,int i,int m,String ip){
        handle=h;iface=n;index=i;mtu=m;local=ip;armed=true;
    }
    boolean pending(){return armed;}
    boolean matches(long h,String n,int i,int m,String ip){
        return armed&&handle==h&&index==i&&mtu==m&&
            iface!=null&&iface.equals(n)&&local!=null&&local.equals(ip);
    }
    boolean complete(boolean oldStopVerified,boolean targetStillPresent){
        if(!armed)return false;
        armed=false; // single use even on failures
        return oldStopVerified&&targetStillPresent;
    }
    void cancel(){armed=false;}
}
