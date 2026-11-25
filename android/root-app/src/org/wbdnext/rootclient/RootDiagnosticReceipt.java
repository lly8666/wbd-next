package org.wbdnext.rootclient;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * App-private, bounded, credential-free native Root acceptance evidence.
 *
 * V1 stages remain fixed enum constants. A47 additionally allows only
 * explicitly ordered numeric original-Rust RAW IPv4 header diagnostics.
 * These may include numeric IPv4 endpoints and ports at user request:
 * never write credentials, tokens, TLS payload or unfiltered native stdout.
 * Diagnostics are advisory; IO errors must NOT affect original Go/Rust Stop.
 *
 * No Android framework dependency: the exact writer is host-unit-tested
 * and compiled into the official signed ARM64 Root APK.
 */
final class RootDiagnosticReceipt {
    enum Event {
        // UI-side V1: captures START failures before RootClientService exists.
        UI_OPENED,
        UI_CREDENTIAL_LOAD_FAILED,
        UI_START_TAPPED,
        UI_CREDENTIAL_SAVE_FAILED,
        UI_START_VALIDATION_REJECTED,
        UI_START_DISPATCH_REQUESTED,
        UI_START_DISPATCHED,
        UI_START_DISPATCH_FAILED,
        START_REQUESTED,
        START_DIAGNOSTIC_STAGES_V2,
        ROOT_SHELL_ENTERED,
        ROOT_SHELL_ROOT_UID_VERIFIED,
        ROOT_SHELL_PRIVATE_DIR_VERIFIED,
        ROOT_SHELL_OWNER_GUARD_PASSED,
        ROOT_SHELL_NATIVE_FILES_STAGED,
        ROOT_SHELL_OWNER_PID_WRITTEN,
        ROOT_SHELL_EXEC_ATTEMPTED,
        ORIGINAL_GO_ENTRY,
        ORIGINAL_GO_ARGS_REJECTED,
        ORIGINAL_GO_PARSE_FLAG_SYNTAX,
        ORIGINAL_GO_PARSE_PASSWORD_FILE,
        ORIGINAL_GO_PARSE_ROUTE_KEY_FILE,
        ORIGINAL_GO_PARSE_ROUTE_KEY_VALUE,
        ORIGINAL_GO_PARSE_INSTALLATION_ID,
        ORIGINAL_GO_PARSE_CN_GEOSITE_FILE,
        ORIGINAL_GO_PARSE_TLS_CA_FILE,
        ORIGINAL_GO_PARSE_ALL_APP_EXCLUSIONS,
        ORIGINAL_GO_PARSE_ANDROID_NETWORK_SCOPE,
        ORIGINAL_GO_PARSE_PEER_ADDRESS,
        ORIGINAL_GO_PARSE_REQUIRED_COLD_SETTINGS,
        ORIGINAL_GO_PARSE_POLICY,
        ORIGINAL_GO_PARSE_OTHER,
        ORIGINAL_GO_ARGS_ACCEPTED,
        ORIGINAL_GO_MODE_READBACK_MATCHED,
        ORIGINAL_GO_INTERFACE_FOUND,
        ORIGINAL_GO_TUN_OPEN_ATTEMPTED,
        ORIGINAL_GO_TUN_OPENED,
        // Actual app-owned secret file lstat readback before su, never
        // credential text, path, mode value, uid, PID or SELinux label.
        APP_PRIVATE_CREDENTIALS_0600_VERIFIED,
        APP_PRIVATE_CREDENTIALS_UNSAFE,
        NETWORK_SCOPE_VERIFIED,
        APP_UID_GROUP_VERIFIED,
        ROOT_STAGE_REQUESTED,
        NATIVE_SOURCE_VERIFIED,
        ORIGINAL_GO_TUN_KERNEL_CONFIGURED,
        ORIGINAL_GO_RAW_SOCKET_READY,
        // Exact original Go syscall result from ClientAssociation.Start();
        // never peer authentication, TLS or data-plane success by itself.
        ORIGINAL_GO_COLD_SYN_TX_OK,
        ORIGINAL_GO_COLD_SYN_TX_PERMISSION_DENIED,
        ORIGINAL_GO_COLD_SYN_TX_NETWORK_UNREACHABLE,
        ORIGINAL_GO_COLD_SYN_TX_INVALID_ARGUMENT,
        ORIGINAL_GO_COLD_SYN_TX_SOURCE_UNAVAILABLE,
        ORIGINAL_GO_COLD_SYN_TX_BUFFER_PRESSURE,
        ORIGINAL_GO_COLD_SYN_TX_OTHER_FAILURE,
        ORIGINAL_GO_COLD_UNAUTH_RST_RX,
        ORIGINAL_GO_TCP_SYNACK_SEEN, // raw filtered candidate, not ClientAssociation acceptance
        // A33 real native cold ownership stages; fixed only and never TLS content.
        ORIGINAL_GO_ASSOC_ESTABLISHED,
        ORIGINAL_GO_COLD_PRODUCT_FAILED,
        ORIGINAL_GO_COLD_PRODUCT_PREPARED,
        ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED,
        ORIGINAL_GO_TLS_HANDSHAKE_FAILED_TIMEOUT,
        ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CERTIFICATE,
        ORIGINAL_GO_TLS_CERT_REASON_UNKNOWN_AUTHORITY,
        ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH,
        ORIGINAL_GO_TLS_CERT_REASON_EXPIRED,
        ORIGINAL_GO_TLS_CERT_REASON_NOT_YET_VALID,
        ORIGINAL_GO_TLS_CERT_REASON_INCOMPATIBLE_USAGE,
        ORIGINAL_GO_TLS_CERT_REASON_INVALID_CERTIFICATE,
        ORIGINAL_GO_TLS_CERT_REASON_OTHER_CERTIFICATE,
        ORIGINAL_GO_TLS_CERT_VERIFY_DISABLED,
        ORIGINAL_GO_TLS_CERT_VERIFY_ENABLED,
        ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_DISABLED,
        ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_ENABLED,
        ORIGINAL_GO_TLS_TRUST_SOURCE_OS_STORE,
        ORIGINAL_GO_TLS_TRUST_SOURCE_APP_PEM,
        ORIGINAL_GO_TLS_HANDSHAKE_FAILED_PEER_CLOSED,
        ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER,
        // A34 original FakeTCP bootstrap/RAW and TLS deadline observation.
        ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_OK,
        // A35 exact-root owned, journal-first Android original FakeTCP RST guard.
        ORIGINAL_GO_COLD_RST_GUARD_READY,
        ORIGINAL_GO_COLD_RST_GUARD_RECOVERED,
        ORIGINAL_GO_COLD_RST_GUARD_MATCHED_RST_DROP,
        ORIGINAL_GO_COLD_RST_GUARD_NO_RST_DROP,
        ORIGINAL_GO_COLD_RST_GUARD_COUNTER_UNAVAILABLE,
        ORIGINAL_GO_COLD_RST_GUARD_STOP_CLEARED,
        ORIGINAL_GO_COLD_RST_GUARD_STOP_UNVERIFIED,
        ORIGINAL_GO_COLD_RST_GUARD_FAILED_SCOPE_CONFLICT,
        ORIGINAL_GO_COLD_RST_GUARD_FAILED_OWNER_LOCKED,
        ORIGINAL_GO_COLD_RST_GUARD_FAILED_JOURNAL_UNSAFE,
        ORIGINAL_GO_COLD_RST_GUARD_FAILED_READBACK_MISMATCH,
        ORIGINAL_GO_COLD_RST_GUARD_FAILED_CLEANUP_UNVERIFIED,
        ORIGINAL_GO_COLD_RST_GUARD_FAILED_IPTABLES_UNAVAILABLE,
        ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX,
        ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_NOT_OBSERVED,
        ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX_NOT_OBSERVED,
        ORIGINAL_GO_COLD_BOOTSTRAP_RTO_OBSERVED,
        ORIGINAL_GO_TLS_HANDSHAKE_FAILED_DEADLINE_ELAPSED_OTHER,
        ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CANCELLED,
        ORIGINAL_GO_TLS_HANDSHAKE_FAILED_BOOTSTRAP_CLOSED,
        ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED,
        ORIGINAL_GO_PROTECTED_REQUEST_WRITE_FAILED,
        ORIGINAL_GO_PROTECTED_REQUEST_WRITE_OK,
        ORIGINAL_GO_PROTECTED_REPLY_FAILED_TIMEOUT,
        ORIGINAL_GO_PROTECTED_REPLY_FAILED_AUTH_REJECTED,
        ORIGINAL_GO_PROTECTED_REPLY_FAILED_VERSION_REJECTED,
        ORIGINAL_GO_PROTECTED_REPLY_FAILED_PEER_CLOSED,
        ORIGINAL_GO_PROTECTED_REPLY_FAILED_POLICY_REJECTED,
        ORIGINAL_GO_PROTECTED_REPLY_FAILED_OTHER,
        ORIGINAL_GO_PROTECTED_REPLY_PARSED,
        ORIGINAL_GO_ADMISSION_VERIFIED,
        ORIGINAL_GO_POSTAUTH_COLD_OK,
        ORIGINAL_GO_POSTAUTH_DETACH_OK,
        ORIGINAL_GO_POSTAUTH_NATIVE_COMMIT_OK,
        ORIGINAL_GO_POSTAUTH_LEASE_FIELD_OK,
        ORIGINAL_GO_POSTAUTH_LEASE_OS_OK,
        ORIGINAL_GO_POSTAUTH_NATIVE_IP_BOUND,
        ORIGINAL_GO_POSTAUTH_UNDERLAY_OK,
        ORIGINAL_GO_POSTAUTH_RAW_ATTACHED,
        ORIGINAL_GO_POSTAUTH_TUN_ATTACHED,
        // B3: native Rust ABI cold readback of the original authenticated
        // one-reader tunnel-UDP DNS subfeature, not Android netd Resolver.
        ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_ENABLED,
        ORIGINAL_GO_POSTAUTH_M4_STARTED,
        ORIGINAL_GO_POSTAUTH_COLD_RTO_STOP_FAILED,
        ORIGINAL_GO_POSTAUTH_DETACH_STATE_FAILED,
        ORIGINAL_GO_POSTAUTH_GO_RX_FILTER_FAILED,
        ORIGINAL_GO_POSTAUTH_GO_RX_FILTER_OK,
        ORIGINAL_GO_POSTAUTH_GO_RX_HANDOFF_OK,
        ORIGINAL_GO_POSTAUTH_UID_ROUTE_ENTERED,
        ORIGINAL_GO_POSTAUTH_COLD_FAILED,
        ORIGINAL_GO_POSTAUTH_DETACH_FAILED,
        ORIGINAL_GO_POSTAUTH_NATIVE_PREPARE_FAILED,
        ORIGINAL_GO_POSTAUTH_NATIVE_COMMIT_FAILED,
        ORIGINAL_GO_POSTAUTH_NATIVE_OTHER_FAILED,
        ORIGINAL_GO_POSTAUTH_LEASE_FIELD_FAILED,
        ORIGINAL_GO_POSTAUTH_LEASE_ADD_FAILED,
        ORIGINAL_GO_POSTAUTH_LEASE_DEL_FAILED,
        ORIGINAL_GO_POSTAUTH_LEASE_READBACK_FAILED,
        ORIGINAL_GO_POSTAUTH_LEASE_MISMATCH,
        ORIGINAL_GO_POSTAUTH_LEASE_OS_FAILED,
        ORIGINAL_GO_POSTAUTH_NATIVE_IP_BIND_FAILED,
        ORIGINAL_GO_POSTAUTH_MTU_FAILED,
        ORIGINAL_GO_POSTAUTH_UNDERLAY_FAILED,
        ORIGINAL_GO_POSTAUTH_RAW_FAILED,
        ORIGINAL_GO_POSTAUTH_TUN_FAILED,
        ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_FAILED,
        ORIGINAL_GO_POSTAUTH_PHYSICAL_DNS_ENABLED,
        ORIGINAL_GO_POSTAUTH_PHYSICAL_DNS_FAILED,
        ORIGINAL_GO_POSTAUTH_CN_DNS_SPLIT_ENABLED,
        ORIGINAL_GO_POSTAUTH_CN_DNS_SPLIT_FAILED,
        ORIGINAL_GO_POSTAUTH_HEALTH_FAILED,
        ORIGINAL_GO_POSTAUTH_M4_START_FAILED,
        ORIGINAL_GO_POSTAUTH_UID_ROUTE_FAILED,
        ROOT_GRANT_REQUESTED,
        ROOT_PROCESS_LAUNCHED,
        ORIGINAL_FEC_RECOVERED_TUN_OBSERVED,
        ORIGINAL_GAME_FEC_RECOVERED_CANDIDATE_OBSERVED,
        NATIVE_M4_RECEIPT,
        UID_ROUTE_RECEIPT,
        NATIVE_M4_AND_UID_READY,
        ORIGINAL_RUST_TUN_IPV4_SEEN,
        ORIGINAL_RUST_TUN_IPV4_REJECTED,
        ORIGINAL_RUST_APP_RAW_TX_COPIED,
        ORIGINAL_RUST_APP_REVERSE_TUN_WRITTEN,
        ORIGINAL_RUST_DNS_UDP53_TUN_SEEN,
        ORIGINAL_RUST_DNS_TCP53_TUN_SEEN,
        ORIGINAL_RUST_DNS_TUNNEL_RAW_COPIED,
        ORIGINAL_RUST_DNS_TUNNEL_REVERSE_TUN_WRITTEN,
        ORIGINAL_RUST_DNS_PHYSICAL_UDP_COPIED,
        ORIGINAL_RUST_DNS_PHYSICAL_REVERSE_TUN_WRITTEN,
        ORIGINAL_RUST_DNS_PHYSICAL_ERROR,
        ORIGINAL_RUST_DNS_CN_PHYSICAL_SENT,
        ORIGINAL_RUST_DNS_NONCN_TUNNEL_RAW_COPIED,
        ORIGINAL_RUST_DNS_TCP53_ORIGINAL_RAW_COPIED,
        ORIGINAL_RUST_DNS_PHYSICAL_TC_REPLY_TUN_WRITTEN,
        ORIGINAL_RUST_RAW_SOCKET_READABLE,
        ORIGINAL_RUST_RAW_PARSE_FAILED,
        ORIGINAL_RUST_RAW_PARSED,
        ORIGINAL_RUST_RAW_AUTHENTICATED,
        ORIGINAL_RUST_RAW_AUTH_REJECTED,
        ORIGINAL_RUST_REVERSE_TUN_WRITE_FAILED,
        ORIGINAL_RUST_TUN_ICMP_SEEN,
        ORIGINAL_RUST_TUN_TCP_SEEN,
        ORIGINAL_RUST_TUN_UDP_SEEN,
        ORIGINAL_GO_UID_ROUTE_GET_MATCHED_TUN,
        ORIGINAL_GO_UID_ROUTE_GET_MISMATCH,
        ORIGINAL_GO_UID_ROUTE_GET_UNAVAILABLE,
        AUTHENTICATED_LEASE_OS_READBACK,
        ORIGINAL_GO_RUST_HANDOFF,
        ORIGINAL_GO_UID_ROUTE_STOP_DRAINED,
        ORIGINAL_GO_RUST_STOP_JOINED,
        ROOT_PROCESS_EXIT_1,
        ROOT_PROCESS_EXIT_139,
        ROOT_PROCESS_EXIT_132,
        ROOT_PROCESS_EXIT_ZERO,
        ROOT_PROCESS_EXIT_NONZERO,
        ROOT_LAUNCH_FAILED,
        START_REFUSED,
        START_FAILED_EXACT_NETWORK,
        START_FAILED_UID_SCOPE,
        ROUTE_SCOPE_ALL_ORDINARY_APPS_IPV4,
        ROUTE_SCOPE_SELECTED_APPS_IPV4,
        // The kernel private-table /32 throw was read back. This is NOT
        // proof that later Android netd routed packets to physical Wi-Fi.
        SERVER_PEER_THROW_PRIVATE_FIB_READBACK,
        ROOT_EXIT_BEFORE_GO_RAW,
        ORIGINAL_GO_EXIT_BEFORE_PEER_SYNACK,
        // A36 explicit Root UI Restore-only fixed events.
        ROOT_RESTORE_REQUESTED,
        ROOT_RESTORE_ROUTE_CLEARED,
        ROOT_RESTORE_RST_CLEARED,
        ROOT_RESTORE_COMPLETE,
        ROOT_RESTORE_FAILED,
        ROOT_RESTORE_REFUSED_LIVE_OWNER,
        STOP_REQUESTED,
        STOP_SIGNAL_STARTED,
        STOP_SIGNAL_ACCEPTED,
        STOP_SIGNAL_REFUSED,
        STOP_SIGNAL_ERROR,
        ORIGINAL_GO_GAME_NATIVE_READY,
        ORIGINAL_GO_GAME_GROUP_STOP_JOINED,
        ORIGINAL_GO_COLD_RESELECT_STOP_CONFIRMED,
        OWNER_CLEANUP_FINISHED
    }

