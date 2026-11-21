package org.wbdnext.rootclient;

import android.content.Context;
import android.os.Build;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;

// Same original Go/Rust Bionic source: arm64 release or x86_64 CI-only APK.
// APK never substitutes its own crypto/TLS, CGo ABI or synthetic traffic.
final class NativePayload {
    final File client;
    final File engine;
    final File cnGeosite;
    final String source;
    final String executableName;
    private static final String PINNED_CN_SHA256=
        "45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6";
    private static final String PINNED_CN_SOURCE=
        "41504eae2a11f305fe88cfc605cf6c105a80bf5a";
    private NativePayload(File c,File e,File g,String s,String binary){
        client=c;engine=e;cnGeosite=g;source=s;executableName=binary;
    }
    private static boolean hasAsset(Context ctx,String path){
        try(InputStream in=ctx.getAssets().open(path)){
            return in.read()!=-1;
        }catch(java.io.IOException absent){return false;}
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
    private static File checkedCopy(Context ctx,String assetPrefix,String asset,File dir,
                                     String fileName,String expected,int maxBytes)throws Exception{
        // Streaming one-pass SHA256 + fd sync: do NOT hold an additional
        // 11MiB original-Go ELF byte[] on the Android app Java heap.
        MessageDigest hash=MessageDigest.getInstance("SHA-256");
        File target=new File(dir,fileName);
        int total=0;
        try(InputStream in=ctx.getAssets().open(assetPrefix+asset);
            FileOutputStream out=new FileOutputStream(target,false)){
            byte[] buffer=new byte[8192];
            int n;
            while((n=in.read(buffer))!=-1){
                total+=n;
                if(total>maxBytes){
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
        // Enforce mode 0600 explicitly; Root Go opens the same regular fd
        // using O_NOFOLLOW and verifies its complete pinned digest.
        target.setReadable(false,false);
        target.setWritable(false,false);
        target.setExecutable(false,false);
        if(!target.setReadable(true,true)||!target.setWritable(true,true)){
            target.delete();
            throw new SecurityException("private signed asset staging mode rejected");
        }
        return target;
    }
    // Isolated, non-product ARM64 debug capability helper. The signed
    // archive carries a separate immutable SHA256 for this test-only binary.
    // It never handles a packet or substitutes original Go/Rust/AEAD/TLS.
    static File stageDeviceSelfTest(Context ctx)throws Exception{
        String hash=new String(load(ctx,
            "native-arm64/device-selftest-sha256.txt",128),
            java.nio.charset.StandardCharsets.US_ASCII).trim();
        if(!hash.matches("[0-9a-f]{64}"))
            throw new SecurityException("invalid signed device diagnostic hash");
        File dir=new File(ctx.getNoBackupFilesDir(),"wbd-arm64-verified");
        if(!dir.isDirectory()&&!dir.mkdir())
            throw new IllegalStateException("device diagnostic staging inaccessible");
        return checkedCopy(ctx,"native-arm64/","device-selftest-arm64",dir,
            "device-selftest-arm64",hash,1024*1024);
    }

    static NativePayload stage(Context ctx)throws Exception{
        // Signed APK may contain one and ONLY one supported 64-bit Bionic ABI.
        // Release bundles ARM64; CI-only test bundles x86_64. The same Java
        // controller/Go/Rust source is used by both, never a native fallback.
        boolean armAssets=hasAsset(ctx,"native-arm64/manifest.json");
        boolean x86Assets=hasAsset(ctx,"native-amd64/manifest.json");
        if(armAssets==x86Assets)throw new SecurityException(
            "exactly one source-locked Android native ABI required");
        String goArch=armAssets?"arm64":"amd64";
        String abi=armAssets?"arm64-v8a":"x86_64";
        String manifestAbi=armAssets?"arm64":"x86_64";
        String prefix="native-"+goArch+"/";
        boolean installedAbi=false;
        for(String installed:Build.SUPPORTED_64_BIT_ABIS)
            if(abi.equals(installed))installedAbi=true;
        if(!installedAbi)throw new SecurityException("signed native ABI not supported by OS");
        JSONObject m=new JSONObject(new String(load(ctx,
            prefix+"manifest.json",65536),java.nio.charset.StandardCharsets.UTF_8));
        if(m.getJSONArray("android_abis").length()!=1||
           !manifestAbi.equals(m.getJSONArray("android_abis").getString(0))||
           !"android".equals(m.getString("go_os"))||
           (!armAssets&&m.optBoolean("release",true))){
            throw new SecurityException("CI/release ABI or manifest mismatch");
        }
        String source=m.getString("source");
        if(!source.matches("[0-9a-f]{40}")||
           !source.equals(new String(load(ctx,prefix+"SOURCE",128),
               java.nio.charset.StandardCharsets.US_ASCII).trim())){
            throw new SecurityException("mixed Go/Rust source SHA");
        }
        String executable="wbd-v4-client-"+goArch;
        String rustFile="libwbd_engine-"+goArch+".so";
        JSONObject binary=m.getJSONObject("artifacts");
        String goSha=binary.getJSONObject(executable).getString("sha256");
        String rustSha=binary.getJSONObject(rustFile).getString("sha256");
        File root=new File(ctx.getNoBackupFilesDir(),"wbd-"+goArch+"-verified");
        if(!root.isDirectory()&&!root.mkdir()){
            throw new IllegalStateException("private native staging inaccessible");
        }
        // Unchanged pinned original geosite provenance; no system DNS takeover.
        JSONObject provenance=new JSONObject(new String(load(ctx,
            prefix+"cn-geosite-provenance.json",65536),
            java.nio.charset.StandardCharsets.UTF_8));
        if(!PINNED_CN_SOURCE.equals(provenance.getString("source_commit"))||
           !PINNED_CN_SHA256.equals(provenance.getString("text_sha256"))||
           provenance.getInt("output_distinct_rules")!=8503||
           provenance.getJSONObject("kinds").getInt("domain")!=8431||
           provenance.getJSONObject("kinds").getInt("full")!=69||
           provenance.getJSONObject("kinds").getInt("regexp")!=3){
            throw new SecurityException("signed CN8503 source provenance mismatch");
        }
        String license=new String(load(ctx,
            prefix+"wbd-cn-geosite-license.txt",65536),
            java.nio.charset.StandardCharsets.UTF_8);
        if(!license.contains("MIT License")||!license.contains("V2Ray")){
            throw new SecurityException("missing authentic signed CN geosite license");
        }
        File go=checkedCopy(ctx,prefix,executable,root,
            executable,goSha,40*1024*1024);
        File rust=checkedCopy(ctx,prefix,rustFile,root,
            "libwbd_engine.so",rustSha,40*1024*1024);
        File cn=checkedCopy(ctx,prefix,"wbd-cn-geosite.txt",root,
            "wbd-cn-geosite.txt",PINNED_CN_SHA256,6000000);
        return new NativePayload(go,rust,cn,source,executable);
    }
}
