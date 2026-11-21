package org.wbdnext.rootclient;

/**
 * Pure-Java production metadata policy used with Android Os.fstat/lstat
 * and host POSIX filesystem tests, not mock Root or native networking.
 */
final class RootPrivateCredentialContract {
    private RootPrivateCredentialContract(){}
    static final String PASSWORD="wbd-pass.secret";
    static final String ROUTE="wbd-route.secret";
    static final String CA="wbd-server-ca.pem";
    static final int OWNER_ONLY=0600;
    private static final int S_IFMT=0170000;
    private static final int S_IFREG=0100000;
    static int maxBytes(String name){
        if(PASSWORD.equals(name)||ROUTE.equals(name))return 4096;
        if(CA.equals(name))return 1<<20;
        throw new IllegalArgumentException("not an original Go private credential");
    }
    static boolean ownerOnlyRegular(String name,int mode,int uid,long links,
                                    long size,int expectedUid){
        int maximum=maxBytes(name);
        return (mode&S_IFMT)==S_IFREG&&
               (mode&0777)==OWNER_ONLY&&uid==expectedUid&&links==1&&
               size>0&&size<=maximum&&
               (!ROUTE.equals(name)||size==65);
    }
}
