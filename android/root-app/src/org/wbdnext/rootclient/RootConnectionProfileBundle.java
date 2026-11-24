package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/** One SAF file for all four existing NONSECRET connection slots.
 * It wraps their exact production codec; never holds credentials or Root state.
 */
final class RootConnectionProfileBundle {
    private static final int MAGIC=0x57425042; // local WBPB v1
    static final int MAX_BYTES=RootConnectionProfile.SLOTS*
        (RootConnectionProfile.MAX_FILE_BYTES+4)+16;
    private RootConnectionProfileBundle(){}

    static void write(OutputStream output,RootConnectionProfile[] profiles)
        throws IOException {
        if(profiles==null||profiles.length!=RootConnectionProfile.SLOTS)
            throw new IllegalArgumentException("four profile slots required");
        DataOutputStream stream=new DataOutputStream(output);
        stream.writeInt(MAGIC);
        stream.writeInt(RootConnectionProfile.SLOTS);
        for(RootConnectionProfile profile:profiles){
            if(profile==null){
                stream.writeInt(0);
                continue;
            }
            ByteArrayOutputStream payload=new ByteArrayOutputStream();
            profile.write(payload); // original B50 profile+settings codec
            byte[] content=payload.toByteArray();
            if(content.length>RootConnectionProfile.MAX_FILE_BYTES)
                throw new IOException("profile exceeds its existing limit");
            stream.writeInt(content.length);
            stream.write(content);
        }
        stream.flush();
    }
    static RootConnectionProfile[] read(InputStream input)throws IOException {
        if(input==null)return null;
        ByteArrayOutputStream raw=new ByteArrayOutputStream();
        byte[] chunk=new byte[4096];
        for(int n;(n=input.read(chunk))!=-1;){
            if(n==0)continue;
            if(raw.size()+n>MAX_BYTES)return null;
            raw.write(chunk,0,n);
        }
        byte[] bytes=raw.toByteArray();
        if(bytes.length<8+4*RootConnectionProfile.SLOTS)return null;
        DataInputStream stream=new DataInputStream(new ByteArrayInputStream(bytes));
        if(stream.readInt()!=MAGIC||stream.readInt()!=RootConnectionProfile.SLOTS)
            return null;
        RootConnectionProfile[] result=
            new RootConnectionProfile[RootConnectionProfile.SLOTS];
        for(int i=0;i<result.length;i++){
            int length=stream.readInt();
            if(length<0||length>RootConnectionProfile.MAX_FILE_BYTES||
               length>stream.available())return null;
            if(length==0)continue;
            byte[] entry=new byte[length];
            stream.readFully(entry);
            try{
                RootConnectionProfile profile=RootConnectionProfile.read(
                    new ByteArrayInputStream(entry));
                if(profile==null)return null;
                result[i]=profile;
            }catch(IllegalArgumentException malformed){
                return null;
            }
        }
        return stream.available()==0?result:null;
    }
}
