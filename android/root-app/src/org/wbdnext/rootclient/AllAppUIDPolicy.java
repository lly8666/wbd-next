package org.wbdnext.rootclient;

import java.util.TreeSet;

/** Cold root route policy only: app IDs, never raw System/root UIDs. */
final class AllAppUIDPolicy {
    static final int PER_USER=100000;
    static final int FIRST_APP_ID=10000;
    static final int LAST_APP_ID=19999;
    static final int MAX_EXCLUDED=8;
    private AllAppUIDPolicy(){}
    static int appId(int actualUid){
        int id=actualUid%PER_USER;
        if(actualUid<FIRST_APP_ID||id<FIRST_APP_ID||id>LAST_APP_ID)
            throw new IllegalArgumentException("not an ordinary Android application UID");
        return id;
    }
    static int[] excluded(int ownerUID,int[] rootManagerUIDs){
        if(rootManagerUIDs==null||rootManagerUIDs.length<1||
           rootManagerUIDs.length>=MAX_EXCLUDED)
            throw new IllegalArgumentException("a verified KernelSU Manager app UID is required");
        TreeSet<Integer> ids=new TreeSet<>();
        int self=appId(ownerUID);
        ids.add(self);
        for(int uid:rootManagerUIDs){
            int id=appId(uid);
            if(id==self)throw new IllegalArgumentException("Root Manager shares WBD owner UID");
            ids.add(id);
        }
        if(ids.size()<2||ids.size()>MAX_EXCLUDED)
            throw new IllegalArgumentException("invalid bounded App UID exclusions");
        int[] out=new int[ids.size()];
        int i=0;for(int id:ids)out[i++]=id;
        return out;
    }
    static String csv(int[] ids){
        if(ids==null||ids.length<2||ids.length>MAX_EXCLUDED)
            throw new IllegalArgumentException("unvalidated all-app exclusion set");
        StringBuilder result=new StringBuilder();
        int prev=0;
        for(int id:ids){
            if(id<FIRST_APP_ID||id>LAST_APP_ID||id<=prev)
                throw new IllegalArgumentException("noncanonical app IDs");
            if(result.length()>0)result.append(',');
            result.append(id);
            prev=id;
        }
        return result.toString();
    }
}
