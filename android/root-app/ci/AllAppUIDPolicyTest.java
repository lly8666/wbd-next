package org.wbdnext.rootclient;

import java.util.Arrays;
public final class AllAppUIDPolicyTest {
    private static int assertions=0;
    private static void check(boolean ok,String text){
        assertions++;
        if(!ok)throw new AssertionError(text);
    }
    private static void rejects(Runnable r,String what){
        boolean denied=false;
        try{r.run();}catch(IllegalArgumentException expected){denied=true;}
        check(denied,what);
    }
    public static void main(String[] args){
        check(AllAppUIDPolicy.appId(10111)==10111,"owner user0");
        check(AllAppUIDPolicy.appId(110111)==10111,"same App ID user1");
        int[] excluded=AllAppUIDPolicy.excluded(110111,new int[]{10222,210333});
        check(Arrays.equals(excluded,new int[]{10111,10222,10333}),"exclude owner/manager all profiles");
        check("10111,10222,10333".equals(AllAppUIDPolicy.csv(excluded)),"canonical csv");
        rejects(()->AllAppUIDPolicy.appId(0),"root never selected");
        rejects(()->AllAppUIDPolicy.appId(1000),"system uid never selected");
        rejects(()->AllAppUIDPolicy.appId(101001),"secondary system AID never selected");
        check(AllAppUIDPolicy.appId(119999)==19999,"other profile ordinary UID");
        rejects(()->AllAppUIDPolicy.excluded(10111,new int[0]),"manager must be known");
        rejects(()->AllAppUIDPolicy.excluded(10111,new int[]{10111}),"cannot share controller UID");
        rejects(()->AllAppUIDPolicy.csv(new int[]{10222,10111}),"sorted required");
        rejects(()->AllAppUIDPolicy.csv(new int[]{10111,10111}),"unique required");
        System.out.println("ANDROID_ALL_APP_UID_SCOPE_DEFAULT_SAFETY_PASS assertions="+assertions);
    }
}
