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
        s.armProfile(3,22L,"rmnet_data0",4,1428,"10.21.0.2");
        ok(s.pending()&&s.profileSlot()==3,"frozen third profile");
        ok(s.matches(22L,"rmnet_data0",4,1428,"10.21.0.2"),
            "profile uses exact current physical target");
        ok(!s.matches(22L,"wlan0",4,1428,"10.21.0.2"),
            "profile cannot accidentally switch physical interface");
        int savedSlot=s.profileSlot();
        ok(savedSlot==3&&s.complete(true,true)&&s.profileSlot()==0,
            "profile starts once after complete old Stop");
        ok(!s.complete(true,true),"profile cannot auto-start twice");
        s.armProfile(4,22L,"rmnet_data0",4,1428,"10.21.0.2");
        ok(!s.complete(false,true)&&s.profileSlot()==0,
            "failed old Go/Rust owner Stop consumes profile intent");
        s.armProfile(2,22L,"rmnet_data0",4,1428,"10.21.0.2");
        s.cancel();
        ok(!s.pending()&&s.profileSlot()==0,"manual STOP cancels profile intent");
        s.armProfile(1,22L,"rmnet_data0",4,1428,"10.21.0.2");
        s.arm(23L,"wlan0",9,1500,"192.0.2.3");
        ok(s.profileSlot()==0&&s.matches(23L,"wlan0",9,1500,"192.0.2.3"),
            "explicit B49 Network switch replaces prior profile request");
        System.out.println("ANDROID_B52_SAVED_PROFILE_COLD_SWITCH_HOST_PASS");
    }
}
