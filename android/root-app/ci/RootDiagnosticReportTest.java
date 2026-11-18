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
        System.out.println("ANDROID_ROOT_SAFE_DIAGNOSTIC_EXPORT_HOST_PASS");
    }
}
