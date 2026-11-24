package org.wbdnext.rootclient;
public final class RootUiRoutingTest {
    public static void main(String[] args){
        if(RootUiRouting.isSplit(false,false,false,false,"",""))throw new AssertionError("default full");
        if(!RootUiRouting.isSplit(true,true,false,false,"",""))throw new AssertionError("CN split");
        if(!RootUiRouting.isSplit(false,false,false,false,"192.168.0.0/16",""))throw new AssertionError("manual");
        if(!RootUiRouting.isSplit(false,false,false,false,"","2001:db8::/32"))throw new AssertionError("IPv6");
        System.out.println("ANDROID_UI_ROUTING_POLICY_PASS");
    }
}
