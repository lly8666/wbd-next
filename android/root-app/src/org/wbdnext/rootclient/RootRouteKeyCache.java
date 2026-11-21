package org.wbdnext.rootclient;

import android.content.Context;
import android.system.Os;
import android.util.AtomicFile;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;

// Root Lite is the REAL Root APK, not the separate historical VpnService.
// Main's short-key v2 becomes the ORIGINAL Go's 32-byte --route-key-hex-file.
// The cache is private and no-backup; never logged or placed in Intent/argv.
final class RootRouteKeyCache {
    private RootRouteKeyCache(){}
    static String resolve(Context context,String serverName,String supplied)throws Exception{
        if(RootRouteKeyV2.legacyHex(supplied))
            return RootRouteKeyV2.canonicalLegacyHex(supplied);
        RootRouteKeyV2.validateShort(supplied);
        if(context==null||serverName==null||serverName.isEmpty())
            throw new IllegalArgumentException("missing TLS identity for private short-key cache");
        byte[] id=MessageDigest.getInstance("SHA-256").digest(
            ("client\u0000"+serverName).getBytes(StandardCharsets.UTF_8));
        String name="route-key-v2-"+RootRouteKeyV2.hex(Arrays.copyOf(id,12))+".txt";
        Arrays.fill(id,(byte)0);
        File destination=new File(context.getNoBackupFilesDir(),name);
        if(java.nio.file.Files.isSymbolicLink(destination.toPath()))
            throw new SecurityException("invalid private route-key cache");
        AtomicFile file=new AtomicFile(destination);
        byte[] derived=null;
        try{
            boolean found=true;
            byte[] raw=null;
            try{raw=file.readFully();}
            catch(FileNotFoundException missing){found=false;}
            if(found){
                if(raw==null||raw.length>136)
                    throw new IllegalArgumentException("invalid private v2 cache size");
                try{
                    String text=new String(raw,StandardCharsets.US_ASCII);
                    derived=RootRouteKeyV2.verifiedCache(text,supplied);
                }finally{Arrays.fill(raw,(byte)0);}
                if(derived!=null)return RootRouteKeyV2.hex(derived);
            }
            // First enrollment or explicitly changed short key: one local
            // PBKDF2 operation. Server must use exactly the same v2 key.
            derived=RootRouteKeyV2.derive(supplied);
            byte[] serialized=RootRouteKeyV2.record(derived,supplied)
                .getBytes(StandardCharsets.US_ASCII);
            FileOutputStream out=null;
            try{
                out=file.startWrite();
                out.write(serialized);
                out.getFD().sync();
                file.finishWrite(out);
                out=null;
                // Explicit owner-only permissions; cache never goes into
                // Android Backup and cannot be world-readable.
                Os.chmod(destination.getAbsolutePath(),0600);
            }catch(Exception failure){
                if(out!=null)file.failWrite(out);
                throw failure;
            }finally{Arrays.fill(serialized,(byte)0);}
            return RootRouteKeyV2.hex(derived);
        }finally{
            if(derived!=null)Arrays.fill(derived,(byte)0);
        }
    }
}
