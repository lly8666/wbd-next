package org.wbdnext.rootclient;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * App-private, bounded, credential-free native Root acceptance evidence.
 *
 * The only serializable values are fixed enum constants and a millisecond
 * timestamp. In particular: never write root generation tokens, usernames,
 * IPs, app package names, route keys, TLS errors or raw native stdout.
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
        ORIGINAL_GO_POSTAUTH_M4_STARTED,
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
        ORIGINAL_GO_POSTAUTH_HEALTH_FAILED,
        ORIGINAL_GO_POSTAUTH_M4_START_FAILED,
        ORIGINAL_GO_POSTAUTH_UID_ROUTE_FAILED,
        ROOT_GRANT_REQUESTED,
        ROOT_PROCESS_LAUNCHED,
        NATIVE_M4_RECEIPT,
        UID_ROUTE_RECEIPT,
        NATIVE_M4_AND_UID_READY,
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
        OWNER_CLEANUP_FINISHED
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
        if(line.length>128)return false;
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
