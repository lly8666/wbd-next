package org.wbdnext.rootclient;

/** Host-only genuine Go log formats; does not mock TLS or native execution. */
public final class OriginalGoMilestonesTest {
    public static void main(String[] args) {
        for(String marker:new String[]{
            "WBD_PUBLIC_ROOT_SHELL_ENTERED",
            "WBD_PUBLIC_ROOT_UID_VERIFIED",
            "WBD_PUBLIC_ROOT_PRIVATE_DIR_VERIFIED",
            "WBD_PUBLIC_ROOT_OWNER_GUARD_PASSED",
            "WBD_PUBLIC_ROOT_NATIVE_FILES_STAGED",
            "WBD_PUBLIC_ROOT_OWNER_PID_WRITTEN",
            "WBD_PUBLIC_ROOT_EXEC_ATTEMPTED",
            "V4_PUBLIC_ANDROID_GO_ENTRY role=client",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=FLAG_SYNTAX",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=PASSWORD_FILE",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ROUTE_KEY_FILE",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ROUTE_KEY_VALUE",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=INSTALLATION_ID",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=CN_GEOSITE_FILE",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=TLS_CA_FILE",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ALL_APP_EXCLUSIONS",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ANDROID_NETWORK_SCOPE",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=PEER_ADDRESS",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=REQUIRED_COLD_SETTINGS",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=POLICY",
            "V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=OTHER",
            "V4_PUBLIC_ANDROID_GO_ARGS_ACCEPTED role=client",
            "V4_PUBLIC_ANDROID_GO_INTERFACE_FOUND role=client",
            "V4_PUBLIC_ANDROID_GO_TUN_OPEN_ATTEMPTED role=client",
            "V4_PUBLIC_ANDROID_GO_TUN_OPENED role=client",
            "V4_PUBLIC_TUN_TXQLEN role=client",
            "V4_PUBLIC_RAW_AF_PACKET_READY role=client",
            "V4_PUBLIC_ANDROID_COLD_SYN_TX_OK role=client",
            "V4_PUBLIC_ANDROID_COLD_UNAUTH_RST_RX role=client",
            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=permission_denied",
            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=network_unreachable",
            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=invalid_argument",
            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=source_unavailable",
            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=buffer_pressure",
            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=other",
            "V4_PUBLIC_ACTUAL_PEER_SYNACK_MSS_V1 side=client",
            "V4_PUBLIC_LEASE_APPLIED role=client",
            "V4_PUBLIC_GO_RX_HANDOFF role=client",
            "V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED",
            "V4_PUBLIC_ANDROID_PEER_THROW_ROUTE_READBACK role=client",
            "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client",
            "V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client",
            "V4_PUBLIC_NATIVE_STOP_DRAINED role=client"
        }){
            if(!OriginalGoMilestones.matches(marker+" readback=1",marker)||
               !OriginalGoMilestones.matches(
                    "2026/11/18 09:10:11 "+marker+" readback=1",marker))
                throw new AssertionError("original Go marker unavailable: "+marker);
            for(String foreign:new String[]{
                "user-controlled "+marker,
                "2026/11/18 09:10:11 another "+marker,
                "2026/11/18 09:10:11"+marker,
                "2026/11/18 09:10:11 "+marker+"_spoof readback=1",
                marker+"X",
                marker+"\npassword"
            })if(OriginalGoMilestones.matches(foreign,marker))
                throw new AssertionError("substring spoof accepted");
        }
        if(OriginalGoMilestones.matches(null,"marker")||
           OriginalGoMilestones.matches("marker",null))
            throw new AssertionError("null accepted");
        System.out.println("ANDROID_ARM64_ORIGINAL_GO_ANCHORED_COLD_STAGE_HOST_PASS");
    }
}
