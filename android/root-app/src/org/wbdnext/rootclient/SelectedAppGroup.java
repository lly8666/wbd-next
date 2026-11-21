package org.wbdnext.rootclient;

import java.util.ArrayList;
import java.util.List;
import java.util.TreeMap;
import java.util.TreeSet;

// The kernel routes by UID: one or multiple selected launchable packages can
// share an identical UID. Capture exactly one sorted, bounded cold snapshot;
// never requery PackageManager on the original Rust packet path.
final class SelectedAppGroup {
    static final int MAX_UIDS=8;
    static final int MAX_PACKAGES=16;
    final String[] packages;
    final int[] uids;

    private SelectedAppGroup(String[] packages,int[] uids){
        this.packages=packages.clone();
        this.uids=uids.clone();
    }
    static SelectedAppGroup from(List<InstalledAppTarget> selected,
                                 int ownUID,String ownPackage){
        if(selected==null||selected.isEmpty()||selected.size()>MAX_PACKAGES)
            throw new IllegalArgumentException("Select 1..16 real packages");
        TreeMap<String,Integer> byPackage=new TreeMap<>();
        TreeSet<Integer> uniqueUIDs=new TreeSet<>();
        for(InstalledAppTarget app:selected){
            if(app==null||!InstalledAppTarget.eligible(
                  app.packageName,app.uid,ownUID,ownPackage)){
                throw new IllegalArgumentException("Invalid selected system/root/own package");
            }
            if(byPackage.put(app.packageName,app.uid)!=null){
                throw new IllegalArgumentException("Duplicate selected package");
            }
            uniqueUIDs.add(app.uid);
            if(uniqueUIDs.size()>MAX_UIDS){
                throw new IllegalArgumentException("At most 8 unique App UIDs per session");
            }
        }
        String[] packages=byPackage.keySet().toArray(new String[0]);
        int[] uids=new int[uniqueUIDs.size()];
        int i=0;
        for(int uid:uniqueUIDs)uids[i++]=uid;
        return new SelectedAppGroup(packages,uids);
    }
    // The Intent must never supply a numeric UID unrelated to the checked
    // package names; it can be inspected at each Android cold-control stage.
    static boolean matchesReceipt(String[] names,int[] allUIDs,
                                  List<InstalledAppTarget> resolved,
                                  int ownUID,String ownPackage){
        try{
            SelectedAppGroup current=from(resolved,ownUID,ownPackage);
            if(names==null||allUIDs==null||
                names.length!=current.packages.length||
                allUIDs.length!=current.uids.length)return false;
            for(int i=0;i<names.length;i++){
                if(!current.packages[i].equals(names[i]))return false;
            }
            for(int i=0;i<allUIDs.length;i++){
                if(current.uids[i]!=allUIDs[i])return false;
            }
            return true;
        }catch(IllegalArgumentException e){
            return false;
        }
    }
    String commaSeparatedUIDs(){
        StringBuilder b=new StringBuilder();
        for(int uid:uids){
            if(b.length()>0)b.append(',');
            b.append(uid);
        }
        return b.toString();
    }
}
