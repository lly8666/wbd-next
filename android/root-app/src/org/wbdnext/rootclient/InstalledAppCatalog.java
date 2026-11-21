package org.wbdnext.rootclient;

import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.os.Process;
import java.util.ArrayList;
import java.util.List;
import java.util.TreeMap;

// Queries only launcher-visible installed packages for current Android user,
// not QUERY_ALL_PACKAGES, arbitrary manual UIDs, or system/root processes.
// Every cold Start rechecks the real PackageManager association.
final class InstalledAppCatalog {
    private InstalledAppCatalog(){}

    static List<InstalledAppTarget> launchable(Context ctx){
        PackageManager pm=ctx.getPackageManager();
        Intent intent=new Intent(Intent.ACTION_MAIN);
        intent.addCategory(Intent.CATEGORY_LAUNCHER);
        TreeMap<String,InstalledAppTarget> unique=new TreeMap<>();
        for(ResolveInfo info:pm.queryIntentActivities(intent,0)){
            if(info==null||info.activityInfo==null)continue;
            String name=info.activityInfo.packageName;
            try{
                ApplicationInfo app=pm.getApplicationInfo(name,0);
                if(!InstalledAppTarget.eligible(name,app.uid,Process.myUid(),
                     ctx.getPackageName()))continue;
                CharSequence label=pm.getApplicationLabel(app);
                unique.put(name,new InstalledAppTarget(name,
                    label==null?name:label.toString(),app.uid));
            }catch(PackageManager.NameNotFoundException|SecurityException e){
                // Package changed or became invisible during the snapshot.
            }
        }
        return new ArrayList<>(unique.values());
    }

    static boolean stillSameGroup(Context ctx,String[] packageNames,int[] uids){
        if(packageNames==null||uids==null||
           packageNames.length<1||packageNames.length>SelectedAppGroup.MAX_PACKAGES||
           uids.length<1||uids.length>SelectedAppGroup.MAX_UIDS)return false;
        PackageManager pm=ctx.getPackageManager();
        ArrayList<InstalledAppTarget> resolved=new ArrayList<>();
        try{
            for(String name:packageNames){
                if(!InstalledAppTarget.validPackage(name))return false;
                ApplicationInfo info=pm.getApplicationInfo(name,0);
                if(pm.getLaunchIntentForPackage(name)==null)return false;
                resolved.add(new InstalledAppTarget(name,name,info.uid));
            }
            return SelectedAppGroup.matchesReceipt(packageNames,uids,resolved,
                Process.myUid(),ctx.getPackageName());
        }catch(PackageManager.NameNotFoundException|SecurityException|
               IllegalArgumentException e){
            return false; // package was removed, remapped or made invisible
        }
    }

    static boolean stillSame(Context ctx,String packageName,int uid){
        if(!InstalledAppTarget.eligible(packageName,uid,Process.myUid(),
             ctx.getPackageName()))return false;
        PackageManager pm=ctx.getPackageManager();
        try{
            ApplicationInfo installed=pm.getApplicationInfo(packageName,0);
            return installed.uid==uid&&
                pm.getLaunchIntentForPackage(packageName)!=null;
        }catch(PackageManager.NameNotFoundException|SecurityException e){
            return false;
        }
    }
}
