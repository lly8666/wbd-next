package org.wbdnext.rootclient;

/** B47 actual App lifecycle parser tested without any fake Android guest. */
public final class RootGameSessionStatusTest {
    private static void ok(boolean value,String name){
        if(!value)throw new AssertionError(name);
    }
    private static void no(boolean value,String name){ok(!value,name);}
    public static void main(String[] args){
        for(int lanes:new int[]{2,4}){
            String game="game"+lanes;
            String original="V4_ORIGINAL_ANDROID_GAME_NATIVE_READY role=client lanes="+
                lanes+" original_go_tls=1 original_rust_m4=1 uid_route_after_m4=1";
            ok(RootGameSessionStatus.expectedLanes(game)==lanes,"off mode lanes");
            ok(RootGameSessionStatus.expectedLanes(game+"-fixed")==lanes,"fixed mode lanes");
            ok(RootGameSessionStatus.gameReady(game,original),"original Game ready");
            ok(RootGameSessionStatus.gameReady(game+"-fixed",
                "2026/11/23 18:30:00 "+original),"timestamped Game ready");
            no(RootGameSessionStatus.gameReady("game"+(lanes==2?4:2),original),
                "wrong Game physical group");
            no(RootGameSessionStatus.gameReady(game,original+" injected=true"),
                "appended unsupported ready evidence");
            no(RootGameSessionStatus.gameReady(game,"bad-hostname "+original),
                "untrusted substring");
            no(RootGameSessionStatus.gameReady(game,original.replace(
                "original_rust_m4=1","original_rust_m4=0")),"M4 missing");
            no(RootGameSessionStatus.gameReady(game,original.replace(
                "uid_route_after_m4=1","uid_route_after_m4=0")),"UID not ready");
            ok(RootGameSessionStatus.readyBrief(game).contains(
                "Game"+lanes+"/off"),"Game off UI");
            ok(RootGameSessionStatus.readyBrief(game+"-fixed").contains(
                "Game"+lanes+"/Fixed"),"Game fixed UI");
            ok(RootGameSessionStatus.readyBrief(game+"-fixed").contains(
                "待应用TCP/UDP"),"kernel receipt not App E2E");
        }
        for(String normal:new String[]{"normal","fec-fixed","fec-auto",null}){
            ok(RootGameSessionStatus.expectedLanes(normal)==0,"no fake Game");
            no(RootGameSessionStatus.gameReady(normal,
                "V4_ORIGINAL_ANDROID_GAME_NATIVE_READY role=client lanes=2 original_go_tls=1 original_rust_m4=1 uid_route_after_m4=1"),
                "normal cannot become Game READY");
        }
        String nativeStop="V4_PUBLIC_NATIVE_STOP_DRAINED role=client";
        String routeStop="V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client";
        ok(RootGameSessionStatus.nativeStopped(nativeStop),"native Stop");
        ok(RootGameSessionStatus.uidRouteWithdrawn(
            "2026/11/23 18:33:00 "+routeStop),"route Stop");
        no(RootGameSessionStatus.nativeStopped(nativeStop+" incomplete=1"),
            "fake native Stop suffix");
        no(RootGameSessionStatus.uidRouteWithdrawn("injected "+routeStop),
            "fake route Stop");
        ok(RootGameSessionStatus.confirmedPreviousOwnerStop(
            true,true,true,true),"all owned Stop confirmed");
        no(RootGameSessionStatus.confirmedPreviousOwnerStop(
            true,false,true,true),"must withdraw UID route");
        no(RootGameSessionStatus.confirmedPreviousOwnerStop(
            false,true,true,true),"must join original Rust worker");
        no(RootGameSessionStatus.confirmedPreviousOwnerStop(
            true,true,false,true),"must have native zero exit");
        ok(RootGameSessionStatus.confirmedPreviousOwnerStop(
            true,false,true,false),"no UID route was installed");
        System.out.println("ANDROID_B47_GAME2_GAME4_ORIGINAL_NATIVE_READY_OWNED_STOP_PARSER_HOST_PASS");
    }
}
