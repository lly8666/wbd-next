package org.wbdnext.rootclient;

// Host JVM exercises the actual selected-package/UID contract. Android
// PackageManager discovery and system broadcasts remain P3 NOT_RUN.
public final class InstalledAppTargetTest {
    private static int count;
    private static void check(boolean ok,String label){
        count++;
        if(!ok)throw new AssertionError(label);
    }
    public static void main(String[] args){
        final int self=10218;
        final String selfPkg="org.wbdnext.rootclient";
        InstalledAppTarget target=new InstalledAppTarget("com.example.browser","Browser",10502);
        check(target.matches("com.example.browser",10502,self,selfPkg),"matched real package and UID");
        check(!target.matches("com.example.browser",10503,self,selfPkg),"reject remapped UID");
        check(!target.matches("com.example.other",10502,self,selfPkg),"reject another package sharing UID");
        check(!target.matches("com.example.browser",10502,10502,selfPkg),"reject owner UID");
        check(!InstalledAppTarget.eligible("com.example.browser",9999,self,selfPkg),"reject system UID");
        check(!InstalledAppTarget.eligible("com.example.browser",0,self,selfPkg),"reject root");
        check(!InstalledAppTarget.eligible(selfPkg,self,self,selfPkg),"reject own package");
        check(InstalledAppTarget.eligible("com.example.browser",10502,self,selfPkg),"allow separate real app UID");
        check(!InstalledAppTarget.validPackage("com..broken"),"reject empty package component");
        check(!InstalledAppTarget.validPackage("com.bad;exit"),"reject shell characters");
        check(!InstalledAppTarget.validPackage("com.9first"),"reject invalid component start");
        check(!InstalledAppTarget.validPackage("nodot"),"reject ambiguous package");
        check(InstalledAppTarget.validPackage("com.example_2.app3"),"allow valid package characters");
        check(target.title().contains("com.example.browser")&&target.title().contains("10502"),"UI displays package and UID");
        check(!InstalledAppTarget.eligible("com.example.browser",2000000,self,selfPkg),"reject out of range");
        check(!InstalledAppTarget.eligible("com.example.browser",10502,10502,selfPkg),"reject owner shared UID");
        check(target.matches("com.example.browser",10502,self,selfPkg),"original identity stable");
        System.out.println("ANDROID_INSTALLED_PACKAGE_UID_POLICY_PASS assertions="+count);
    }
}
