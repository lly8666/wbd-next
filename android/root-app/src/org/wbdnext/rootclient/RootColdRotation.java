package org.wbdnext.rootclient;

/** Original-owner cold rotation policy; no packet path or recurring poll. */
final class RootColdRotation {
    static long delayMillis(int minutes){
        switch(minutes){
            case 0:case 5:case 15:case 30:return minutes*60000L;
            default:throw new IllegalArgumentException("rotation interval 0/5/15/30 minutes");
        }
    }
    // Prefer actual physical default, validated alternate, then sole LAN.
    static int recoveryIndex(long active,long excluded,long[] handles,boolean[] validated){
        int only=-1,count=0,online=-1;
        for(int i=0;i<handles.length;i++){
            if(handles[i]==0||handles[i]==excluded)continue;
            if(handles[i]==active)return i;
            if(validated[i]&&online<0)online=i;
            only=i;count++;
        }
        return online>=0?online:count==1?only:-1;
    }
    static boolean mayRestart(boolean requested,boolean joinedStop,boolean samePhysical){
        return requested&&joinedStop&&samePhysical;
    }
}
