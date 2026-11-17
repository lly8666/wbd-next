package org.wbdnext.rootclient;

import android.content.Context;
import android.os.Build;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;

// Native Go/Rust assets are source-locked to the SAME verified ARM64 CI.
// APK never substitutes its own crypto/TLS, CGo ABI or synthetic traffic.
final class NativePayload {
    final File client;
    final File engine;
    final String source;
    private NativePayload(File c,File e,String s){
        client=c;engine=e;source=s;
    }
    private static byte[] load(Context ctx,String path,int maximum)throws Exception{
        try(InputStream in=ctx.getAssets().open(path);
            ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] buf=new byte[8192];
            int n;
            while((n=in.read(buf))!=-1){
                if(out.size()+n>maximum)throw new IllegalStateException(
                    "source-locked native asset exceeds bound");
                out.write(buf,0,n);
            }
            return out.toByteArray();
        }
    }
    private static String hex(byte[] data){
        final char[] digits="0123456789abcdef".toCharArray();
        char[] out=new char[data.length*2];
        for(int i=0;i<data.length;i++){
            int v=data[i]&255;
            out[i*2]=digits[v>>>4];
            out[i*2+1]=digits[v&15];
        }
        return new String(out);
    }
    private static File checkedCopy(Context ctx,String asset,File dir,
                                     String fileName,String expected)throws Exception{
        // Streaming one-pass SHA256 + fd sync: do NOT hold an additional
        // 11MiB original-Go ELF byte[] on the Android app Java heap.
        MessageDigest hash=MessageDigest.getInstance("SHA-256");
        File target=new File(dir,fileName);
        int total=0;
        try(InputStream in=ctx.getAssets().open("native-arm64/"+asset);
            FileOutputStream out=new FileOutputStream(target,false)){
            byte[] buffer=new byte[8192];
            int n;
            while((n=in.read(buffer))!=-1){
                total+=n;
                if(total>40*1024*1024){
                    throw new SecurityException("native source asset exceeds bound");
                }
                hash.update(buffer,0,n);
                out.write(buffer,0,n);
            }
            out.getFD().sync();
        }catch(Exception failure){
            target.delete();
            throw failure;
        }
        if(total==0||!hex(hash.digest()).equals(expected)){
            target.delete();
            throw new SecurityException("native SHA256 does not match signed APK manifest");
        }
        target.setReadable(false,false);
        if(!target.setReadable(true,true)){
            throw new SecurityException("private native staging mode rejected");
        }
        return target;
    }
    static NativePayload stage(Context ctx)throws Exception{
        boolean arm64=false;
        for(String abi:Build.SUPPORTED_64_BIT_ABIS){
            if("arm64-v8a".equals(abi)){arm64=true;break;}
        }
        if(!arm64)throw new IllegalStateException(
            "only original WBD Android ARM64-v8a product accepted");
        JSONObject m=new JSONObject(new String(load(ctx,
            "native-arm64/manifest.json",65536),java.nio.charset.StandardCharsets.UTF_8));
        if(m.getJSONArray("android_abis").length()!=1||
           !"arm64".equals(m.getJSONArray("android_abis").getString(0))||
           !"android".equals(m.getString("go_os"))){
            throw new SecurityException("wrong ABI or untrusted native manifest");
        }
        String source=m.getString("source");
        if(!source.matches("[0-9a-f]{40}")||
           !source.equals(new String(load(ctx,"native-arm64/SOURCE",128),
               java.nio.charset.StandardCharsets.US_ASCII).trim())){
            throw new SecurityException("mixed Go/Rust source SHA");
        }
        JSONObject binary=m.getJSONObject("artifacts");
        String goSha=binary.getJSONObject("wbd-v4-client-arm64").getString("sha256");
        String rustSha=binary.getJSONObject("libwbd_engine-arm64.so").getString("sha256");
        File root=new File(ctx.getNoBackupFilesDir(),"wbd-arm64-verified");
        if(!root.isDirectory()&&!root.mkdir()){
            throw new IllegalStateException("private native staging inaccessible");
        }
        File go=checkedCopy(ctx,"wbd-v4-client-arm64",root,
            "wbd-v4-client-arm64",goSha);
        File rust=checkedCopy(ctx,"libwbd_engine-arm64.so",root,
            "libwbd_engine.so",rustSha);
        return new NativePayload(go,rust,source);
    }
}
