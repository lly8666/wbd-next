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
        System.out.println("ANDROID_A33_SYNACK_TLS_ADMISSION_STAGE_PRIORITY_HOST_PASS");
        System.out.println("ANDROID_A32_PRE_SU_CREDENTIAL_0600_RECEIPT_HOST_PASS");
        System.out.println("ANDROID_ROOT_A31_PARSE_REASON_SAFE_HOST_PASS");
        System.out.println("ANDROID_ROOT_SAFE_DIAGNOSTIC_EXPORT_HOST_PASS");
    }
}
