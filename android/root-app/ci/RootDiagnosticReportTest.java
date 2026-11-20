package org.wbdnext.rootclient;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** Host execution of the production offline export. No network/Root. */
public final class RootDiagnosticReportTest {
    private static void contains(String report,String key){
        if(!report.contains(key))throw new AssertionError("missing "+key);
    }
    public static void main(String[] args)throws Exception{
        File dir=Files.createTempDirectory("wbd-export-test").toFile();
        RootDiagnosticReceipt wr=new RootDiagnosticReceipt(new File(dir,"wbd-root-diagnostic.txt"));
        String source="74d4442bc40c7452c89e96efc7658389d474c34c";
        String report=RootDiagnosticReport.build(dir,source,35);
        contains(report,"last_session_stage=NOT_STARTED");
        wr.record(RootDiagnosticReceipt.Event.START_REQUESTED);
        wr.record(RootDiagnosticReceipt.Event.ROUTE_SCOPE_ALL_ORDINARY_APPS_IPV4);
        wr.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_OK);
        report=RootDiagnosticReport.build(dir,source,35);
        contains(report,"SYN_SENDTO_ONLY_PEER_SYNACK_UNPROVEN");
        contains(report,"server_ip_exclusion_readback=NOT_OBSERVED");
        wr.record(RootDiagnosticReceipt.Event.SERVER_PEER_THROW_PRIVATE_FIB_READBACK);
        wr.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TCP_SYNACK_SEEN);
        report=RootDiagnosticReport.build(dir,source,35);
        contains(report,"SYNACK_OBSERVED_TLS_LEASE_UNPROVEN");
        contains(report,"server_ip_exclusion_readback=OBSERVED_PRIVATE_FIB_ONLY");
        // Attack-like untrusted log content is never exported.
        File file=new File(dir,"wbd-root-diagnostic.txt");
        Files.write(file.toPath(),(
            "1770000000000|START_REQUESTED\n"+
            "1770000000001|PASSWORD_SECRET=AAA DNS=203.0.113.45 USER=bob\n"+
            "1770000000002|ORIGINAL_GO_COLD_SYN_TX_OK\n"+
            "1770000000003|ROOT_PROCESS_EXIT_999\n").getBytes(StandardCharsets.UTF_8));
        report=RootDiagnosticReport.build(dir,"not-a-real-sha",35);
        contains(report,"source=UNAVAILABLE");
        contains(report,"SYN_SENDTO_ONLY_PEER_SYNACK_UNPROVEN");
        if(report.contains("203.0.113.45")||report.contains("USER=bob")||
           report.contains("PASSWORD_SECRET")||report.contains("ROOT_PROCESS_EXIT_999"))
            throw new AssertionError("untrusted native/secret line was exported");
        // Prior 16K safely rotated history is also supported.
        Files.move(file.toPath(),new File(dir,"wbd-root-diagnostic.txt.previous").toPath());
        wr.record(RootDiagnosticReceipt.Event.START_REQUESTED);
        wr.record(RootDiagnosticReceipt.Event.STOP_REQUESTED);
        report=RootDiagnosticReport.build(dir,source,35);
        contains(report,"STOP_JOIN_NOT_PROVEN");
        if(report.length()>24000)throw new AssertionError("export unbounded");
        // The user's real A29 first-device failure was 11 V1 events:
        // Native SOURCE verified, su subprocess started, exit1 before TUN.
        // It does NOT prove Go entry or TUN failure and must stay V1 unknown.
        File oldDir=Files.createTempDirectory("wbd-v1-stage").toFile();
        RootDiagnosticReceipt old=new RootDiagnosticReceipt(
            new File(oldDir,"wbd-root-diagnostic.txt"));
        for(RootDiagnosticReceipt.Event event:new RootDiagnosticReceipt.Event[]{
            RootDiagnosticReceipt.Event.START_REQUESTED,
            RootDiagnosticReceipt.Event.NETWORK_SCOPE_VERIFIED,
            RootDiagnosticReceipt.Event.APP_UID_GROUP_VERIFIED,
            RootDiagnosticReceipt.Event.ROUTE_SCOPE_ALL_ORDINARY_APPS_IPV4,
            RootDiagnosticReceipt.Event.ROOT_STAGE_REQUESTED,
            RootDiagnosticReceipt.Event.NATIVE_SOURCE_VERIFIED,
            RootDiagnosticReceipt.Event.ROOT_GRANT_REQUESTED,
            RootDiagnosticReceipt.Event.ROOT_PROCESS_LAUNCHED,
            RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO,
            RootDiagnosticReceipt.Event.ROOT_EXIT_BEFORE_GO_RAW,
            RootDiagnosticReceipt.Event.OWNER_CLEANUP_FINISHED}){
            old.record(event);
        }
        contains(RootDiagnosticReport.build(oldDir,source,36),
            "last_session_stage=ROOT_PROCESS_BEFORE_RAW_OR_GRANT_UNPROVEN");
        // For a new-source failure, classify EXACT last witnessed boundary,
        // not an inferred raw stdout error or a fictitious TLS/Root success.
        RootDiagnosticReceipt.Event[] reached={
            null,
            RootDiagnosticReceipt.Event.ROOT_SHELL_ENTERED,
            RootDiagnosticReceipt.Event.ROOT_SHELL_ROOT_UID_VERIFIED,
            RootDiagnosticReceipt.Event.ROOT_SHELL_PRIVATE_DIR_VERIFIED,
            RootDiagnosticReceipt.Event.ROOT_SHELL_OWNER_GUARD_PASSED,
            RootDiagnosticReceipt.Event.ROOT_SHELL_NATIVE_FILES_STAGED,
            RootDiagnosticReceipt.Event.ROOT_SHELL_OWNER_PID_WRITTEN,
            RootDiagnosticReceipt.Event.ROOT_SHELL_EXEC_ATTEMPTED,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_ACCEPTED,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_INTERFACE_FOUND,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_OPEN_ATTEMPTED,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_OPENED
        };
        String[] expected={
            "SU_SUBPROCESS_STARTED_COMMAND_NOT_REACHED",
            "SU_ENTERED_BUT_ROOT_UID_UNVERIFIED",
            "ROOT_PRIVATE_DIRECTORY_VERIFICATION_FAILED_OR_UNCONFIRMED",
            "ROOT_PREVIOUS_OWNER_GUARD_UNVERIFIED",
            "ROOT_NATIVE_BINARY_STAGE_UNVERIFIED",
            "ROOT_NATIVE_STAGED_OWNER_RECORD_UNVERIFIED",
            "ROOT_OWNER_RECORD_WRITTEN_PRE_EXEC",
            "ROOT_EXEC_ATTEMPTED_NO_GO_ENTRY_OR_LOADER",
            "ORIGINAL_GO_ENTRY_PRE_ARGS_ACCEPTANCE",
            "ORIGINAL_GO_ARGUMENT_PARSE_REJECTED",
            "ORIGINAL_GO_ARGS_ACCEPTED_PRE_INTERFACE",
            "ORIGINAL_GO_INTERFACE_FOUND_PRE_BUDGET_OR_DNS",
            "ORIGINAL_GO_TUN_OPEN_FAILED_OR_UNCONFIRMED",
            "ORIGINAL_GO_TUN_OPENED_CONFIG_BEFORE_RAW"
        };
        for(int i=0;i<reached.length;i++){
            File stageDir=Files.createTempDirectory("wbd-stage-fixture").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(stageDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_LAUNCHED);
            if(reached[i]!=null)w.record(reached[i]);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_1);
            String classified=RootDiagnosticReport.build(stageDir,source,36);
            contains(classified,"last_session_stage="+expected[i]);
            if(classified.contains("password")||classified.contains("route-key")||
               classified.contains("203.0.113.9")||classified.contains("username"))
                throw new AssertionError("secret leaked in fixed stage report");
        }
        // A31: API36 verified genuine Root and original Go ELF entry,
        // then actual original parse rejected. The next app receives one
        // of these controlled, non-secret error classes, never raw errors.

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_FLAG_SYNTAX);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_FLAG_SYNTAX");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_PASSWORD_FILE);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_PASSWORD_FILE");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_ROUTE_KEY_FILE);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_ROUTE_KEY_FILE");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_ROUTE_KEY_VALUE);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_ROUTE_KEY_VALUE");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_INSTALLATION_ID);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_INSTALLATION_ID");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_CN_GEOSITE_FILE);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_CN_GEOSITE_FILE");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_TLS_CA_FILE);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_TLS_CA_FILE");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_ALL_APP_EXCLUSIONS);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_ALL_APP_EXCLUSIONS");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_ANDROID_NETWORK_SCOPE);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_ANDROID_NETWORK_SCOPE");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_PEER_ADDRESS);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_PEER_ADDRESS");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_REQUIRED_COLD_SETTINGS);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_REQUIRED_COLD_SETTINGS");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_POLICY);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_POLICY");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }

        {
            File reasonDir=Files.createTempDirectory("wbd-a31-reason").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(reasonDir,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_OTHER);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String classified=RootDiagnosticReport.build(reasonDir,source,36);
            contains(classified,"last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_OTHER");
            if(classified.contains("203.0.113")||
               classified.contains("password=")||
               classified.contains("/data/user/"))
                throw new AssertionError("diagnostics leaked raw user input");
        }
        // This SOURCE adds classification, not a new retroactive verdict:
        // existing V2 generic events must keep their old generic label.
        {
            File dir3=Files.createTempDirectory("wbd-a30-generic").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(dir3,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            contains(RootDiagnosticReport.build(dir3,source,36),
                "last_session_stage=ORIGINAL_GO_ARGUMENT_PARSE_REJECTED");
        }
        // The Android API36 A31 original Go password-file rejection
        // now has a pre-su app fd + lstat 0600 safety gate.
        {
            File denied=Files.createTempDirectory("wbd-a32-unsafe").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(denied,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.APP_PRIVATE_CREDENTIALS_UNSAFE);
            w.record(RootDiagnosticReceipt.Event.ROOT_LAUNCH_FAILED);
            contains(RootDiagnosticReport.build(denied,source,36),
                "last_session_stage=APP_PRIVATE_CREDENTIAL_FILE_0600_OR_SOURCE_REJECTED");
            if(RootDiagnosticReport.build(denied,source,36).contains("wbd-pass.secret"))
                throw new AssertionError("secret file name leaked by rejection");
        }
        // A33: reproduce the user's actual A32 sequence, including TUN,
        // RAW, raw SYNACK candidate and nonzero exit. The former report
        // incorrectly stopped at TUN because its V2 failure block won.
        for(RootDiagnosticReceipt.Event[] diagnosticCase:new RootDiagnosticReceipt.Event[][]{
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_TCP_SYNACK_SEEN},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_ASSOC_ESTABLISHED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_PRODUCT_FAILED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_PRODUCT_PREPARED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_TIMEOUT},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CERTIFICATE},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_PEER_CLOSED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REQUEST_WRITE_FAILED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REQUEST_WRITE_OK},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_TIMEOUT},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_AUTH_REJECTED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_VERSION_REJECTED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_PEER_CLOSED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_POLICY_REJECTED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_OTHER},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_PARSED},
            {RootDiagnosticReceipt.Event.ORIGINAL_GO_ADMISSION_VERIFIED},
        }){
            RootDiagnosticReceipt.Event finalStage=diagnosticCase[0];
            String wantA33=null;
            switch(finalStage){
            case ORIGINAL_GO_TCP_SYNACK_SEEN: wantA33="SYNACK_CANDIDATE_ASSOC_NOT_PROVEN"; break;
            case ORIGINAL_GO_ASSOC_ESTABLISHED: wantA33="FAKETCP_ASSOC_ESTABLISHED_TLS_UNPROVEN"; break;
            case ORIGINAL_GO_COLD_PRODUCT_FAILED: wantA33="COLD_PRODUCT_PRE_TLS_FAILED"; break;
            case ORIGINAL_GO_COLD_PRODUCT_PREPARED: wantA33="COLD_PRODUCT_PREPARED_TLS_UNPROVEN"; break;
            case ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED: wantA33="TLS_HANDSHAKE_ATTEMPTED_RESULT_UNPROVEN"; break;
            case ORIGINAL_GO_TLS_HANDSHAKE_FAILED_TIMEOUT: wantA33="TLS_HANDSHAKE_FAILED_TIMEOUT"; break;
            case ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CERTIFICATE: wantA33="TLS_HANDSHAKE_FAILED_CERTIFICATE"; break;
            case ORIGINAL_GO_TLS_HANDSHAKE_FAILED_PEER_CLOSED: wantA33="TLS_HANDSHAKE_FAILED_PEER_CLOSED"; break;
            case ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER: wantA33="TLS_HANDSHAKE_FAILED_OTHER"; break;
            case ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED: wantA33="TLS_VERIFIED_ADMISSION_UNPROVEN"; break;
            case ORIGINAL_GO_PROTECTED_REQUEST_WRITE_FAILED: wantA33="PROTECTED_REQUEST_WRITE_FAILED"; break;
            case ORIGINAL_GO_PROTECTED_REQUEST_WRITE_OK: wantA33="PROTECTED_REQUEST_WRITTEN_REPLY_UNPROVEN"; break;
            case ORIGINAL_GO_PROTECTED_REPLY_FAILED_TIMEOUT: wantA33="PROTECTED_REPLY_FAILED_TIMEOUT"; break;
            case ORIGINAL_GO_PROTECTED_REPLY_FAILED_AUTH_REJECTED: wantA33="PROTECTED_REPLY_FAILED_AUTH_REJECTED"; break;
            case ORIGINAL_GO_PROTECTED_REPLY_FAILED_VERSION_REJECTED: wantA33="PROTECTED_REPLY_FAILED_VERSION_REJECTED"; break;
            case ORIGINAL_GO_PROTECTED_REPLY_FAILED_PEER_CLOSED: wantA33="PROTECTED_REPLY_FAILED_PEER_CLOSED"; break;
            case ORIGINAL_GO_PROTECTED_REPLY_FAILED_POLICY_REJECTED: wantA33="PROTECTED_REPLY_FAILED_POLICY_REJECTED"; break;
            case ORIGINAL_GO_PROTECTED_REPLY_FAILED_OTHER: wantA33="PROTECTED_REPLY_FAILED_OTHER"; break;
            case ORIGINAL_GO_PROTECTED_REPLY_PARSED: wantA33="PROTECTED_REPLY_PARSED_VERIFICATION_UNPROVEN"; break;
            case ORIGINAL_GO_ADMISSION_VERIFIED: wantA33="PROTECTED_ADMISSION_VERIFIED_LEASE_UNPROVEN"; break;
            default:throw new AssertionError("missing A33 stage expectation");
            }
            File diag=Files.createTempDirectory("wbd-a33-cold").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(
                new File(diag,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_OPENED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_KERNEL_CONFIGURED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_RAW_SOCKET_READY);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_OK);
            if(finalStage!=RootDiagnosticReceipt.Event.ORIGINAL_GO_TCP_SYNACK_SEEN)
                w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TCP_SYNACK_SEEN);
            w.record(finalStage);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String actual=RootDiagnosticReport.build(diag,source,36);
            contains(actual,"last_session_stage="+wantA33);
            if(actual.contains("ROOT_PRIVATE_SECRET")||actual.contains("/data/user/"))
                throw new AssertionError("cold report exposed private input");
        }
        // Real A33 phone sequence stopped at native TLS after 14.997s.
        // A34 exports independent original payload TX/RX and deadline facts.
        for(RootDiagnosticReceipt.Event failure:new RootDiagnosticReceipt.Event[]{
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_DEADLINE_ELAPSED_OTHER,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CANCELLED,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_BOOTSTRAP_CLOSED
        }){
            File dir34=Files.createTempDirectory("wbd-a34-receipt").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(new File(dir34,"wbd-root-diagnostic.txt"));
            for(RootDiagnosticReceipt.Event e:new RootDiagnosticReceipt.Event[]{
                RootDiagnosticReceipt.Event.START_REQUESTED,
                RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2,
                RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_OPENED,
                RootDiagnosticReceipt.Event.ORIGINAL_GO_RAW_SOCKET_READY,
                RootDiagnosticReceipt.Event.ORIGINAL_GO_ASSOC_ESTABLISHED,
                RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED,
                RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_OK,
                RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX_NOT_OBSERVED,
                failure,
                RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO
            })w.record(e);
            String txt=RootDiagnosticReport.build(dir34,source,36);
            contains(txt,"last_session_stage="+failure.name().replace("ORIGINAL_GO_",""));
            contains(txt,"ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_OK");
            contains(txt,"ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX_NOT_OBSERVED");
        }
        // A35: reproducible API36 three times: real original FakeTCP
        // Established, bootstrap TX, no peer payload, original RTO.
        // A scoped rooted kernel RST guard either verifies exact install
        // and Stop or fails before any new SYN. Never count Linux as phone.
        for(RootDiagnosticReceipt.Event result:new RootDiagnosticReceipt.Event[]{
            RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_FAILED_IPTABLES_UNAVAILABLE,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_FAILED_READBACK_MISMATCH,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_STOP_UNVERIFIED
        }){
            File a35=Files.createTempDirectory("wbd-a35-kernel-rst").toFile();
            RootDiagnosticReceipt w=new RootDiagnosticReceipt(new File(a35,"wbd-root-diagnostic.txt"));
            w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_ACCEPTED);
            w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_OPENED);
            w.record(result);
            w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            String actual=RootDiagnosticReport.build(a35,source,36);
            contains(actual,"last_session_stage="+(result==
                RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_STOP_UNVERIFIED
                ?"COLD_RST_GUARD_STOP_UNVERIFIED":result.name()));
            if(actual.contains("198.51.100.")||actual.contains("password="))
                throw new AssertionError("A35 root-only rule private data exposed");
        }
        // A35 positive source-locked receipt: verified exact root rule,
        // an observed matched RST drop and exact Stop all survive export.
        // They NEVER turn a TLS failure into authentication success.
        File verified35=Files.createTempDirectory("wbd-a35-verified").toFile();
        RootDiagnosticReceipt w35=new RootDiagnosticReceipt(
            new File(verified35,"wbd-root-diagnostic.txt"));
        for(RootDiagnosticReceipt.Event e:new RootDiagnosticReceipt.Event[]{
            RootDiagnosticReceipt.Event.START_REQUESTED,
            RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_READY,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_OK,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_ASSOC_ESTABLISHED,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_OK,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_TIMEOUT,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_MATCHED_RST_DROP,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_STOP_CLEARED,
            RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO
        })w35.record(e);
        String verifiedTxt=RootDiagnosticReport.build(verified35,source,36);
        contains(verifiedTxt,"last_session_stage=TLS_HANDSHAKE_FAILED_TIMEOUT");
        contains(verifiedTxt,"ORIGINAL_GO_COLD_RST_GUARD_READY");
        contains(verifiedTxt,"ORIGINAL_GO_COLD_RST_GUARD_MATCHED_RST_DROP");
        contains(verifiedTxt,"ORIGINAL_GO_COLD_RST_GUARD_STOP_CLEARED");
        if(verifiedTxt.contains("198.51.100.")||verifiedTxt.contains("password="))
            throw new AssertionError("A35 positive TXT leaked private text");
        // A36: Restore overrides the previous TLS failure only with a new
        // verified journal receipt; rejected/partial recovery stays red.
        for(RootDiagnosticReceipt.Event end:new RootDiagnosticReceipt.Event[]{
            RootDiagnosticReceipt.Event.ROOT_RESTORE_COMPLETE,
            RootDiagnosticReceipt.Event.ROOT_RESTORE_FAILED,
            RootDiagnosticReceipt.Event.ROOT_RESTORE_REFUSED_LIVE_OWNER
        }){
            File restore=Files.createTempDirectory("wbd-a36-restore").toFile();
            RootDiagnosticReceipt wr36=new RootDiagnosticReceipt(new File(restore,"wbd-root-diagnostic.txt"));
            wr36.record(RootDiagnosticReceipt.Event.START_REQUESTED);
            wr36.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
            wr36.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CERTIFICATE);
            wr36.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            wr36.record(RootDiagnosticReceipt.Event.ROOT_RESTORE_REQUESTED);
            if(end==RootDiagnosticReceipt.Event.ROOT_RESTORE_COMPLETE){
                wr36.record(RootDiagnosticReceipt.Event.ROOT_RESTORE_ROUTE_CLEARED);
                wr36.record(RootDiagnosticReceipt.Event.ROOT_RESTORE_RST_CLEARED);
            }
            wr36.record(end);
            String result=RootDiagnosticReport.build(restore,source,36);
            String want=end==RootDiagnosticReceipt.Event.ROOT_RESTORE_COMPLETE
                ?"ROOT_RESTORE_VERIFIED_OWNED_KERNEL_CLEAR":
                end==RootDiagnosticReceipt.Event.ROOT_RESTORE_FAILED
                ?"ROOT_RESTORE_FAILED_NO_GLOBAL_MUTATION":"ROOT_RESTORE_REFUSED_LIVE_OWNER";
            contains(result,"last_session_stage="+want);
        }
        File certDir=Files.createTempDirectory("wbd-a36-cert").toFile();
        RootDiagnosticReceipt certWriter=new RootDiagnosticReceipt(new File(certDir,"wbd-root-diagnostic.txt"));
        for(RootDiagnosticReceipt.Event e:new RootDiagnosticReceipt.Event[]{
            RootDiagnosticReceipt.Event.START_REQUESTED,
            RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_TRUST_SOURCE_APP_PEM,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH,
            RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CERTIFICATE,
            RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO
        })certWriter.record(e);
        String certReport=RootDiagnosticReport.build(certDir,source,36);
        contains(certReport,"last_session_stage=TLS_HANDSHAKE_FAILED_CERTIFICATE");
        contains(certReport,"ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH");
        File a37=Files.createTempDirectory("wbd-a37-default-policy").toFile();
        RootDiagnosticReceipt a37w=new RootDiagnosticReceipt(new File(a37,"wbd-root-diagnostic.txt"));
        a37w.record(RootDiagnosticReceipt.Event.START_REQUESTED);
        a37w.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
        a37w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_ACCEPTED);
        a37w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_VERIFY_DISABLED);
        a37w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED);
        a37w.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
        String a37txt=RootDiagnosticReport.build(a37,source,36);
        contains(a37txt,"ORIGINAL_GO_TLS_CERT_VERIFY_DISABLED");
        contains(a37txt,"last_session_stage=TLS_VERIFIED_ADMISSION_UNPROVEN");
        if(a37txt.contains("ORIGINAL_GO_TLS_CERT_VERIFY_ENABLED"))
            throw new AssertionError("reported strict verification in default mode");
        a37w.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_DISABLED);
        String effective=RootDiagnosticReport.build(a37,source,36);
        contains(effective,"ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_DISABLED");
        if(effective.contains("ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_ENABLED"))
            throw new AssertionError("admission TLS override falsely reported");
        // A39: distinguish "APK opened but nobody started" from a tap
        // rejected before the Service, and a Start dispatch with no native
        // event. A new UI tap must not inherit an earlier TLS error.
        File openedDir=Files.createTempDirectory("wbd-a39-opened").toFile();
        RootDiagnosticReceipt opened=new RootDiagnosticReceipt(
            new File(openedDir,"wbd-root-diagnostic.txt"));
        opened.record(RootDiagnosticReceipt.Event.UI_OPENED);
        contains(RootDiagnosticReport.build(openedDir,source,36),
            "last_session_stage=UI_OPEN_NO_START");
        opened.record(RootDiagnosticReceipt.Event.UI_CREDENTIAL_LOAD_FAILED);
        opened.record(RootDiagnosticReceipt.Event.UI_START_TAPPED);
        opened.record(RootDiagnosticReceipt.Event.UI_START_VALIDATION_REJECTED);
        contains(RootDiagnosticReport.build(openedDir,source,36),
            "last_session_stage=UI_START_PRE_SERVICE_REJECTED");

        File dispatchDir=Files.createTempDirectory("wbd-a39-dispatch").toFile();
        RootDiagnosticReceipt dispatch=new RootDiagnosticReceipt(
            new File(dispatchDir,"wbd-root-diagnostic.txt"));
        dispatch.record(RootDiagnosticReceipt.Event.START_REQUESTED);
        dispatch.record(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CERTIFICATE);
        dispatch.record(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
        dispatch.record(RootDiagnosticReceipt.Event.UI_START_TAPPED);
        dispatch.record(RootDiagnosticReceipt.Event.UI_CREDENTIAL_SAVE_FAILED);
        dispatch.record(RootDiagnosticReceipt.Event.UI_START_DISPATCH_REQUESTED);
        dispatch.record(RootDiagnosticReceipt.Event.UI_START_DISPATCHED);
        String noService=RootDiagnosticReport.build(dispatchDir,source,36);
        contains(noService,"last_session_stage=UI_START_DISPATCHED_SERVICE_NOT_OBSERVED");
        contains(noService,"UI_CREDENTIAL_SAVE_FAILED");
        dispatch.record(RootDiagnosticReceipt.Event.START_REQUESTED);
        dispatch.record(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
        dispatch.record(RootDiagnosticReceipt.Event.NETWORK_SCOPE_VERIFIED);
        String nowService=RootDiagnosticReport.build(dispatchDir,source,36);
        contains(nowService,"last_session_stage=APP_PRE_NATIVE");
        dispatch.record(RootDiagnosticReceipt.Event.UI_START_TAPPED);
        dispatch.record(RootDiagnosticReceipt.Event.UI_START_DISPATCH_FAILED);
        contains(RootDiagnosticReport.build(dispatchDir,source,36),
            "last_session_stage=UI_START_SERVICE_DISPATCH_FAILED");
        System.out.println("ANDROID_A39_ZERO_EVENT_APP_PREFLIGHT_FIXED_DIAGNOSTIC_HOST_PASS");
        System.out.println("ANDROID_A38_ORIGINAL_ADMISSION_TLS_EFFECTIVE_OFF_RECEIPT_HOST_PASS");
        System.out.println("ANDROID_A37_MAIN_TLS_DEFAULT_OFF_FIXED_RECEIPT_HOST_PASS");
        System.out.println("ANDROID_A36_CERT_REASON_RESTORE_REPORT_HOST_PASS");
        System.out.println("ANDROID_A35_ORIGINAL_ROOT_RST_GUARD_RECEIPT_HOST_PASS");
        System.out.println("ANDROID_A34_TLS_ORIGINAL_WIRE_AND_DEADLINE_HOST_PASS");
        System.out.println("ANDROID_A33_SYNACK_TLS_ADMISSION_STAGE_PRIORITY_HOST_PASS");
        System.out.println("ANDROID_A32_PRE_SU_CREDENTIAL_0600_RECEIPT_HOST_PASS");
        System.out.println("ANDROID_ROOT_A31_PARSE_REASON_SAFE_HOST_PASS");
        System.out.println("ANDROID_ROOT_SAFE_DIAGNOSTIC_EXPORT_HOST_PASS");
    }
}
