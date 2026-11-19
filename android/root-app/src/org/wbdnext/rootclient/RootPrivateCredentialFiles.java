package org.wbdnext.rootclient;

import android.content.Context;
import android.os.Process;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructStat;
import java.io.File;
import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * Android Context.MODE_PRIVATE is NOT an OS guarantee of mode 0600:
 * AOSP ContextImpl.setFilePermissionsFromMode includes S_IRGRP|S_IWGRP.
 * Original Go's readPrivateArgFile MUST reject those bits.
 *
 * Author the exact Android credential files with kernel O_NOFOLLOW,
 * force fd mode 0600, and check the SAME fd owner/type/mode/bytes.
 * This is cold-only, not a second Go/TLS/AEAD or packet handler.
 */
final class RootPrivateCredentialFiles {
    private RootPrivateCredentialFiles(){}
    static final String PASSWORD=RootPrivateCredentialContract.PASSWORD;
    static final String ROUTE=RootPrivateCredentialContract.ROUTE;
    static final String CA=RootPrivateCredentialContract.CA;

    private static void verifyStat(StructStat st,String name,int owner,long bytes){
        if(st.st_size!=bytes||
           !RootPrivateCredentialContract.ownerOnlyRegular(
               name,st.st_mode,st.st_uid,st.st_nlink,st.st_size,owner))
            throw new SecurityException("original Go private credential not owner-only regular 0600");
    }
    static void write(Context ctx,String name,String content)throws Exception{
        int limit=RootPrivateCredentialContract.maxBytes(name);
        if(ctx==null||content==null||content.indexOf('\0')>=0)
            throw new IllegalArgumentException("invalid private credential input");
        byte[] payload=content.getBytes(StandardCharsets.UTF_8);
        try{
            if(payload.length<1||payload.length>limit||
               (ROUTE.equals(name)&&(payload.length!=65||
                 !content.matches("[0-9a-f]{64}\\n"))))
                throw new IllegalArgumentException("invalid bounded private credential");
            File path=new File(ctx.getFilesDir(),name);
            // Do not call openFileOutput(MODE_PRIVATE): Android itself can
            // create 0660, which original Go correctly rejects.
            FileDescriptor fd=Os.open(path.getAbsolutePath(),
                OsConstants.O_WRONLY|OsConstants.O_CREAT|OsConstants.O_TRUNC|
                OsConstants.O_CLOEXEC|OsConstants.O_NOFOLLOW,
                RootPrivateCredentialContract.OWNER_ONLY);
            try(FileOutputStream out=new FileOutputStream(fd)){
                Os.fchmod(fd,RootPrivateCredentialContract.OWNER_ONLY);
                out.write(payload);
                out.getFD().sync();
                verifyStat(Os.fstat(fd),name,Process.myUid(),payload.length);
            }
        }finally{Arrays.fill(payload,(byte)0);}
    }
    private static void verifyFile(File dir,String name,int uid)throws Exception{
        RootPrivateCredentialContract.maxBytes(name);
        StructStat st=Os.lstat(new File(dir,name).getAbsolutePath());
        if(!RootPrivateCredentialContract.ownerOnlyRegular(
               name,st.st_mode,st.st_uid,st.st_nlink,st.st_size,uid))
            throw new SecurityException("original Go private credentials failed 0600 readback");
    }
    static void verifyAtStart(Context ctx,boolean hasCA)throws Exception{
        if(ctx==null)throw new IllegalArgumentException("missing private app context");
        File dir=ctx.getFilesDir();
        int uid=Process.myUid();
        verifyFile(dir,PASSWORD,uid);
        verifyFile(dir,ROUTE,uid);
        if(hasCA)verifyFile(dir,CA,uid);
    }
}
