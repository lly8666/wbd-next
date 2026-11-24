package org.wbdnext.rootclient;

/** Original-owner cold rotation policy; no packet path or recurring poll. */
final class RootColdRotation {
    static long delayMillis(int minutes){
        switch(minutes){
            case 0:case 5:case 15:case 30:return minutes*60000L;
            default:throw new IllegalArgumentException("rotation interval 0/5/15/30 minutes");
        }
    }
    static boolean mayRestart(boolean requested,boolean joinedStop,boolean samePhysical){
        return requested&&joinedStop&&samePhysical;
    }
}
