package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;

/**
 * Cold, user-chosen SAF import of the exact production non-secret B22/B25
 * connection preset. The same RootConnectionSettings.write() exports it.
 * Password, RouteKey, CA and physical Network are not part of that model.
 */
final class RootConnectionSettingsTransfer {
    static final int MAX_BYTES=8192;
    private RootConnectionSettingsTransfer(){}

    static RootConnectionSettings read(InputStream source)throws IOException{
        if(source==null)return null;
        ByteArrayOutputStream b=new ByteArrayOutputStream();
        byte[] chunk=new byte[1024];
        int n;
        while((n=source.read(chunk))!=-1){
            if(n==0)continue;
            if(b.size()+n>MAX_BYTES)return null;
            b.write(chunk,0,n);
        }
        if(b.size()==0)return null;
        return RootConnectionSettings.read(
            new ByteArrayInputStream(b.toByteArray()));
    }
}
