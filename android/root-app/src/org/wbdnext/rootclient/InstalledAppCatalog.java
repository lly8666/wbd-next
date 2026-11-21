package org.wbdnext.rootclient;

import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.net.Uri;
import android.os.Process;
import java.util.ArrayList;
import java.util.List;
import java.util.TreeMap;
import java.util.TreeSet;

// B26: discover current-user launchers plus the narrowly-declared Android
// share-text and HTTPS handlers. This includes installed non-launcher apps
// exposing those standard entry points, WITHOUT QUERY_ALL_PACKAGES.
// All discovery and UID identity checks are cold-only, never in Go/Rust M4.
final class InstalledAppCatalog {
    private InstalledAppCatalog(){}

    private static List<Intent> discoverableIntents(){
        ArrayList<Intent> intents=new ArrayList<>();
        Intent launcher=new Intent(Intent.ACTION_MAIN);
        launcher.addCategory(Intent.CATEGORY_LAUNCHER);
        intents.add(launcher);
        Intent share=new Intent(Intent.ACTION_SEND);
        share.setType("text/plain");
        intents.add(share);
        Intent web=new Intent(Intent.ACTION_VIEW,
            Uri.parse("https://example.org/"));
        web.addCategory(Intent.CATEGORY_BROWSABLE);
        intents.add(web);
        return intents;
    }

    private static TreeSet<String> visibleNames(PackageManager pm){
        TreeSet<String> names=new TreeSet<>();
        // Query only the three explicit Android manifest intents once per
        // cold scope check. No per-selected-app full label scan.
        for(Intent intent:discoverableIntents()){
            for(ResolveInfo info:pm.queryIntentActivities(intent,0)){
                if(info!=null&&info.activityInfo!=null)
                    names.add(info.activityInfo.packageName);
            }
        }
        return names;
    }

    static List<InstalledAppTarget> discoverable(Context ctx){
        PackageManager pm=ctx.getPackageManager();
        TreeMap<String,InstalledAppTarget> unique=new TreeMap<>();
        for(String name:visibleNames(pm)){
            try{
                ApplicationInfo app=pm.getApplicationInfo(name,0);
                if(!InstalledAppTarget.eligible(name,app.uid,Process.myUid(),
                    ctx.getPackageName()))continue;
                CharSequence label=pm.getApplicationLabel(app);
                unique.put(name,new InstalledAppTarget(name,
                    label==null?name:label.toString(),app.uid));
            }catch(PackageManager.NameNotFoundException|
                   SecurityException|IllegalArgumentException ignored){
                // Changed or no longer visible in this cold snapshot.
            }
        }
        return new ArrayList<>(unique.values());
    }

    static boolean stillSameGroup(Context ctx,String[] packageNames,int[] uids){
        if(packageNames==null||uids==null||
           packageNames.length<1||packageNames.length>SelectedAppGroup.MAX_PACKAGES||
           uids.length<1||uids.length>SelectedAppGroup.MAX_UIDS)return false;
        PackageManager pm=ctx.getPackageManager();
        TreeSet<String> available=visibleNames(pm);
        ArrayList<InstalledAppTarget> resolved=new ArrayList<>();
        try{
            for(String name:packageNames){
                if(!available.contains(name))return false;
                ApplicationInfo app=pm.getApplicationInfo(name,0);
                resolved.add(new InstalledAppTarget(name,name,app.uid));
            }
            return SelectedAppGroup.matchesReceipt(packageNames,uids,resolved,
                Process.myUid(),ctx.getPackageName());
        }catch(PackageManager.NameNotFoundException|SecurityException|
               IllegalArgumentException changed){return false;}
    }

    static boolean stillSame(Context ctx,String packageName,int uid){
        if(!InstalledAppTarget.eligible(packageName,uid,Process.myUid(),
            ctx.getPackageName()))return false;
        PackageManager pm=ctx.getPackageManager();
        if(!visibleNames(pm).contains(packageName))return false;
        try{
            ApplicationInfo app=pm.getApplicationInfo(packageName,0);
            return app.uid==uid;
        }catch(PackageManager.NameNotFoundException|SecurityException ignored){
            return false;
        }
    }
}
