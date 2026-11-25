package org.wbdnext.rootclient;

/** One explicit user-initiated cold Network switch, no background Root grant. */
final class RootColdNetworkSwitch {
    private boolean armed;
    private long handle;
    private String iface,local;
    private int index,mtu,profileSlot;
    // Slot zero is the B49 same-profile Network switch; 1..10 are
    // user-selected saved connections. No change to Go/Rust owner.
    void arm(long h,String n,int i,int m,String ip){
        profileSlot=0;
        setTarget(h,n,i,m,ip);
    }
    void armProfile(int slot,long h,String n,int i,int m,String ip){
        if(slot<1||slot>RootConnectionProfile.SLOTS)
            throw new IllegalArgumentException("profile slot 1.."+RootConnectionProfile.SLOTS);
        profileSlot=slot;
        setTarget(h,n,i,m,ip);
    }
    private void setTarget(long h,String n,int i,int m,String ip){
        handle=h;iface=n;index=i;mtu=m;local=ip;armed=true;
    }
    int profileSlot(){return armed?profileSlot:0;}
    boolean pending(){return armed;}
    boolean matches(long h,String n,int i,int m,String ip){
        return armed&&handle==h&&index==i&&mtu==m&&
            iface!=null&&iface.equals(n)&&local!=null&&local.equals(ip);
    }
    boolean complete(boolean oldStopVerified,boolean targetStillPresent){
        if(!armed)return false;
        armed=false; // single use even on failures
        profileSlot=0;
        return oldStopVerified&&targetStillPresent;
    }
    void cancel(){armed=false;profileSlot=0;}
}
