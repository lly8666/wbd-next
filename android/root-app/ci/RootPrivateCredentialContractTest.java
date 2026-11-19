package org.wbdnext.rootclient;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermission;
import java.util.EnumSet;
import java.util.Set;

/** Host POSIX filesystem test of exact production Android cold-file metadata policy. */
public final class RootPrivateCredentialContractTest {
    private static Set<PosixFilePermission> perms(String octal){
        Set<PosixFilePermission> result=EnumSet.noneOf(PosixFilePermission.class);
        if(octal.charAt(0)=='6'){
            result.add(PosixFilePermission.OWNER_READ);
            result.add(PosixFilePermission.OWNER_WRITE);
        }
        if(octal.charAt(1)=='6'){
            result.add(PosixFilePermission.GROUP_READ);
            result.add(PosixFilePermission.GROUP_WRITE);
        }
        if(octal.charAt(1)=='4')result.add(PosixFilePermission.GROUP_READ);
        if(octal.charAt(2)=='4')result.add(PosixFilePermission.OTHERS_READ);
        return result;
    }
    private static boolean safe(Path file,String name,int expectedUid)throws Exception{
        LinkOption nofollow=LinkOption.NOFOLLOW_LINKS;
        int mode=((Number)Files.getAttribute(file,"unix:mode",nofollow)).intValue();
        int uid=((Number)Files.getAttribute(file,"unix:uid",nofollow)).intValue();
        long links=((Number)Files.getAttribute(file,"unix:nlink",nofollow)).longValue();
        long size=((Number)Files.getAttribute(file,"unix:size",nofollow)).longValue();
        return RootPrivateCredentialContract.ownerOnlyRegular(name,mode,uid,links,size,expectedUid);
    }
    private static void check(boolean condition,String message){
        if(!condition)throw new AssertionError(message);
    }
    private static void reject(Runnable test){
        try{test.run();throw new AssertionError("invalid private file name accepted");}
        catch(IllegalArgumentException expected){}
    }
    public static void main(String[] args)throws Exception{
        Path dir=Files.createTempDirectory("wbd-posix-credentials-");
        Path password=dir.resolve(RootPrivateCredentialContract.PASSWORD);
        Path route=dir.resolve(RootPrivateCredentialContract.ROUTE);
        Path ca=dir.resolve(RootPrivateCredentialContract.CA);
        Files.write(password,"password\\n".replace("\\n","\n").getBytes(StandardCharsets.US_ASCII));
        int uid=((Number)Files.getAttribute(password,"unix:uid")).intValue();
        Files.setPosixFilePermissions(password,perms("600"));
        check(safe(password,RootPrivateCredentialContract.PASSWORD,uid),
            "0600 regular password must be accepted");
        // Android ContextImpl.MODE_PRIVATE may create precisely this 0660.
        Files.setPosixFilePermissions(password,perms("660"));
        check(!safe(password,RootPrivateCredentialContract.PASSWORD,uid),
            "0660 MODE_PRIVATE must be rejected by Go parity policy");
        Files.setPosixFilePermissions(password,perms("640"));
        check(!safe(password,RootPrivateCredentialContract.PASSWORD,uid),
            "0640 group-readable password accepted");
        Files.setPosixFilePermissions(password,perms("604"));
        check(!safe(password,RootPrivateCredentialContract.PASSWORD,uid),
            "0604 world-readable password accepted");
        Files.setPosixFilePermissions(password,perms("600"));
        check(!safe(password,RootPrivateCredentialContract.PASSWORD,uid+1),
            "wrong Android app owner accepted");
        Path hard=dir.resolve("hard");
        Files.createLink(hard,password);
        check(!safe(password,RootPrivateCredentialContract.PASSWORD,uid),
            "hardlinked credential accepted");
        Files.delete(hard);
        Path link=dir.resolve("link");
        Files.createSymbolicLink(link,password);
        check(!safe(link,RootPrivateCredentialContract.PASSWORD,uid),
            "symlink accepted despite O_NOFOLLOW gate");
        Files.write(route,(new String(new char[64]).replace("\0","a")+"\n")
            .getBytes(StandardCharsets.US_ASCII));
        Files.setPosixFilePermissions(route,perms("660"));
        check(!safe(route,RootPrivateCredentialContract.ROUTE,uid),
            "0660 route-key file accepted");
        Files.setPosixFilePermissions(route,perms("600"));
        check(safe(route,RootPrivateCredentialContract.ROUTE,uid),
            "proper 32-byte 64hex + newline route file rejected");
        Files.write(route,"short\n".getBytes(StandardCharsets.US_ASCII));
        check(!safe(route,RootPrivateCredentialContract.ROUTE,uid),
            "truncated route key file accepted");
        Files.write(ca,"-----BEGIN CERTIFICATE-----\n".getBytes(StandardCharsets.US_ASCII));
        Files.setPosixFilePermissions(ca,perms("600"));
        check(safe(ca,RootPrivateCredentialContract.CA,uid),
            "owner-only optional CA metadata should be accepted");
        reject(()->RootPrivateCredentialContract.maxBytes("../password"));
        check(!RootPrivateCredentialContract.ownerOnlyRegular(
                RootPrivateCredentialContract.PASSWORD,0100600,uid,1,0,uid),
              "empty secret accepted");
        check(!RootPrivateCredentialContract.ownerOnlyRegular(
                RootPrivateCredentialContract.PASSWORD,0100600,uid,1,4097,uid),
              "unbounded original Go secret accepted");
        System.out.println("ANDROID_ORIGINAL_GO_COLD_SECRET_0600_POSIX_HOST_PASS");
    }
}
