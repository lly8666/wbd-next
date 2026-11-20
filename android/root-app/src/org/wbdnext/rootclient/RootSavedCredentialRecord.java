package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

// Pure-Java production codec, host-tested with real AES-256-GCM.
// The Keystore adapter owns the non-exportable key, not this codec.
// Only ciphertext (never UI secrets) may be written to disk.
final class RootSavedCredentialRecord {
    private RootSavedCredentialRecord(){}
    private static final byte[] MAGIC="WBDCRD38".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] AAD="WBD-ANDROID-ROOT-SAVED-CREDENTIALS-V1".getBytes(StandardCharsets.US_ASCII);
    private static final int IV=12;
    static final int MAX_FILE=4096;

    static final class Secrets {
        final String password;
        final String routeKey;
        Secrets(String password,String routeKey){
            this.password=password;
            this.routeKey=routeKey;
        }
    }
    static void validate(String password,String routeKey){
        if(password==null||routeKey==null||
           password.isEmpty()||password.length()>512||
           password.indexOf('\0')>=0||password.indexOf('\n')>=0||
           password.indexOf('\r')>=0)
            throw new IllegalArgumentException("invalid saved password");
        // Main's v2 8..32 ASCII short key or exact legacy 64 hex. Never
        // transform the human short key before encrypting it for UI recall.
        if(routeKey.matches("[0-9a-fA-F]{64}"))return;
        if(routeKey.length()<8||routeKey.length()>32||
           !routeKey.matches("[A-Za-z0-9]{8,32}"))
            throw new IllegalArgumentException("invalid saved short route key");
    }
    static byte[] encrypt(SecretKey key,String password,String routeKey)
        throws Exception{
        validate(password,routeKey);
        byte[] pw=password.getBytes(StandardCharsets.UTF_8);
        byte[] rk=routeKey.getBytes(StandardCharsets.US_ASCII);
        byte[] clear=null;
        try{
            ByteArrayOutputStream raw=new ByteArrayOutputStream();
            DataOutputStream out=new DataOutputStream(raw);
            out.writeShort(pw.length);out.write(pw);
            out.writeShort(rk.length);out.write(rk);out.flush();
            clear=raw.toByteArray();
            byte[] iv=new byte[IV];
            new SecureRandom().nextBytes(iv);
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE,key,new GCMParameterSpec(128,iv));
            cipher.updateAAD(AAD);
            byte[] sealed=cipher.doFinal(clear);
            byte[] result=new byte[MAGIC.length+IV+sealed.length];
            System.arraycopy(MAGIC,0,result,0,MAGIC.length);
            System.arraycopy(iv,0,result,MAGIC.length,IV);
            System.arraycopy(sealed,0,result,MAGIC.length+IV,sealed.length);
            if(result.length>MAX_FILE)throw new GeneralSecurityException("encrypted record oversized");
            return result;
        }finally{
            Arrays.fill(pw,(byte)0);
            Arrays.fill(rk,(byte)0);
            if(clear!=null)Arrays.fill(clear,(byte)0);
        }
    }
    static Secrets decrypt(SecretKey key,byte[] record)throws Exception{
        if(record==null||record.length<MAGIC.length+IV+16+5||
           record.length>MAX_FILE)
            throw new GeneralSecurityException("saved record size invalid");
        for(int i=0;i<MAGIC.length;i++)
            if(record[i]!=MAGIC[i])throw new GeneralSecurityException("saved record version invalid");
        byte[] iv=Arrays.copyOfRange(record,MAGIC.length,MAGIC.length+IV);
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE,key,new GCMParameterSpec(128,iv));
        cipher.updateAAD(AAD);
        byte[] clear=cipher.doFinal(record,MAGIC.length+IV,record.length-MAGIC.length-IV);
        try{
            DataInputStream input=new DataInputStream(new ByteArrayInputStream(clear));
            int pwLen=input.readUnsignedShort();
            if(pwLen<1||pwLen>2048||pwLen>input.available())
                throw new GeneralSecurityException("invalid password length");
            byte[] pw=new byte[pwLen];input.readFully(pw);
            int rkLen=input.readUnsignedShort();
            if(rkLen<8||rkLen>64||rkLen!=input.available())
                throw new GeneralSecurityException("invalid route key length");
            byte[] rk=new byte[rkLen];input.readFully(rk);
            try{
                Secrets result=new Secrets(new String(pw,StandardCharsets.UTF_8),
                    new String(rk,StandardCharsets.US_ASCII));
                validate(result.password,result.routeKey);
                return result;
            }finally{Arrays.fill(pw,(byte)0);Arrays.fill(rk,(byte)0);}
        }finally{Arrays.fill(clear,(byte)0);}
    }
}
