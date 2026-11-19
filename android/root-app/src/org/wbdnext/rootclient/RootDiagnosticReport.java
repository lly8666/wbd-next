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
 * Every event is exactly RootDiagnosticReceipt.Event; all other lines are
 * dropped before serialization. Host JVM tests run this SAME report builder.
 */
final class RootDiagnosticReport {
    private RootDiagnosticReport(){}
    private static final int FILE_BOUND=16384;
    private static final int MAX_LINES=180;
    private static boolean validSource(String s){
        if(s==null||s.length()!=40)return false;
        for(int i=0;i<s.length();i++){
            char c=s.charAt(i);
            if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;
        }
        return true;
    }
    private static void appendSafe(File f,List<String> into){
        if(!f.isFile()||f.length()<0||f.length()>FILE_BOUND)return;
        try(BufferedReader input=new BufferedReader(new InputStreamReader(
                new FileInputStream(f),StandardCharsets.US_ASCII))){
            String line;
            int count=0;
            while((line=input.readLine())!=null&&count++<800){
                if(line.length()<15||line.length()>128||line.charAt(13)!='|')continue;
                boolean stamp=true;
                for(int j=0;j<13;j++){
                    if(line.charAt(j)<'0'||line.charAt(j)>'9'){stamp=false;break;}
                }
                String event=line.substring(14);
                if(stamp&&RootDiagnosticReceipt.safeEventToken(event))
                    into.add(line);
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
        appendSafe(new File(appFilesDir,"wbd-root-diagnostic.txt.previous"),events);
        appendSafe(new File(appFilesDir,"wbd-root-diagnostic.txt"),events);
        int start=0;
        for(int i=0;i<events.size();i++){
            if(events.get(i).endsWith("|START_REQUESTED"))start=i;
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
        out.append("device_real_business_tcp_udp=NOT_PROVEN_BY_THIS_REPORT\n");
        out.append("android_netd_physical_bypass=NOT_PROVEN_BY_THIS_REPORT\n");
        out.append("receipt_event_count=").append(events.size()).append('\n');
        out.append("events_timestamp_ms_and_fixed_stage_only:\n");
        int from=Math.max(0,events.size()-MAX_LINES);
        for(int i=from;i<events.size();i++)out.append(events.get(i)).append('\n');
        out.append("END_OF_SAFE_DIAGNOSTIC\n");
        return out.toString();
    }
}
