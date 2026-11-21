package org.wbdnext.rootclient;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Locale;
import javax.crypto.Mac;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

// Main's exact H2208 route-key v2: purely OFFLINE enrollment. Not TLS,
// admission, a second crypto protocol or a per-packet handler.
final class RootRouteKeyV2 {
    private RootRouteKeyV2(){}
    private static final byte[] SALT=
        "WBD-V4-ROUTE-KEY-PBKDF2-SHA256-v2\u0000".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] CHECK_DOMAIN=
        "WBD-V4-ROUTE-KEY-CACHE-v2\u0000".getBytes(StandardCharsets.US_ASCII);

    static boolean legacyHex(String s){
        return s!=null&&s.matches("[0-9a-fA-F]{64}");
    }
    static String canonicalLegacyHex(String s){
        if(!legacyHex(s))
            throw new IllegalArgumentException("legacy key must be exactly 64 hexadecimal characters");
        return s.toLowerCase(Locale.ROOT);
    }
    static void validateShort(String s){
        if(s==null||s.length()<8||s.length()>32)
            throw new IllegalArgumentException("short v2 key needs 8..32 ASCII letters/digits");
        for(int i=0;i<s.length();i++){
            char c=s.charAt(i);
            if(!((c>='0'&&c<='9')||(c>='A'&&c<='Z')||(c>='a'&&c<='z')))
                throw new IllegalArgumentException("short v2 key needs 8..32 ASCII letters/digits");
        }
    }
    static byte[] derive(String s)throws GeneralSecurityException{
        validateShort(s);
        char[] chars=s.toCharArray();
        PBEKeySpec spec=new PBEKeySpec(chars,SALT,4096,256);
        try{
            byte[] result=SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
                .generateSecret(spec).getEncoded();
            if(result.length!=32)throw new GeneralSecurityException("short v2 KDF length mismatch");
            return result;
        }finally{
            spec.clearPassword();
            Arrays.fill(chars,'\0');
        }
    }
    static String hex(byte[] bytes){
        final char[] digits="0123456789abcdef".toCharArray();
        char[] out=new char[bytes.length*2];
        for(int i=0;i<bytes.length;i++){
            int n=bytes[i]&255;
            out[i*2]=digits[n>>>4];out[i*2+1]=digits[n&15];
        }
        return new String(out);
    }
    private static byte[] fromHex32(String value){
        if(value==null||!value.matches("[0-9a-f]{64}"))
            throw new IllegalArgumentException("invalid private v2 cache encoding");
        byte[] bytes=new byte[32];
        for(int i=0;i<32;i++){
            int a=Character.digit(value.charAt(i*2),16);
            int b=Character.digit(value.charAt(i*2+1),16);
            bytes[i]=(byte)(a*16+b);
        }
        return bytes;
    }
    private static byte[] proof(byte[] key,String shortKey)throws GeneralSecurityException{
        Mac mac=Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key,"HmacSHA256"));
        mac.update(CHECK_DOMAIN);
        return mac.doFinal(shortKey.getBytes(StandardCharsets.US_ASCII));
    }
    static String record(byte[] key,String input)throws GeneralSecurityException{
        validateShort(input);
        if(key==null||key.length!=32)throw new IllegalArgumentException("invalid v2 derived key");
        return "v2\n"+hex(key)+"\n"+hex(proof(key,input))+"\n";
    }
    // Reuse cached derived key across app restarts; never persist the
    // human short key. Corrupt/unknown-version cache fails closed.
    // A changed valid short key returns null, causing explicit rotation.
    static byte[] verifiedCache(String record,String input)throws GeneralSecurityException{
        validateShort(input);
        if(record==null||record.length()>136)
            throw new IllegalArgumentException("invalid private v2 cache record");
        String[] fields=record.split("\n",-1);
        if(fields.length!=4||!"v2".equals(fields[0])||!fields[3].isEmpty())
            throw new IllegalArgumentException("invalid private v2 cache version");
        byte[] key=fromHex32(fields[1]);
        byte[] tag=fromHex32(fields[2]);
        try{
            if(MessageDigest.isEqual(tag,proof(key,input)))return key;
            Arrays.fill(key,(byte)0);
            return null;
        }finally{Arrays.fill(tag,(byte)0);}
    }
}
