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
 * No permission to QUERY_ALL_PACKAGES; explicit manifest package queries.
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
        int[] excluded=AllAppUIDPolicy.excluded(Process.myUid(),managerUIDs);
        Collections.sort(packages);
        return new AllAppRouteScope(excluded,packages.toArray(new String[0]));
    }
    static boolean same(Context ctx,int[] excluded,String[] managerPackages){
        if(excluded==null||managerPackages==null)return false;
        try{
            AllAppRouteScope now=snapshot(ctx);
            return Arrays.equals(now.excludedAppIDs,excluded)&&
                Arrays.equals(now.managerPackages,managerPackages);
        }catch(RuntimeException ignored){return false;}
    }
}
