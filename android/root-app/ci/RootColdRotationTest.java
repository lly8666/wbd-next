package org.wbdnext.rootclient;
public final class RootColdRotationTest {
    private static void ok(boolean v,String why){if(!v)throw new AssertionError(why);}
    public static void main(String[] args){
        ok(RootColdRotation.delayMillis(0)==0,"default off");
        ok(RootColdRotation.delayMillis(5)==300000L,"five minutes");
        ok(RootColdRotation.delayMillis(15)==900000L,"fifteen minutes");
        ok(RootColdRotation.delayMillis(30)==1800000L,"thirty minutes");
        try{RootColdRotation.delayMillis(1);throw new AssertionError("invalid interval");}
        catch(IllegalArgumentException expected){}
        ok(!RootColdRotation.mayRestart(false,true,true),"ordinary/manual Stop");
        ok(!RootColdRotation.mayRestart(true,false,true),"incomplete original Stop");
        ok(!RootColdRotation.mayRestart(true,true,false),"old physical scope changed");
        ok(RootColdRotation.mayRestart(true,true,true),"joined cold rotation");
        ok(RootColdRotation.recoveryIndex(20,0,new long[]{10,20},
            new boolean[]{true,false})==1,"actual physical default wins");
        ok(RootColdRotation.recoveryIndex(10,10,new long[]{10,20},
            new boolean[]{true,true})==1,"lost or blocked old handle excluded");
        ok(RootColdRotation.recoveryIndex(0,0,new long[]{10,20},
            new boolean[]{false,true})==1,"validated alternate underlay");
        ok(RootColdRotation.recoveryIndex(0,0,new long[]{10},
            new boolean[]{false})==0,"sole LAN-only physical underlay");
        ok(RootColdRotation.recoveryIndex(0,0,new long[]{10,20},
            new boolean[]{false,false})==-1,"ambiguous LAN waits");
        ok(RootColdRotation.recoveryIndex(0,0,new long[]{},new boolean[]{})==-1,
            "no Network waits for callback, not busy retry");
        System.out.println("ANDROID_B61_ORIGINAL_OWNER_COLD_ROTATION_HOST_PASS");
        System.out.println("ANDROID_B62_COLD_NETWORK_RECOVERY_SELECTION_HOST_PASS");
    }
}
