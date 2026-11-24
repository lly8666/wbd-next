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
        System.out.println("ANDROID_B61_ORIGINAL_OWNER_COLD_ROTATION_HOST_PASS");
    }
}
