package org.wbdnext.rootclient;
public final class RootColdNetworkSwitchTest {
    private static void ok(boolean v,String why){if(!v)throw new AssertionError(why);}
    public static void main(String[] args){
        RootColdNetworkSwitch s=new RootColdNetworkSwitch();
        ok(!s.pending()&&!s.complete(true,true),"no unarmed Root relaunch");
        s.arm(10L,"wlan0",12,1500,"192.0.2.4");
        ok(s.matches(10L,"wlan0",12,1500,"192.0.2.4"),"exact target");
        ok(!s.matches(11L,"wlan0",12,1500,"192.0.2.4"),"network handle");
        ok(!s.matches(10L,"rmnet0",12,1500,"192.0.2.4"),"interface");
        ok(!s.matches(10L,"wlan0",13,1500,"192.0.2.4"),"ifindex");
        ok(!s.matches(10L,"wlan0",12,1400,"192.0.2.4"),"MTU");
        ok(!s.matches(10L,"wlan0",12,1500,"192.0.2.5"),"IPv4");
        ok(!s.complete(false,true)&&!s.pending(),"failed Stop cancels");
        s.arm(10L,"wlan0",12,1500,"192.0.2.4");
        ok(!s.complete(true,false)&&!s.pending(),"lost target cancels");
        s.arm(10L,"wlan0",12,1500,"192.0.2.4");
        ok(s.complete(true,true)&&!s.complete(true,true),"only one Start");
        s.arm(10L,"wlan0",12,1500,"192.0.2.4");s.cancel();
        ok(!s.pending()&&!s.complete(true,true),"pause cancels");
        System.out.println("ANDROID_B49_FOREGROUND_ONESHOT_COLD_NETWORK_HOST_PASS");
    }
}
