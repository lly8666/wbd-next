package org.wbdnext.rootclient;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;

public final class RootSavedCredentialRecordTest{
    private static void refused(Runnable fn){
        boolean failed=false;
        try{fn.run();}catch(Exception expected){failed=true;}
        if(!failed)throw new AssertionError("invalid secret record accepted");
    }
    public static void main(String[] args)throws Exception{
        KeyGenerator kg=KeyGenerator.getInstance("AES");
        kg.init(256);
        SecretKey key=kg.generateKey(),wrong=kg.generateKey();
        for(String route:new String[]{"Abc12345","A1b2C3d4E5f6G7h8J9k0",
          "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}){
            String password="test-password-测试-🚀-not-for-logs";
            byte[] sealed=RootSavedCredentialRecord.encrypt(key,password,route);
            byte[] sealedAgain=RootSavedCredentialRecord.encrypt(key,password,route);
            // The provider (not app code) must generate a fresh GCM IV.
            if(Arrays.equals(sealed,sealedAgain))
                throw new AssertionError("GCM IV/ciphertext repeated");
            if(!route.equals(RootSavedCredentialRecord.decrypt(key,sealedAgain).routeKey))
                throw new AssertionError("second provider IV was not readable");
            String printable=new String(sealed,StandardCharsets.ISO_8859_1);
            if(printable.contains(password)||printable.contains(route))
                throw new AssertionError("persisted plaintext credential");
            RootSavedCredentialRecord.Secrets recovered=
                RootSavedCredentialRecord.decrypt(key,sealed);
            if(!password.equals(recovered.password)||!route.equals(recovered.routeKey))
                throw new AssertionError("encrypted persistence lost secrets");
            byte[] tampered=sealed.clone();
            tampered[tampered.length-1]^=1;
            refused(()->{
                try{RootSavedCredentialRecord.decrypt(key,tampered);}
                catch(Exception e){throw new IllegalStateException(e);}
            });
            refused(()->{
                try{RootSavedCredentialRecord.decrypt(wrong,sealed);}
                catch(Exception e){throw new IllegalStateException(e);}
            });
            sealed[0]^=1;
            refused(()->{
                try{RootSavedCredentialRecord.decrypt(key,sealed);}
                catch(Exception e){throw new IllegalStateException(e);}
            });
        }
        for(String route:new String[]{"short","contains-hyphen",
                "route key spaced","0000111122223333444455556666777788889999aaaabbbbccccddddffffeeeezzzz"}){
            refused(()->{
                try{RootSavedCredentialRecord.encrypt(key,"secret",route);}
                catch(Exception e){throw new IllegalStateException(e);}
            });
        }
        refused(()->{
            try{RootSavedCredentialRecord.encrypt(key,"","Abc12345");}
            catch(Exception e){throw new IllegalStateException(e);}
        });
        System.out.println("ANDROID_A39_PROVIDER_GENERATED_GCM_IV_REAL_JVM_HOST_PASS");
        System.out.println("ANDROID_A38_SAVED_CREDENTIAL_AES_GCM_REAL_JVM_ROUNDTRIP_TAMPER_HOST_PASS");
    }
}
