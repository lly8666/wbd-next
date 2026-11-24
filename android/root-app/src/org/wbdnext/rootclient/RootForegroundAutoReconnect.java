package org.wbdnext.rootclient;

/** B60 foreground-only automatic cold Network handover decision. */
final class RootForegroundAutoReconnect {
    private boolean armed,pending;
    void arm(){armed=true;pending=false;}
    boolean armed(){return armed;}
    boolean pending(){return pending;}
    void onNetworkStop(boolean selectedNetworkChanged){
        if(armed&&selectedNetworkChanged){armed=false;pending=true;}
    }
    boolean complete(boolean ownerGone,boolean joinedStop,boolean physicalAvailable){
        if(!pending||!ownerGone)return false;
        pending=false;
        return joinedStop&&physicalAvailable;
    }
    void cancel(){armed=false;pending=false;}
}
