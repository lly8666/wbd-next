package org.wbdnext.rootclient;

import android.content.Context;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;

/** App-only, no-backup connection UI preset. Secret storage stays in Keystore. */
final class RootConnectionSettingsStore {
    private static final String NAME="wbd-last-connection.properties";
    private RootConnectionSettingsStore(){}
    static RootConnectionSettings load(Context ctx)throws IOException{
        File file=new File(ctx.getNoBackupFilesDir(),NAME);
        if(!file.isFile())return null;
        if(file.length()>8192)return null;
        try(FileInputStream in=new FileInputStream(file)){
            return RootConnectionSettings.read(in);
        }
    }
    static void save(Context ctx,RootConnectionSettings value)throws IOException{
        File dir=ctx.getNoBackupFilesDir();
        File target=new File(dir,NAME);
        File tmp=new File(dir,NAME+".tmp");
        try(FileOutputStream out=new FileOutputStream(tmp,false)){
            value.write(out);
            out.getFD().sync();
        }
        if(!tmp.renameTo(target)){
            tmp.delete();
            throw new IOException("could not save local connection settings");
        }
    }
}
