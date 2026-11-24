package org.wbdnext.rootclient;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

// Real positive/negative selection contract shared by production Java code.
// Android PackageManager/KernelSU/netd runtime still NOT_RUN in CI.
public final class SelectedAppGroupTest {
    private static int count;
    private static void check(boolean ok,String reason){
        count++;
        if(!ok)throw new AssertionError(reason);
    }
    private static InstalledAppTarget app(String name,int uid){
        return new InstalledAppTarget(name,name,uid);
    }
    private static SelectedAppGroup make(List<InstalledAppTarget> apps){
        return SelectedAppGroup.from(apps,10101,"org.wbdnext.rootclient");
    }
    private static void mustFail(List<InstalledAppTarget> apps,String reason){
        boolean rejected=false;
        try{make(apps);}
        catch(IllegalArgumentException e){rejected=true;}
        check(rejected,reason);
    }
    private static void mustRejectInvalidTarget(String name,int uid,String reason){
        boolean rejected=false;
        try{new InstalledAppTarget(name,name,uid);}
        catch(IllegalArgumentException e){rejected=true;}
        check(rejected,reason);
    }
    public static void main(String[] args){
        InstalledAppTarget a=app("com.a.alpha",12010),b=app("com.b.beta",12045);
        InstalledAppTarget c=app("com.c.gamma",12045);
        SelectedAppGroup g=make(Arrays.asList(b,a,c));
        check(Arrays.equals(g.packages,new String[]{"com.a.alpha","com.b.beta","com.c.gamma"}),
            "canonical package order");
        check(Arrays.equals(g.uids,new int[]{12010,12045}),"shared uid deduplicated");
        check(g.commaSeparatedUIDs().equals("12010,12045"),"native UID argv is deterministic");
        check(SelectedAppGroup.matchesReceipt(g.packages,g.uids,
            Arrays.asList(a,b,c),10101,"org.wbdnext.rootclient"),"matching exact selection");
        check(!SelectedAppGroup.matchesReceipt(g.packages,g.uids,
            Arrays.asList(a,app("com.b.beta",12046),c),
            10101,"org.wbdnext.rootclient"),"reject remapped UID");
        check(!SelectedAppGroup.matchesReceipt(g.packages,g.uids,
            Arrays.asList(a,c),10101,"org.wbdnext.rootclient"),"reject missing selected package");
        check(!SelectedAppGroup.matchesReceipt(new String[]{"com.a.alpha","com.c.gamma","com.b.beta"},
            g.uids,Arrays.asList(a,b,c),10101,"org.wbdnext.rootclient"),"reject unordered package receipt");
        check(!SelectedAppGroup.matchesReceipt(g.packages,new int[]{12045,12010},
            Arrays.asList(a,b,c),10101,"org.wbdnext.rootclient"),"reject unordered UIDs");
        check(!SelectedAppGroup.matchesReceipt(g.packages,new int[]{12010,12045,12099},
            Arrays.asList(a,b,c),10101,"org.wbdnext.rootclient"),"reject extra unowned UID");
        check(Arrays.equals(make(Arrays.asList(a)).uids,new int[]{12010}),"single UID backward compatible");
        mustFail(new ArrayList<>(),"empty selection");
        mustFail(Arrays.asList(a,a),"duplicate package");
        mustFail(Arrays.asList(app("org.wbdnext.rootclient",10101)),"own UID/own package");
        mustRejectInvalidTarget("com.bad.system",9999,"system UID rejected before assembly");
        mustRejectInvalidTarget("com.bad.root",0,"root UID rejected before assembly");
        mustFail(Arrays.asList(app("com.a.alpha",10101)),"alias of owner UID");
        // B58 real production selection: 16 different Android UIDs and
        // 32 installed package names, including shared-UID applications.
        List<InstalledAppTarget> sixteen=new ArrayList<>();
        for(int i=0;i<16;i++)sixteen.add(app("com.test.app"+i,11000+i));
        check(make(sixteen).uids.length==16,"sixteen original UID routes supported");
        check(make(sixteen).commaSeparatedUIDs().split(",").length==16,
            "all 16 original Go --android-route-uids forwarded");
        List<InstalledAppTarget> seventeen=new ArrayList<>(sixteen);
        seventeen.add(app("com.test.app16",11016));
        mustFail(seventeen,"over sixteen real UIDs");
        List<InstalledAppTarget> packages=new ArrayList<>();
        for(int i=0;i<32;i++)packages.add(app("com.test.pkg"+i,11000+i%16));
        SelectedAppGroup wide=make(packages);
        check(wide.uids.length==16&&wide.packages.length==32,
            "32 packages sharing 16 real App UIDs");
        check(SelectedAppGroup.matchesReceipt(wide.packages,wide.uids,
            packages,10101,"org.wbdnext.rootclient"),
            "32 package/16 UID exact cold selection receipt");
        packages.add(app("com.test.pkg32",11000));
        mustFail(packages,"over thirty-two packages");
        System.out.println("ANDROID_ROOT_MULTI_APP_UID_GROUP_CONTRACT_PASS assertions="+count);
        System.out.println("ANDROID_B58_SELECTED_16_UID_32_PACKAGE_ORIGINAL_ROOT_HOST_PASS");
    }
}
