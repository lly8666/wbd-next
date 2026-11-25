package org.wbdnext.rootclient;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/** Portable server backup. The old settings-only format remains readable. */
final class RootConnectionProfileBundle {
    private static final int MAGIC=0x57425042; // local WBPB v1
    static final int MAX_BYTES=RootConnectionProfile.SLOTS*
        (RootConnectionProfile.MAX_FILE_BYTES+4)+16;
    private static final int FULL_MAGIC=0x57425043;
    private static final int MAX_CA=1<<20;
    private static final int FULL_MAX=RootConnectionProfile.SLOTS*(RootConnectionProfile.MAX_FILE_BYTES+MAX_CA+4096)+32;
    static final class Entry {
        final RootConnectionProfile profile;
        final String password,routeKey,ca;
        Entry(RootConnectionProfile profile,String password,String routeKey,String ca){
            if(profile==null||password==null||routeKey==null||ca==null)
                throw new IllegalArgumentException("missing server data");
            if(!password.isEmpty()||!routeKey.isEmpty())RootSavedCredentialRecord.validate(password,routeKey);
            if(ca.getBytes(java.nio.charset.StandardCharsets.UTF_8).length>MAX_CA)
                throw new IllegalArgumentException("CA too large");
            this.profile=profile;this.password=password;this.routeKey=routeKey;this.ca=ca;
        }
    }
    private RootConnectionProfileBundle(){}
    static void writeComplete(OutputStream output,Entry[] entries)throws IOException{
        if(entries==null||entries.length!=RootConnectionProfile.SLOTS)
            throw new IllegalArgumentException("ten server slots required");
        DataOutputStream out=new DataOutputStream(output);
        out.writeInt(FULL_MAGIC);out.writeInt(entries.length);
        for(Entry entry:entries){
            out.writeBoolean(entry!=null);
            if(entry==null)continue;
            ByteArrayOutputStream profile=new ByteArrayOutputStream();
            entry.profile.write(profile);
            out.writeInt(profile.size());profile.writeTo(out);
            out.writeUTF(entry.password);out.writeUTF(entry.routeKey);
            byte[] ca=entry.ca.getBytes(java.nio.charset.StandardCharsets.UTF_8);
            out.writeInt(ca.length);out.write(ca);
        }
        out.flush();
    }
    static Entry[] readComplete(InputStream input)throws IOException{
        if(input==null)return null;
        ByteArrayOutputStream raw=new ByteArrayOutputStream();
        byte[] chunk=new byte[8192];
        for(int n;(n=input.read(chunk))!=-1;){
            if(raw.size()+n>FULL_MAX)return null;raw.write(chunk,0,n);
        }
        byte[] bytes=raw.toByteArray();
        if(bytes.length<8)return null;
        DataInputStream in=new DataInputStream(new ByteArrayInputStream(bytes));
        int magic=in.readInt();
        if(magic==MAGIC){
            RootConnectionProfile[] old=read(new ByteArrayInputStream(bytes));
            if(old==null)return null;
            Entry[] result=new Entry[old.length];
            for(int i=0;i<old.length;i++)if(old[i]!=null)result[i]=new Entry(old[i],"","","");
            return result;
        }
        if(magic!=FULL_MAGIC||in.readInt()!=RootConnectionProfile.SLOTS)return null;
        Entry[] entries=new Entry[RootConnectionProfile.SLOTS];
        try{
            for(int i=0;i<entries.length;i++){
                if(!in.readBoolean())continue;
                int len=in.readInt();
                if(len<1||len>RootConnectionProfile.MAX_FILE_BYTES||len>in.available())return null;
                byte[] profile=new byte[len];in.readFully(profile);
                RootConnectionProfile parsed=RootConnectionProfile.read(new ByteArrayInputStream(profile));
                if(parsed==null)return null;
                String pw=in.readUTF(),key=in.readUTF();
                int size=in.readInt();if(size<0||size>MAX_CA||size>in.available())return null;
                byte[] ca=new byte[size];in.readFully(ca);
                entries[i]=new Entry(parsed,pw,key,new String(ca,java.nio.charset.StandardCharsets.UTF_8));
            }
        }catch(IllegalArgumentException|java.io.EOFException e){return null;}
        return in.available()==0?entries:null;
    }

    static void write(OutputStream output,RootConnectionProfile[] profiles)
        throws IOException {
        if(profiles==null||profiles.length!=RootConnectionProfile.SLOTS)
            throw new IllegalArgumentException("ten profile slots required");
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
        if(bytes.length<8+4*4)return null;
        DataInputStream stream=new DataInputStream(new ByteArrayInputStream(bytes));
        if(stream.readInt()!=MAGIC)return null;
        int slots=stream.readInt();
        // Original four-slot v1 backups restore only slots 1–4.
        // Never clear newly added slots 5–10 on legacy import.
        if((slots!=4&&slots!=RootConnectionProfile.SLOTS)||bytes.length<8+4*slots)return null;
        RootConnectionProfile[] result=new RootConnectionProfile[slots];
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
