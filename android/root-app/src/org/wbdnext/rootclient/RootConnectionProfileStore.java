package org.wbdnext.rootclient;

import android.content.Context;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;

/** Four named local UI profiles. Native credentials remain in existing store. */
final class RootConnectionProfileStore {
    private RootConnectionProfileStore(){}
    private static File file(Context context,int slot){
        if(slot<1||slot>RootConnectionProfile.SLOTS)
            throw new IllegalArgumentException("profile slot 1..4");
        return new File(context.getNoBackupFilesDir(),"wbd-profile-"+slot+".bin");
    }
    static RootConnectionProfile load(Context context,int slot)throws IOException {
        File profile=file(context,slot);
        if(!profile.isFile())return null;
        if(profile.length()>RootConnectionProfile.MAX_FILE_BYTES)return null;
        try(FileInputStream in=new FileInputStream(profile)){
            return RootConnectionProfile.read(in);
        }
    }
    static void save(Context context,int slot,RootConnectionProfile value)
        throws IOException {
        File dest=file(context,slot),temp=new File(dest.getPath()+".tmp");
        try(FileOutputStream out=new FileOutputStream(temp,false)){
            value.write(out);
            out.getFD().sync();
        }
        if(temp.length()>RootConnectionProfile.MAX_FILE_BYTES||
           !temp.renameTo(dest)){
            temp.delete();
            throw new IOException("could not save connection profile");
        }
    }
    static void delete(Context context,int slot)throws IOException {
        File target=file(context,slot);
        if(target.exists()&&!target.delete())
            throw new IOException("could not delete connection profile");
    }
}
