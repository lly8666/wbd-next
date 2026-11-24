package org.wbdnext.rootclient;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Process;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;

/**
 * Device-wide ordinary app UID scope, across bounded per-user ranges.
 * Android system/root/isolated UIDs are NOT included. The controller and
 * every known installed KernelSU Manager get exact per-user AppID exclusions.
 * B32 original Root sideload app has QUERY_ALL_PACKAGES for complete
 * installed ordinary App visibility. Owner/KernelSU UIDs are still excluded
 * from the full-app kernel route; no new packet engine is used.
 */
final class AllAppRouteScope {
    private static final String[] MANAGERS={
        "me.weishu.kernelsu","com.rifsxd.ksunext","com.sukisu.ultra"
    };
    final int[] excludedAppIDs;
    final String[] managerPackages;
    private AllAppRouteScope(int[] excluded,String[] managers){
        excludedAppIDs=excluded.clone();managerPackages=managers.clone();
    }
    static AllAppRouteScope snapshot(Context ctx){
        return snapshot(ctx,new String[0],new int[0]);
    }
    static AllAppRouteScope snapshot(Context ctx,String[] bypassPackages,int[] bypassUIDs){
        if(bypassPackages==null||bypassUIDs==null||
            bypassPackages.length!=bypassUIDs.length||bypassPackages.length>6)
            throw new IllegalArgumentException("invalid selected all-app bypass list");

        PackageManager pm=ctx.getPackageManager();
        ArrayList<Integer> uids=new ArrayList<>();
        ArrayList<String> packages=new ArrayList<>();
        for(String pkg:MANAGERS){
            try{
                ApplicationInfo info=pm.getApplicationInfo(pkg,0);
                // No exemptions from untrusted missing, system or own UID.
                if(info==null||info.uid==Process.myUid())
                    throw new IllegalStateException("KernelSU Manager app UID invalid");
                AllAppUIDPolicy.appId(info.uid);
                uids.add(info.uid);
                packages.add(pkg);
            }catch(PackageManager.NameNotFoundException absent){
                // Other supported KSU Manager variants may be installed.
            }
        }
        if(packages.isEmpty())
            throw new IllegalStateException("No recognized installed KernelSU Manager; full-device proxy refused");
        int[] managerUIDs=new int[uids.size()];
        for(int i=0;i<uids.size();i++)managerUIDs[i]=uids.get(i);
        // Cold PackageManager revalidation. Root's user-space install
        // visibility is only an enumeration aid, NEVER a trusted UID source.
        String previous="";
        for(int i=0;i<bypassPackages.length;i++){
            String pkg=bypassPackages[i];
            if(!InstalledAppTarget.eligible(pkg,bypassUIDs[i],
                Process.myUid(),ctx.getPackageName())||
                (!previous.isEmpty()&&previous.compareTo(pkg)>=0)||
                packages.contains(pkg))
                throw new IllegalArgumentException("noncanonical bypass package identity");
            previous=pkg;
            try{
                ApplicationInfo info=pm.getApplicationInfo(pkg,0);
                if(info==null||info.uid!=bypassUIDs[i])
                    throw new IllegalArgumentException("installed bypass UID has changed");
            }catch(PackageManager.NameNotFoundException absent){
                throw new IllegalArgumentException("previously selected bypass app uninstalled");
            }
        }
        int[] excluded=AllAppUIDPolicy.excluded(Process.myUid(),managerUIDs,bypassUIDs);
        Collections.sort(packages);
        return new AllAppRouteScope(excluded,packages.toArray(new String[0]));
    }
    static boolean same(Context ctx,int[] excluded,String[] managerPackages){
        return same(ctx,excluded,managerPackages,new String[0],new int[0]);
    }
    static boolean same(Context ctx,int[] excluded,String[] managerPackages,
                        String[] bypassPackages,int[] bypassUIDs){
        if(excluded==null||managerPackages==null)return false;
        try{
            AllAppRouteScope now=snapshot(ctx,bypassPackages,bypassUIDs);
            return Arrays.equals(now.excludedAppIDs,excluded)&&
                Arrays.equals(now.managerPackages,managerPackages);
        }catch(RuntimeException ignored){return false;}
    }
}
