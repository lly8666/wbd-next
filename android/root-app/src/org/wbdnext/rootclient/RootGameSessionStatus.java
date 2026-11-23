package org.wbdnext.rootclient;

/**
 * App-only presentation of original Go authenticated Game2/4 lifecycle.
 * Native READY is not derived from UI mode or an unrelated TUN counter:
 * original Go prints this exact marker only after 2/4 TLS lanes,
 * the original Rust Game group M4 and the selected UID route are ready.
 * No packet path or alternative transport is implemented here.
 */
final class RootGameSessionStatus {
    private RootGameSessionStatus(){}

    static int expectedLanes(String selectedMode){
        if("game2".equals(selectedMode)||"game2-fixed".equals(selectedMode))
            return 2;
        if("game4".equals(selectedMode)||"game4-fixed".equals(selectedMode))
            return 4;
        return 0;
    }

    static boolean gameReady(String selectedMode,String logLine){
        int lanes=expectedLanes(selectedMode);
        if(lanes==0||logLine==null)return false;
        String marker="V4_ORIGINAL_ANDROID_GAME_NATIVE_READY role=client lanes="+
            lanes+" original_go_tls=1 original_rust_m4=1 uid_route_after_m4=1";
        // OriginalGoMilestones accepts ONLY line start or Go's exact
        // timestamp prefix. endsWith excludes appended native fields.
        return logLine.endsWith(marker)&&OriginalGoMilestones.matches(logLine,marker);
    }

    static String readyBrief(String selectedMode){
        int lanes=expectedLanes(selectedMode);
        if(lanes==0)return null;
        boolean fixed=selectedMode.endsWith("-fixed");
        return "Game"+lanes+(fixed?"/Fixed":"/off")+
            ": 原Go真实TLS组、Rust M4及UID路由已就绪"+
            "；待应用TCP/UDP业务与Stop实机验证";
    }

    static boolean nativeStopped(String logLine){
        return logLine!=null&&
            logLine.endsWith("V4_PUBLIC_NATIVE_STOP_DRAINED role=client")&&
            OriginalGoMilestones.matches(logLine,
                "V4_PUBLIC_NATIVE_STOP_DRAINED role=client");
    }

    static boolean uidRouteWithdrawn(String logLine){
        return logLine!=null&&
            logLine.endsWith("V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client")&&
            OriginalGoMilestones.matches(logLine,
                "V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client");
    }

    static boolean gameGroupStopped(String selectedMode,String logLine){
        int lanes=expectedLanes(selectedMode);
        if(lanes==0||logLine==null)return false;
        String marker="V4_PUBLIC_ANDROID_GAME_STOP_JOINED role=client lanes="+
            lanes+" rust_m4=joined uid_route=settled rst_guard=cleared";
        return logLine.endsWith(marker)&&OriginalGoMilestones.matches(logLine,marker);
    }

    static boolean confirmedPreviousOwnerStop(String selectedMode,boolean groupStopped,
                                              boolean nativeStop,boolean routeStop,
                                              boolean successExit,boolean hadUIDRoute){
        // Product claims a clean cold restart ONLY when the previous
        // original process terminated and every owned UID route was
        // read back as withdrawn. Game never gets special fake credit.
        return successExit&&nativeStop&&(!hadUIDRoute||routeStop)&&
            (expectedLanes(selectedMode)==0||groupStopped);
    }
}
