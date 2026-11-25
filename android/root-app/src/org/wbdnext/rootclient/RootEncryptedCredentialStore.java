package org.wbdnext.rootclient;

import android.content.Context;
import android.os.Process;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructStat;
import android.util.AtomicFile;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.security.KeyStore;
import java.util.Arrays;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;

// Android Keystore-backed, app-private, NO_BACKUP persistence of only the
// password + original user short RouteKey for UI autofill. Root startup
// still uses the existing 0600 one-session credential files. Never log,
// place in Intent/argv, SharedPreferences, Android backup or safe TXT.
final class RootEncryptedCredentialStore {
    private static final String ALIAS="wbd-root-a38-ui-credentials-v1";
    private static final String NAME="wbd-root-ui-credentials-v1.gcm";
    private RootEncryptedCredentialStore(){}
    private static File file(Context ctx){
        if(ctx==null)throw new IllegalArgumentException("missing app context");
        return new File(ctx.getNoBackupFilesDir(),NAME);
    }
    private static SecretKey key(boolean create)throws Exception{
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if(store.containsAlias(ALIAS)){
            java.security.Key k=store.getKey(ALIAS,null);
            if(!(k instanceof SecretKey))throw new SecurityException("invalid private credential key");
            return (SecretKey)k;
        }
        if(!create)throw new SecurityException("saved credential keystore key missing");
        KeyGenerator generator=KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(ALIAS,
            KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setRandomizedEncryptionRequired(true)
            .setUserAuthenticationRequired(false)
            .build());
        return generator.generateKey();
    }
    private static void ownerOnly(File f)throws Exception{
        StructStat st=Os.lstat(f.getAbsolutePath());
        if((st.st_mode&OsConstants.S_IFMT)!=OsConstants.S_IFREG||
           (st.st_mode&0777)!=0600||st.st_uid!=Process.myUid()||
           st.st_nlink!=1||st.st_size<1||
           st.st_size>RootSavedCredentialRecord.MAX_FILE)
            throw new SecurityException("saved encrypted credential inode unsafe");
    }
    private static void noSymlinks(File f)throws Exception{
        for(File path:new File[]{f,new File(f.getAbsolutePath()+".new"),
            new File(f.getAbsolutePath()+".bak")}){
            if(path.exists()||java.nio.file.Files.isSymbolicLink(path.toPath())){
                StructStat st=Os.lstat(path.getAbsolutePath());
                if((st.st_mode&OsConstants.S_IFMT)!=OsConstants.S_IFREG||
                   st.st_uid!=Process.myUid()||st.st_nlink!=1)
                    throw new SecurityException("foreign encrypted credential path");
            }
        }
    }
    // The ten named B50 profiles reuse the EXACT existing Keystore key,
    // AES-GCM record codec and 0600 Android AtomicFile persistence.
    // No new credentials, native format, TLS or network engine.
    private static File profileFile(Context ctx,int slot){
        if(slot<1||slot>RootConnectionProfile.SLOTS)
            throw new IllegalArgumentException("profile slot 1.."+RootConnectionProfile.SLOTS);
        return new File(ctx.getNoBackupFilesDir(),
            "wbd-root-ui-credentials-profile-"+slot+".gcm");
    }
    private static void saveFile(File target,String password,String shortKey)
        throws Exception{
        byte[] ciphertext=RootSavedCredentialRecord.encrypt(key(true),password,shortKey);
        noSymlinks(target);
        AtomicFile atomic=new AtomicFile(target);
        FileOutputStream out=null;
        try{
            out=atomic.startWrite();
            Os.fchmod(out.getFD(),0600);
            out.write(ciphertext);
            out.getFD().sync();
            atomic.finishWrite(out);
            out=null;
            Os.chmod(target.getAbsolutePath(),0600);
            ownerOnly(target);
        }catch(Exception failure){
            if(out!=null)atomic.failWrite(out);
            throw failure;
        }finally{Arrays.fill(ciphertext,(byte)0);}
    }
    static synchronized void save(Context ctx,String password,String shortKey)throws Exception{
        saveFile(file(ctx),password,shortKey);
    }
    static synchronized void saveProfile(Context ctx,int slot,String password,String routeKey)
        throws Exception{
        saveFile(profileFile(ctx,slot),password,routeKey);
    }
    private static RootSavedCredentialRecord.Secrets loadFile(File target)throws Exception{
        if(!target.exists()&&!java.nio.file.Files.isSymbolicLink(target.toPath()))
            return null;
        noSymlinks(target);
        ownerOnly(target);
        AtomicFile atomic=new AtomicFile(target);
        byte[] ciphertext=atomic.readFully();
        try{
            if(ciphertext.length>RootSavedCredentialRecord.MAX_FILE)
                throw new SecurityException("saved credential record size invalid");
            return RootSavedCredentialRecord.decrypt(key(false),ciphertext);
        }finally{Arrays.fill(ciphertext,(byte)0);}
    }
    static synchronized RootSavedCredentialRecord.Secrets load(Context ctx)throws Exception{
        return loadFile(file(ctx));
    }
    static synchronized RootSavedCredentialRecord.Secrets loadProfile(Context ctx,int slot)
        throws Exception{
        return loadFile(profileFile(ctx,slot));
    }
    // Activating one saved server makes the legacy "last connection" UI
    // credentials agree with that server across Activity recreation.
    // An empty slot clears ONLY the default remembered record, never the
    // independent credentials belonging to the other three profiles.
    static synchronized RootSavedCredentialRecord.Secrets activateProfile(
        Context ctx,int slot)throws Exception{
        RootSavedCredentialRecord.Secrets selected;
        try{selected=loadFile(profileFile(ctx,slot));}
        catch(Exception unavailable){
            deleteFile(file(ctx));
            return null;
        }
        if(selected==null)deleteFile(file(ctx));
        else saveFile(file(ctx),selected.password,selected.routeKey);
        return selected;
    }
    private static void deleteFile(File target)throws Exception{
        noSymlinks(target);
        new AtomicFile(target).delete();
    }
    static synchronized void clearProfile(Context ctx,int slot)throws Exception{
        deleteFile(profileFile(ctx,slot)); // Keep shared key for other profiles.
    }
    static synchronized void clear(Context ctx)throws Exception{
        deleteFile(file(ctx));
        // "Clear saved credentials" includes all named B50 profiles; do not
        // silently leave old encrypted profiles unreadable under a deleted key.
        for(int slot=1;slot<=RootConnectionProfile.SLOTS;slot++)
            deleteFile(profileFile(ctx,slot));
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if(store.containsAlias(ALIAS))store.deleteEntry(ALIAS);
    }
}