    // A47: numeric-only forensic snapshots from the original native M4;
    // exhaustive field/order allowlist blocks native stderr/credentials.
    private static final String[] RAW_KEYS={
        "read",
        "data",
        "ack",
        "tuple",
        "ipck",
        "tcpck",
        "flags",
        "len",
        "opts",
        "ttl0",
        "other",
        "seq",
        "offer",
        "recv_err",
        "lastlen",
        "lastttl",
        "lastflags",
        "src",
        "dst",
        "sport",
        "dport",
        "errno"
    };
    private static final String[] M4_KEYS={
        "poll",
        "parse_fail",
        "parsed",
        "auth",
        "rejected",
        "writefail",
        "tun",
        "trej",
        "rawtx",
        "rtun",
        "tcp",
        "udp",
        "icmp",
        "dnsudp",
        "dnstcp",
        "dnsraw",
        "dnsrtun",
        "dnsptx",
        "dnsprx",
        "dnsperr",
        "rxerr",
        "txerr",
        "health"
    };
    static boolean safeNativeSnapshot(String raw){
        if(raw==null||raw.length()>370||
           !raw.startsWith("V4_PUBLIC_ANDROID_M4_DIAG role=client kind="))return false;
        String body=raw.substring("V4_PUBLIC_ANDROID_M4_DIAG role=client ".length());
        String[] parts=body.split(" ",-1);
        if(parts.length==0)return false;
        String[] keys;
        if(parts[0].equals("kind=rx"))keys=RAW_KEYS;
        else if(parts[0].equals("kind=m4"))keys=M4_KEYS;
        else return false;
        // Preserve A47 and B3d reports across the B4 DNS metric addition.
        // Historical fields keep their exact order and are never invented.
        boolean oldM4=parts[0].equals("kind=m4")&&
            parts.length==M4_KEYS.length-4; // A47: five DNS counters absent
        boolean b3dM4=parts[0].equals("kind=m4")&&
            parts.length==M4_KEYS.length-2; // B3d: three physical absent
        if(parts.length!=keys.length+1&&!oldM4&&!b3dM4)return false;
        int field=1;
        for(int i=0;i<keys.length;i++){
            String key=keys[i];
            if((oldM4||b3dM4)&&(key.equals("dnsptx")||
                key.equals("dnsprx")||key.equals("dnsperr")))continue;
            if(oldM4&&(key.equals("dnsraw")||key.equals("dnsrtun")))continue;
            String prefix=key+"=";
            if(!parts[field].startsWith(prefix))return false;
            String digits=parts[field++].substring(prefix.length());
            if(digits.length()==0||digits.length()>20)return false;
            for(int j=0;j<digits.length();j++){
                char c=digits.charAt(j);
                if(c<'0'||c>'9')return false;
            }
        }
        return true;
    }
    synchronized boolean recordNativeSnapshot(String raw){
        if(!safeNativeSnapshot(raw))return false;
        final String body=raw.substring("V4_PUBLIC_ANDROID_M4_DIAG role=client ".length());
        return appendReceipt((Long.toString(System.currentTimeMillis())+
            "|NATIVE_M4_DIAG "+body+"\n").getBytes(StandardCharsets.US_ASCII),450);
    }
    // B6 is a separate additive receipt. Never change the historical
    // 18/20/23-number M4 wire accepted by A47/B3d/B4 report export.
    private static final String B6_PREFIX=
        "V4_PUBLIC_ANDROID_DNS_B6_DIAG role=client ";
    private static final String[] B6_KEYS={"cnptx","noncnraw","tcpraw","ptctun"};
    static boolean safeDNSB6Snapshot(String raw){
        if(raw==null||raw.length()>140||!raw.startsWith(B6_PREFIX))return false;
        String[] parts=raw.substring(B6_PREFIX.length()).split(" ",-1);
        if(parts.length!=B6_KEYS.length)return false;
        for(int i=0;i<parts.length;i++){
            String prefix=B6_KEYS[i]+"=";
            if(!parts[i].startsWith(prefix))return false;
            String digits=parts[i].substring(prefix.length());
            if(digits.isEmpty()||digits.length()>20)return false;
            for(int j=0;j<digits.length();j++){
                char c=digits.charAt(j);
                if(c<'0'||c>'9')return false;
            }
        }
        return true;
    }
    synchronized boolean recordDNSB6Snapshot(String raw){
        if(!safeDNSB6Snapshot(raw))return false;
        String body=raw.substring(B6_PREFIX.length());
        return appendReceipt((Long.toString(System.currentTimeMillis())+
            "|NATIVE_DNS_B6_DIAG "+body+"\n").getBytes(StandardCharsets.US_ASCII),230);
    }
    private static final int MAX_BYTES=16384;
    private final File current;

