package org.wbdnext.rootclient;

import android.content.Context;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Existing optional Go TLS CA text, scoped to each named cold connection.
 * Public certificate material only; this does not alter TLS verification.
 */
final class RootConnectionProfileCAStore {
    private RootConnectionProfileCAStore(){}
    private static final String ACTIVE="wbd-current-ui-ca.pem";
    private static File slotFile(Context ctx,int slot){
        if(slot<1||slot>RootConnectionProfile.SLOTS)
            throw new IllegalArgumentException("profile slot 1..4");
        return new File(ctx.getNoBackupFilesDir(),"wbd-profile-"+slot+"-ca.pem");
    }
    private static File current(Context ctx){
        return new File(ctx.getNoBackupFilesDir(),ACTIVE);
    }
    private static int limit(){
        return RootPrivateCredentialContract.maxBytes(RootPrivateCredentialFiles.CA);
    }
    private static String read(File target)throws IOException{
        if(!target.isFile())return "";
        if(target.length()>limit())throw new IOException("CA exceeds existing Go bound");
        try(FileInputStream in=new FileInputStream(target)){
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            byte[] chunk=new byte[4096];
            for(int n;(n=in.read(chunk))!=-1;){
                if(n==0)continue;
                if(out.size()+n>limit())throw new IOException("CA too large");
                out.write(chunk,0,n);
            }
            return new String(out.toByteArray(),StandardCharsets.UTF_8);
        }
    }
    private static void write(File target,String pem)throws IOException{
        if(pem==null)throw new IllegalArgumentException("missing CA text");
        byte[] bytes=pem.getBytes(StandardCharsets.UTF_8);
        if(bytes.length>limit())throw new IOException("CA too large");
        File temp=new File(target.getPath()+".tmp");
        try(FileOutputStream out=new FileOutputStream(temp,false)){
            out.write(bytes);
            out.getFD().sync();
        }
        if(!temp.renameTo(target)){
            temp.delete();
            throw new IOException("could not save UI CA");
        }
    }
    static void saveSlot(Context ctx,int slot,String pem)throws IOException{
        File target=slotFile(ctx,slot);
        String value=pem==null?"":pem.trim();
        if(value.isEmpty()){
            if(target.exists()&&!target.delete())
                throw new IOException("could not clear profile CA");
        }else write(target,value+"\n");
    }
    static String loadSlot(Context ctx,int slot)throws IOException{
        return read(slotFile(ctx,slot)).trim();
    }
    static void clearSlot(Context ctx,int slot)throws IOException{
        saveSlot(ctx,slot,"");
    }
    // Even an EMPTY file means "this profile intentionally has no CA".
    // Absence alone means a pre-B54 installation should use old A32 recall.
    static void saveCurrent(Context ctx,String pem)throws IOException{
        write(current(ctx),pem==null?"":pem.trim());
    }
    static String loadCurrent(Context ctx)throws IOException{
        File target=current(ctx);
        return target.isFile()?read(target).trim():null;
    }
}
