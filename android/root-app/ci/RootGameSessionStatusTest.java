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
            "normal",false,true,true,true,true),"Normal owned Stop confirmed");
        no(RootGameSessionStatus.confirmedPreviousOwnerStop(
            "normal",false,true,false,true,true),"must withdraw UID route");
        no(RootGameSessionStatus.confirmedPreviousOwnerStop(
            "normal",false,false,true,true,true),"must join original Rust");
        no(RootGameSessionStatus.confirmedPreviousOwnerStop(
            "normal",false,true,true,false,true),"requires zero exit");
        ok(RootGameSessionStatus.confirmedPreviousOwnerStop(
            "normal",false,true,false,true,false),"no UID route installed");
        for(int lanes:new int[]{2,4}){
            for(String suffix:new String[]{"","-fixed"}){
                String mode="game"+lanes+suffix;
                String marker="V4_PUBLIC_ANDROID_GAME_STOP_JOINED role=client lanes="+
                    lanes+" rust_m4=joined uid_route=settled rst_guard=cleared";
                ok(RootGameSessionStatus.gameGroupStopped(mode,marker),
                    "original Game grouped Stop");
                ok(RootGameSessionStatus.gameGroupStopped(mode,
                    "2026/11/23 18:33:00 "+marker),"timestamped grouped Stop");
                no(RootGameSessionStatus.gameGroupStopped(mode,marker.replace(
                    "rst_guard=cleared","rst_guard=unknown")),"RST not cleared");
                no(RootGameSessionStatus.gameGroupStopped(mode,marker.replace(
                    "rust_m4=joined","rust_m4=active")),"Rust M4 not drained");
                no(RootGameSessionStatus.gameGroupStopped(mode,marker+
                    " spoofed=1"),"fake appended group marker");
                no(RootGameSessionStatus.gameGroupStopped("game"+
                    (lanes==2?4:2),marker),"wrong Game group stop");
                no(RootGameSessionStatus.confirmedPreviousOwnerStop(
                    mode,false,true,true,true,true),
                    "No Game-specific owned Stop token");
                ok(RootGameSessionStatus.confirmedPreviousOwnerStop(
                    mode,true,true,true,true,true),"Full Game owned Stop");
                no(RootGameSessionStatus.confirmedPreviousOwnerStop(
                    mode,true,false,true,true,true),"Game native not drained");
                no(RootGameSessionStatus.confirmedPreviousOwnerStop(
                    mode,true,true,false,true,true),"Game UID still routed");
                no(RootGameSessionStatus.confirmedPreviousOwnerStop(
                    mode,true,true,true,false,true),"Game nonzero exit");
            }
        }
        System.out.println("ANDROID_B48_GAME2_GAME4_ORIGINAL_GROUP_UID_RST_FULL_STOP_PARSER_HOST_PASS");
    }
}