    RootDiagnosticReceipt(File file) {
        if(file==null)throw new IllegalArgumentException("missing receipt path");
        current=file;
    }

    synchronized boolean record(Event event) {
        if(event==null)throw new IllegalArgumentException("missing event");
        final byte[] line=(Long.toString(System.currentTimeMillis())+
            "|" + event.name() + "\n").getBytes(StandardCharsets.US_ASCII);
        return appendReceipt(line,128);
    }
    private boolean appendReceipt(byte[] line,int maxLine){
        if(line.length>maxLine)return false;
        File parent=current.getParentFile();
        if(parent==null||!parent.isDirectory())return false;
        try{
            if(current.length()+line.length>MAX_BYTES){
                File previous=new File(parent,current.getName()+".previous");
                if(previous.exists()&&!previous.delete())return false;
                if(!current.renameTo(previous))return false;
            }
            try(FileOutputStream out=new FileOutputStream(current,true)){
                if(!current.setReadable(false,false)||
                   !current.setWritable(false,false)||
                   !current.setReadable(true,true)||
                   !current.setWritable(true,true))return false;
                out.write(line);
                out.getFD().sync();
            }
            return true;
        }catch(IOException|SecurityException e){
            // Logging cannot become a source of Root startup/Stop failure.
            return false;
        }
    }

    static boolean safeEventToken(String token) {
        if(token==null)return false;
        for(Event e:Event.values())if(e.name().equals(token))return true;
        return false;
    }
}
