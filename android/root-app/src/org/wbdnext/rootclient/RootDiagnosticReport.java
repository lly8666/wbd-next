package org.wbdnext.rootclient;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Production safe diagnostic export, NOT raw Android logcat/native stdout.
 * Each stage is exactly RootDiagnosticReceipt.Event. A47 additionally
 * exports strictly allowlisted original-Rust numeric RAW diagnostic frames,
 * including numeric IP/ports; arbitrary native stderr is still rejected.
 * Host JVM tests run this SAME report builder.
 */
final class RootDiagnosticReport {
    private RootDiagnosticReport(){}
    private static final int FILE_BOUND=16384;
    private static final int MAX_LINES=180;
    private static final int MAX_NATIVE_DEBUG=44;
    private static boolean validSource(String s){
        if(s==null||s.length()!=40)return false;
        for(int i=0;i<s.length();i++){
            char c=s.charAt(i);
            if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;
        }
        return true;
    }
    private static void appendSafe(File f,List<String> into,List<String> debug){
        if(!f.isFile()||f.length()<0||f.length()>FILE_BOUND)return;
        try(BufferedReader input=new BufferedReader(new InputStreamReader(
                new FileInputStream(f),StandardCharsets.US_ASCII))){
            String line;
            int count=0;
            while((line=input.readLine())!=null&&count++<800){
                if(line.length()<15||line.length()>450||line.charAt(13)!='|')continue;
                boolean stamp=true;
                for(int j=0;j<13;j++){
                    if(line.charAt(j)<'0'||line.charAt(j)>'9'){stamp=false;break;}
                }
                String event=line.substring(14);
                if(stamp&&RootDiagnosticReceipt.safeEventToken(event))
                    into.add(line);
                else if(stamp&&event.startsWith("NATIVE_M4_DIAG ")){
                    String prefix="V4_PUBLIC_ANDROID_M4_DIAG role=client ";
                    String original=prefix+event.substring("NATIVE_M4_DIAG ".length());
                    if(RootDiagnosticReceipt.safeNativeSnapshot(original))debug.add(line);
                }
            }
        }catch(Exception ignored){
            // Read-only diagnostic export must never affect live Root.
        }
    }
    private static boolean has(List<String> session,String event){
        for(String s:session)if(s.endsWith("|"+event))return true;
        return false;
    }
    private static String stage(List<String> session){
        if(session.isEmpty())return "NOT_STARTED";
        // A39: old 0-event reports gave no clue when on-device START was
        // rejected before Service. A UI tap is a real session boundary.
        if(has(session,"UI_START_DISPATCH_FAILED"))
            return "UI_START_SERVICE_DISPATCH_FAILED";
        if(has(session,"UI_START_VALIDATION_REJECTED"))
            return "UI_START_PRE_SERVICE_REJECTED";
        if(has(session,"UI_START_TAPPED")&&!has(session,"START_REQUESTED")){
            if(has(session,"UI_START_DISPATCHED"))
                return "UI_START_DISPATCHED_SERVICE_NOT_OBSERVED";
            return "UI_START_TAPPED_BEFORE_SERVICE";
        }
        if(has(session,"UI_OPENED")&&!has(session,"START_REQUESTED"))
            return "UI_OPEN_NO_START";
        if(has(session,"ROOT_RESTORE_COMPLETE"))return "ROOT_RESTORE_VERIFIED_OWNED_KERNEL_CLEAR";
        if(has(session,"ROOT_RESTORE_FAILED"))return "ROOT_RESTORE_FAILED_NO_GLOBAL_MUTATION";
        if(has(session,"ROOT_RESTORE_REFUSED_LIVE_OWNER"))return "ROOT_RESTORE_REFUSED_LIVE_OWNER";
        if(has(session,"ROOT_RESTORE_REQUESTED"))return "ROOT_RESTORE_REQUESTED_NOT_VERIFIED";
        // This is a last-proven-boundary classification, not an assumed
        // errno or a promise of physical network/TLS success.
        if(has(session,"START_DIAGNOSTIC_STAGES_V2")&&
           has(session,"ROOT_PROCESS_EXIT_NONZERO")){
            if(has(session,"ORIGINAL_GO_PARSE_FLAG_SYNTAX"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_FLAG_SYNTAX";
            if(has(session,"ORIGINAL_GO_PARSE_PASSWORD_FILE"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_PASSWORD_FILE";
            if(has(session,"ORIGINAL_GO_PARSE_ROUTE_KEY_FILE"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_ROUTE_KEY_FILE";
            if(has(session,"ORIGINAL_GO_PARSE_ROUTE_KEY_VALUE"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_ROUTE_KEY_VALUE";
            if(has(session,"ORIGINAL_GO_PARSE_INSTALLATION_ID"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_INSTALLATION_ID";
            if(has(session,"ORIGINAL_GO_PARSE_CN_GEOSITE_FILE"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_CN_GEOSITE_FILE";
            if(has(session,"ORIGINAL_GO_PARSE_TLS_CA_FILE"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_TLS_CA_FILE";
            if(has(session,"ORIGINAL_GO_PARSE_ALL_APP_EXCLUSIONS"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_ALL_APP_EXCLUSIONS";
            if(has(session,"ORIGINAL_GO_PARSE_ANDROID_NETWORK_SCOPE"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_ANDROID_NETWORK_SCOPE";
            if(has(session,"ORIGINAL_GO_PARSE_PEER_ADDRESS"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_PEER_ADDRESS";
            if(has(session,"ORIGINAL_GO_PARSE_REQUIRED_COLD_SETTINGS"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_REQUIRED_COLD_SETTINGS";
            if(has(session,"ORIGINAL_GO_PARSE_POLICY"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_POLICY";
            if(has(session,"ORIGINAL_GO_PARSE_OTHER"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_OTHER";
            if(has(session,"ORIGINAL_GO_ARGS_REJECTED"))
                return "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED";
            if(has(session,"ORIGINAL_GO_COLD_RST_GUARD_STOP_UNVERIFIED"))
                return "COLD_RST_GUARD_STOP_UNVERIFIED";
            for(String failure:new String[]{
                "ORIGINAL_GO_COLD_RST_GUARD_FAILED_SCOPE_CONFLICT",
                "ORIGINAL_GO_COLD_RST_GUARD_FAILED_OWNER_LOCKED",
                "ORIGINAL_GO_COLD_RST_GUARD_FAILED_JOURNAL_UNSAFE",
                "ORIGINAL_GO_COLD_RST_GUARD_FAILED_READBACK_MISMATCH",
                "ORIGINAL_GO_COLD_RST_GUARD_FAILED_CLEANUP_UNVERIFIED",
                "ORIGINAL_GO_COLD_RST_GUARD_FAILED_IPTABLES_UNAVAILABLE"
            }){
                if(has(session,failure))return failure;
            }
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_FAILED_TIMEOUT"))
                return "TLS_HANDSHAKE_FAILED_TIMEOUT";
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CERTIFICATE"))
                return "TLS_HANDSHAKE_FAILED_CERTIFICATE";
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_FAILED_PEER_CLOSED"))
                return "TLS_HANDSHAKE_FAILED_PEER_CLOSED";
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_FAILED_DEADLINE_ELAPSED_OTHER"))
                return "TLS_HANDSHAKE_FAILED_DEADLINE_ELAPSED_OTHER";
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CANCELLED"))
                return "TLS_HANDSHAKE_FAILED_CANCELLED";
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_FAILED_BOOTSTRAP_CLOSED"))
                return "TLS_HANDSHAKE_FAILED_BOOTSTRAP_CLOSED";
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER"))
                return "TLS_HANDSHAKE_FAILED_OTHER";
            if(has(session,"ORIGINAL_GO_PROTECTED_REPLY_FAILED_AUTH_REJECTED"))
                return "PROTECTED_REPLY_FAILED_AUTH_REJECTED";
            if(has(session,"ORIGINAL_GO_PROTECTED_REPLY_FAILED_VERSION_REJECTED"))
                return "PROTECTED_REPLY_FAILED_VERSION_REJECTED";
            if(has(session,"ORIGINAL_GO_PROTECTED_REPLY_FAILED_TIMEOUT"))
                return "PROTECTED_REPLY_FAILED_TIMEOUT";
            if(has(session,"ORIGINAL_GO_PROTECTED_REPLY_FAILED_PEER_CLOSED"))
                return "PROTECTED_REPLY_FAILED_PEER_CLOSED";
            if(has(session,"ORIGINAL_GO_PROTECTED_REPLY_FAILED_POLICY_REJECTED"))
                return "PROTECTED_REPLY_FAILED_POLICY_REJECTED";
            if(has(session,"ORIGINAL_GO_PROTECTED_REPLY_FAILED_OTHER"))
                return "PROTECTED_REPLY_FAILED_OTHER";
            if(has(session,"ORIGINAL_GO_PROTECTED_REQUEST_WRITE_FAILED"))
                return "PROTECTED_REQUEST_WRITE_FAILED";
            if(has(session,"ORIGINAL_GO_COLD_PRODUCT_FAILED"))
                return "COLD_PRODUCT_PRE_TLS_FAILED";
            for(String failure:new String[]{
                "ORIGINAL_GO_POSTAUTH_COLD_FAILED",
                "ORIGINAL_GO_POSTAUTH_DETACH_FAILED",
                "ORIGINAL_GO_POSTAUTH_NATIVE_PREPARE_FAILED",
                "ORIGINAL_GO_POSTAUTH_NATIVE_COMMIT_FAILED",
                "ORIGINAL_GO_POSTAUTH_NATIVE_OTHER_FAILED",
                "ORIGINAL_GO_POSTAUTH_LEASE_FIELD_FAILED",
                "ORIGINAL_GO_POSTAUTH_LEASE_ADD_FAILED",
                "ORIGINAL_GO_POSTAUTH_LEASE_DEL_FAILED",
                "ORIGINAL_GO_POSTAUTH_LEASE_READBACK_FAILED",
                "ORIGINAL_GO_POSTAUTH_LEASE_MISMATCH",
                "ORIGINAL_GO_POSTAUTH_LEASE_OS_FAILED",
                "ORIGINAL_GO_POSTAUTH_NATIVE_IP_BIND_FAILED",
                "ORIGINAL_GO_POSTAUTH_MTU_FAILED",
                "ORIGINAL_GO_POSTAUTH_UNDERLAY_FAILED",
                "ORIGINAL_GO_POSTAUTH_RAW_FAILED",
                "ORIGINAL_GO_POSTAUTH_TUN_FAILED",
                "ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_FAILED",
                "ORIGINAL_GO_POSTAUTH_HEALTH_FAILED",
                "ORIGINAL_GO_POSTAUTH_M4_START_FAILED",
                "ORIGINAL_GO_POSTAUTH_UID_ROUTE_FAILED",
                "ORIGINAL_GO_POSTAUTH_COLD_RTO_STOP_FAILED",
                "ORIGINAL_GO_POSTAUTH_DETACH_STATE_FAILED",
                "ORIGINAL_GO_POSTAUTH_GO_RX_FILTER_FAILED",
            }){
                if(has(session,failure))return failure;
            }
            for(String done:new String[]{
                "ORIGINAL_GO_POSTAUTH_UID_ROUTE_ENTERED",
                "ORIGINAL_GO_POSTAUTH_GO_RX_HANDOFF_OK",
                "ORIGINAL_GO_POSTAUTH_GO_RX_FILTER_OK",
                "ORIGINAL_GO_POSTAUTH_M4_STARTED",
                "ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_ENABLED",
                "ORIGINAL_GO_POSTAUTH_TUN_ATTACHED",
                "ORIGINAL_GO_POSTAUTH_RAW_ATTACHED",
                "ORIGINAL_GO_POSTAUTH_UNDERLAY_OK",
                "ORIGINAL_GO_POSTAUTH_NATIVE_IP_BOUND",
                "ORIGINAL_GO_POSTAUTH_LEASE_OS_OK",
                "ORIGINAL_GO_POSTAUTH_LEASE_FIELD_OK",
                "ORIGINAL_GO_POSTAUTH_NATIVE_COMMIT_OK",
                "ORIGINAL_GO_POSTAUTH_DETACH_OK",
                "ORIGINAL_GO_POSTAUTH_COLD_OK",
            }){
                if(has(session,done))return done+"_NEXT_STAGE_UNPROVEN";
            }
            if(has(session,"ORIGINAL_GO_ADMISSION_VERIFIED"))
                return "PROTECTED_ADMISSION_VERIFIED_LEASE_UNPROVEN";
            if(has(session,"ORIGINAL_GO_PROTECTED_REPLY_PARSED"))
                return "PROTECTED_REPLY_PARSED_VERIFICATION_UNPROVEN";
            if(has(session,"ORIGINAL_GO_PROTECTED_REQUEST_WRITE_OK"))
                return "PROTECTED_REQUEST_WRITTEN_REPLY_UNPROVEN";
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED"))
                return "TLS_VERIFIED_ADMISSION_UNPROVEN";
            if(has(session,"ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED"))
                return "TLS_HANDSHAKE_ATTEMPTED_RESULT_UNPROVEN";
            if(has(session,"ORIGINAL_GO_COLD_PRODUCT_PREPARED"))
                return "COLD_PRODUCT_PREPARED_TLS_UNPROVEN";
            if(has(session,"ORIGINAL_GO_ASSOC_ESTABLISHED"))
                return "FAKETCP_ASSOC_ESTABLISHED_TLS_UNPROVEN";
            if(has(session,"ORIGINAL_GO_TCP_SYNACK_SEEN"))
                return "SYNACK_CANDIDATE_ASSOC_NOT_PROVEN";
            if(has(session,"ORIGINAL_GO_COLD_SYN_TX_OK"))
                return "SYN_SENDTO_ONLY_PEER_SYNACK_UNPROVEN";
            if(has(session,"ORIGINAL_GO_RAW_SOCKET_READY"))
                return "ORIGINAL_GO_RAW_BEFORE_SYNACK";
            if(has(session,"ORIGINAL_GO_TUN_OPENED"))
                return "ORIGINAL_GO_TUN_OPENED_CONFIG_BEFORE_RAW";
            if(has(session,"ORIGINAL_GO_TUN_OPEN_ATTEMPTED"))
                return "ORIGINAL_GO_TUN_OPEN_FAILED_OR_UNCONFIRMED";
            if(has(session,"ORIGINAL_GO_INTERFACE_FOUND"))
                return "ORIGINAL_GO_INTERFACE_FOUND_PRE_BUDGET_OR_DNS";
            if(has(session,"ORIGINAL_GO_ARGS_ACCEPTED"))
                return "ORIGINAL_GO_ARGS_ACCEPTED_PRE_INTERFACE";
            if(has(session,"ORIGINAL_GO_ENTRY"))
                return "ORIGINAL_GO_ENTRY_PRE_ARGS_ACCEPTANCE";
            if(has(session,"ROOT_SHELL_EXEC_ATTEMPTED"))
                return "ROOT_EXEC_ATTEMPTED_NO_GO_ENTRY_OR_LOADER";
            if(has(session,"ROOT_SHELL_OWNER_PID_WRITTEN"))
                return "ROOT_OWNER_RECORD_WRITTEN_PRE_EXEC";
            if(has(session,"ROOT_SHELL_NATIVE_FILES_STAGED"))
                return "ROOT_NATIVE_STAGED_OWNER_RECORD_UNVERIFIED";
            if(has(session,"ROOT_SHELL_OWNER_GUARD_PASSED"))
                return "ROOT_NATIVE_BINARY_STAGE_UNVERIFIED";
            if(has(session,"ROOT_SHELL_PRIVATE_DIR_VERIFIED"))
                return "ROOT_PREVIOUS_OWNER_GUARD_UNVERIFIED";
            if(has(session,"ROOT_SHELL_ROOT_UID_VERIFIED"))
                return "ROOT_PRIVATE_DIRECTORY_VERIFICATION_FAILED_OR_UNCONFIRMED";
            if(has(session,"ROOT_SHELL_ENTERED"))
                return "SU_ENTERED_BUT_ROOT_UID_UNVERIFIED";
            if(has(session,"ROOT_PROCESS_LAUNCHED"))
                return "SU_SUBPROCESS_STARTED_COMMAND_NOT_REACHED";
        }
        if(has(session,"APP_PRIVATE_CREDENTIALS_UNSAFE"))
            return "APP_PRIVATE_CREDENTIAL_FILE_0600_OR_SOURCE_REJECTED";
        if(has(session,"STOP_REQUESTED")&&!has(session,"ORIGINAL_GO_RUST_STOP_JOINED"))
            return "STOP_JOIN_NOT_PROVEN";
        if(has(session,"NATIVE_M4_AND_UID_READY"))
            return "NATIVE_UID_READY_BUT_APP_TRAFFIC_UNVERIFIED";
        if(has(session,"AUTHENTICATED_LEASE_OS_READBACK"))
            return "LEASE_APPLIED_M4_UID_UNPROVEN";
        if(has(session,"ORIGINAL_GO_TCP_SYNACK_SEEN"))
            return "SYNACK_OBSERVED_TLS_LEASE_UNPROVEN";
        if(has(session,"ORIGINAL_GO_COLD_SYN_TX_OK"))
            return "SYN_SENDTO_ONLY_PEER_SYNACK_UNPROVEN";
        if(has(session,"ORIGINAL_GO_RAW_SOCKET_READY"))
            return "ORIGINAL_GO_RAW_BEFORE_SYNACK";
        if(has(session,"ROOT_PROCESS_LAUNCHED"))
            return "ROOT_PROCESS_BEFORE_RAW_OR_GRANT_UNPROVEN";
        if(has(session,"START_REFUSED")||has(session,"ROOT_LAUNCH_FAILED"))
            return "APP_OR_ROOT_START_REFUSED";
        return "APP_PRE_NATIVE";
    }
    static String build(File appFilesDir,String source,int sdk){
        if(appFilesDir==null)throw new IllegalArgumentException("missing app files");
        ArrayList<String> events=new ArrayList<>();
        ArrayList<String> rawDebug=new ArrayList<>();
        appendSafe(new File(appFilesDir,"wbd-root-diagnostic.txt.previous"),events,rawDebug);
        appendSafe(new File(appFilesDir,"wbd-root-diagnostic.txt"),events,rawDebug);
        int start=0;
        for(int i=0;i<events.size();i++){
            if(events.get(i).endsWith("|START_REQUESTED")||
               events.get(i).endsWith("|UI_START_TAPPED"))start=i;
        }
        List<String> session=events.subList(start,events.size());
        boolean peer=has(session,"SERVER_PEER_THROW_PRIVATE_FIB_READBACK");
        StringBuilder out=new StringBuilder(18000);
        out.append("WBD_ANDROID_ROOT_SAFE_DIAGNOSTIC_V1\n");
        out.append("source=").append(validSource(source)?source:"UNAVAILABLE").append('\n');
        out.append("android_api=").append(sdk>=28&&sdk<=200?sdk:"UNAVAILABLE").append('\n');
        out.append("proxy_scope=ORDINARY_APP_IPV4_UID_ONLY_NOT_SYSTEM_IPV6_OR_SYSTEM_DNS\n");
        out.append("server_ip_exclusion=PRIVATE_TABLE_THROW32_REQUIRED_ALL_APPS\n");
        out.append("server_ip_exclusion_readback=").append(peer?"OBSERVED_PRIVATE_FIB_ONLY":"NOT_OBSERVED").append('\n');
        out.append("last_session_stage=").append(stage(session)).append('\n');
        // Real Go logs TUNNEL_DNS_ENABLED only after original Rust cold
        // effective readback returned 1; this is not system netd capture or
        // observed successful DNS request/answer delivery.
        String tunnelDNS=has(session,"ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_FAILED")
            ?"COLD_NATIVE_GRANT_FAILED":
             has(session,"ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_ENABLED")
            ?"RUST_COLD_ENABLED_APP_TUN_UDP53_ONLY":
             "NOT_OBSERVED";
        out.append("tunnel_dns_native_cold=").append(tunnelDNS).append('\n');
        out.append("device_real_business_tcp_udp=NOT_PROVEN_BY_THIS_REPORT\n");
        out.append("android_netd_physical_bypass=NOT_PROVEN_BY_THIS_REPORT\n");
        out.append("receipt_event_count=").append(events.size()).append('\n');
        out.append("events_timestamp_ms_and_fixed_stage_only:\n");
        int from=Math.max(0,events.size()-MAX_LINES);
        for(int i=from;i<events.size();i++)out.append(events.get(i)).append('\n');
        out.append("native_m4_numeric_debug_count=").append(rawDebug.size()).append('\n');
        out.append("native_m4_numeric_debug_samples:\n");
        int debugStart=Math.max(0,rawDebug.size()-MAX_NATIVE_DEBUG);
        for(int i=debugStart;i<rawDebug.size();i++)
            out.append(rawDebug.get(i)).append('\n');
        out.append("END_OF_SAFE_DIAGNOSTIC\n");
        return out.toString();
    }
}
