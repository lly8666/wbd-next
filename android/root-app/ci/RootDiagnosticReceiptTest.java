package org.wbdnext.rootclient;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

// Host-Java assurance of the EXACT sealed, credential-free Root receipt writer.
// No dummy Go/TLS success signals or Android device execution claims.
public final class RootDiagnosticReceiptTest {
    public static void main(String[] args)throws Exception{
        File dir=Files.createTempDirectory("wbd-diagnostic-fixture").toFile();
        try{
            File receipt=new File(dir,"root-receipt.txt");
            RootDiagnosticReceipt writer=new RootDiagnosticReceipt(receipt);
            if(writer.record(null))throw new AssertionError("null event accepted");
        }catch(IllegalArgumentException correct){
            // Only the enum can reach the writer: caller data is not stored.
        }
        File file=new File(dir,"root-receipt.txt");
        RootDiagnosticReceipt receipt=new RootDiagnosticReceipt(file);
        if(!receipt.record(RootDiagnosticReceipt.Event.START_REQUESTED)||
            !receipt.record(RootDiagnosticReceipt.Event.NATIVE_SOURCE_VERIFIED)||
            !receipt.record(RootDiagnosticReceipt.Event.STOP_REQUESTED)||
            !receipt.record(RootDiagnosticReceipt.Event.OWNER_CLEANUP_FINISHED))
            throw new AssertionError("initial fixed receipt unavailable");
        String content=new String(Files.readAllBytes(file.toPath()),StandardCharsets.US_ASCII);
        if(content.split("\\n").length!=4)throw new AssertionError("wrong record count");
        for(String line:content.split("\\n")){
            String[] columns=line.split("\\|",-1);
            if(columns.length!=2||!columns[0].matches("[0-9]{13}")||
               !RootDiagnosticReceipt.safeEventToken(columns[1]))
                throw new AssertionError("non-allowlisted/secret field");
        }
        if(RootDiagnosticReceipt.safeEventToken("secret_username")||
           RootDiagnosticReceipt.safeEventToken("ROOT_PROCESS_EXIT_139")||
           RootDiagnosticReceipt.safeEventToken("10.0.0.1"))
            throw new AssertionError("untrusted input would be serialized");
        for(int i=0;i<1200;i++){
            if(!receipt.record(RootDiagnosticReceipt.Event.UID_ROUTE_RECEIPT))
                throw new AssertionError("rollover failed at "+i);
        }
        File prev=new File(dir,"root-receipt.txt.previous");
        if(!prev.isFile()||file.length()>16384||prev.length()>16384)
            throw new AssertionError("bounded rollover failed");
        String recent=new String(Files.readAllBytes(file.toPath()),StandardCharsets.US_ASCII);
        if(!recent.contains("UID_ROUTE_RECEIPT")||
           recent.contains("password")||recent.contains("username")||
           recent.contains("token")||recent.contains("route_key"))
            throw new AssertionError("not safely bounded/allowlisted");
        Files.deleteIfExists(file.toPath());
        Files.deleteIfExists(prev.toPath());
        Files.deleteIfExists(dir.toPath());
        System.out.println("ANDROID_ARM64_ROOT_DIAGNOSTIC_FIXED_ENUM_ROTATION_HOST_PASS");
    }
}
