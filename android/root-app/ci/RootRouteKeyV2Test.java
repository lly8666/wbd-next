package org.wbdnext.rootclient;

import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.Arrays;

public final class RootRouteKeyV2Test {
    private static void same(String a,String b){if(!a.equals(b))throw new AssertionError("v2 source vector mismatch");}
    private static void reject(Runnable task){
        try{task.run();throw new AssertionError("accepted invalid v2 input");}
        catch(IllegalArgumentException correct){}
    }
    private static void check(String input,String expected)throws Exception{
        byte[] key=RootRouteKeyV2.derive(input);
        try{
            same(RootRouteKeyV2.hex(key),expected);
            String record=RootRouteKeyV2.record(key,input);
            byte[] from=RootRouteKeyV2.verifiedCache(record,input);
            if(from==null||!MessageDigest.isEqual(key,from))
                throw new AssertionError("v2 cache verification mismatch");
            Arrays.fill(from,(byte)0);
            String alternative=input.equals("Abc12345")?"Abc12346":"Abc12345";
            if(RootRouteKeyV2.verifiedCache(record,alternative)!=null)
                throw new AssertionError("old key reused after rotation");
            for(String corruption:new String[]{"v1\n"+record,"{bad","v2\n"+expected+"\nX\n",
                    "v2\n"+expected+"\n"+expected+"\nextra\n"}){
                reject(()->{
                    try{RootRouteKeyV2.verifiedCache(corruption,input);}
                    catch(GeneralSecurityException e){throw new AssertionError(e);}
                });
            }
        }finally{Arrays.fill(key,(byte)0);}
    }
    public static void main(String[] args)throws Exception{
        check("Abc12345","b3745a18edd59a1ce6aa2586ae5d90c3ec2eee3fbfafa059783e4492e2bc0539");
        check("A1b2C3d4E5f6G7h8","68ef025a9224cafa38c55e4fad14eec0fece1642c8679a41368fee0f5702033e");
        check("ABCdef0123456789ABCdef0123456789","fcb0fd63fb6e807da50afc7d1c39a9df68b7c39ae67ed2cc2db76ebe9127054e");
        for(String bad:new String[]{"","1234567","abc-def123","ABC_12345","ABC 12345",
                "abc\n12345","中文abc1234","123456789012345678901234567890123"}){
            reject(()->RootRouteKeyV2.validateShort(bad));
        }
        if(RootRouteKeyV2.hex(RootRouteKeyV2.derive("Abc12345"))
                .equals(RootRouteKeyV2.hex(RootRouteKeyV2.derive("abc12345"))))
            throw new AssertionError("v2 case sensitivity lost");
        same(RootRouteKeyV2.canonicalLegacyHex(
            "B3745A18EDD59A1CE6AA2586AE5D90C3EC2EEE3FBFAFA059783E4492E2BC0539"),
            "b3745a18edd59a1ce6aa2586ae5d90c3ec2eee3fbfafa059783e4492e2bc0539");
        reject(()->RootRouteKeyV2.canonicalLegacyHex("Abc12345"));
        System.out.println("ANDROID_ROOT_LITE_V2_SHORT_ROUTEKEY_MAIN_GO_VECTORS_HOST_PASS");
    }
}
