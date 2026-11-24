package org.wbdnext.rootclient;

import android.content.Context;
import android.os.Build;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Explicit, one-tap, NON-PROTOCOL ARM64 KernelSU cold capabilities test.
 *
 * The only route mutation is a single documentation TEST-NET-1 /32 in
 * independent table 19843 and an exact UID range for THIS test APK only,
 * never another app UID / default route / netd table / production 19842.
 * POSIX trap owns immediate rollback; no persistent TUN or packet tunnel.
 * The signed ORIGINAL Go ELF is separately checked via its real CLI help.
 * Real TLS/auth/lease/M4 needs an actual server and is always NOT_RUN here.
 */
final class RootDeviceSelfTest {
    private RootDeviceSelfTest(){}
    private static boolean uidPacketEvent(String code){
        for(String allowed:UID_PACKET_EVENTS)if(allowed.equals(code))return true;
        return false;
    }
    // A12 exclusively emits fixed, credential-free kernel stage/errno classes.
    private static final String[] UID_PACKET_DIAG_EVENTS={
        "TUN_INTERFACE_DISAPPEARED",
        "TUN_ROUTE_ADD_FAIL","TUN_ROUTE_ERR_EINVAL",
        "TUN_ROUTE_ERR_EPERM","TUN_ROUTE_ERR_DEVICE",
        "TUN_ROUTE_ERR_EXISTS","TUN_ROUTE_ERR_OTHER",
        "UID_RULE_ADD_FAIL","UID_RULE_ERR_EINVAL",
        "UID_RULE_ERR_EPERM","UID_RULE_ERR_EXISTS",
        "UID_RULE_ERR_OTHER","UID_RULE_SHOW_UNAVAILABLE",
        "UID_RULE_READBACK_FAIL","TUN_ROUTE_SHOW_UNAVAILABLE",
        "TUN_ROUTE_READBACK_FAIL"
    };
    private static boolean allowedUidPacketDiag(String value){
        for(String code:UID_PACKET_DIAG_EVENTS)if(code.equals(value))return true;
        return false;
    }
    private static final String[] UID_PACKET_EVENTS={
        "ROOT_FAIL","REFUSED","UID_TUN_COLLISION",
        "UID_TUN_CREATE_FAIL","UID_TUN_SETUP_FAIL","UID_TUN_ROUTE_FAIL",
        "UID_ROUTE_LOOKUP_FAIL","UID_TUN_SEND_READY",
        "UID_TUN_PACKET_PASS","UID_TUN_PACKET_FAIL",
        "UID_TUN_ROLLBACK_PASS","UID_TUN_ROLLBACK_FAIL","SCRIPT_DONE"
    };

    private static void realUidTunPacketTest(File sourceLockedHelper,int ownUid,
                                              List<String> events){
        if(!(events.contains("ROOT_PASS") &&
             events.contains("TUN_PASS") &&
             events.contains("ROUTE_UID_PASS") &&
             events.contains("ROUTE_ROLLBACK_PASS"))){
            events.add("REAL_APP_UID_TUN_PACKET=NOT_RUN (previous gate failed)");
            return;
        }
        boolean sendAttempted=false;
        boolean nativeCaptureConfirmed=false;
        boolean cleanupConfirmed=false;
        try{
            String script=RootUidTunPacketScript.build(sourceLockedHelper,ownUid);
            Process shell=new ProcessBuilder("su","-c",script)
                .redirectErrorStream(true).start();
            try(BufferedReader reader=new BufferedReader(
                new InputStreamReader(shell.getInputStream(),StandardCharsets.UTF_8))){
                String line;
                while((line=reader.readLine())!=null){
                    if(line.startsWith("WBD_A12_")){
                        String diagnostic=line.substring("WBD_A12_".length()).trim();
                        if(allowedUidPacketDiag(diagnostic)&&
                           !events.contains("A12_"+diagnostic))
                            events.add("A12_"+diagnostic);
                        continue;
                    }
                    if(!line.startsWith("WBD_A11_"))continue;
                    String event=line.substring("WBD_A11_".length()).trim();
                    if(!uidPacketEvent(event))continue;
                    if(!events.contains("A11_"+event))events.add("A11_"+event);
                    if("UID_TUN_SEND_READY".equals(event)&&!sendAttempted){
                        sendAttempted=true;
                        // Runs in this original Android app's real kernel
                        // UID. Do NOT Network.bindSocket / bindProcessToNetwork:
                        // this is precisely a natural unbound App UID flow.
                        // No resolver, plaintext credential or external host.
                        try(DatagramSocket sender=new DatagramSocket()){
                            byte[] bytes=RootUidTunPacketScript.PAYLOAD.getBytes(
                                StandardCharsets.US_ASCII);
                            byte[] reserved={(byte)192,0,2,1};
                            DatagramPacket packet=new DatagramPacket(
                                bytes,bytes.length,
                                InetAddress.getByAddress(reserved),
                                RootUidTunPacketScript.PORT);
                            sender.send(packet);
                            events.add("A11_APP_UID_UDP_SEND_ATTEMPTED");
                        }catch(Exception ignored){
                            // The kernel route can reject socket egress.
                            events.add("A11_APP_UID_UDP_SEND_FAILED");
                        }
                    }
                    if("UID_TUN_PACKET_PASS".equals(event))
                        nativeCaptureConfirmed=true;
                    if("UID_TUN_ROLLBACK_PASS".equals(event))
                        cleanupConfirmed=true;
                }
            }
            if(shell.waitFor()!=0)events.add("A11_ROOT_CHILD_EXIT_NONZERO");
            if(nativeCaptureConfirmed&&sendAttempted&&cleanupConfirmed){
                events.add("REAL_APP_UID_TO_TEMP_TUN_PACKET=PASS (kernel packet observed)");
            }else{
                events.add("REAL_APP_UID_TO_TEMP_TUN_PACKET=NOT_PROVEN");
            }
            if(!cleanupConfirmed)events.add("A11_ROUTE_ROLLBACK=NOT_VERIFIED");
        }catch(Exception e){
            events.add("REAL_APP_UID_TO_TEMP_TUN_PACKET=NOT_PROVEN");
            events.add("A11_LAUNCH=FAIL ("+e.getClass().getSimpleName()+")");
        }
    }

    static final String[] CODES={
        "ROOT_PASS","ROOT_FAIL",
        "GO_ELF_HELP_PASS","GO_ELF_HELP_FAIL","GO_ELF_SIGSEGV","GO_ELF_SIGILL",
        "TUN_PASS","TUN_FAIL",
        "RAW_PASS","RAW_FAIL",
        "UNDERLAY_PASS","UNDERLAY_FAIL","UNDERLAY_NOT_RUN",
        "ROUTE_UID_PASS","ROUTE_UID_FAIL","ROUTE_UID_COLLISION",
        "ROUTE_ROLLBACK_PASS","ROUTE_ROLLBACK_FAIL","ROUTE_ROLLBACK_NOT_RUN",
        "SELFTEST_REFUSED","SELFTEST_SCRIPT_DONE"
    };
    private static String q(String value){
        if(value==null)throw new IllegalArgumentException("null POSIX argument");
        return "'"+value.replace("'","'\\''")+"'";
    }
    private static boolean allowed(String name){
        for(String v:CODES)if(v.equals(name))return true;
        return false;
    }
    private static boolean validIface(String value){
        return value!=null&&value.matches("[A-Za-z0-9_.-]{1,15}");
    }
    static String script(File nativeClient,File originalRust,File probe,
                         String iface,int ownUid){
        if(!validIface(iface)||ownUid<10000||ownUid>999999999)
            throw new IllegalArgumentException("invalid local kernel scope");
        StringBuilder sh=new StringBuilder(8200);
        sh.append("set -u; umask 077; PATH=/system/bin:/system/xbin:/vendor/bin; export PATH; ");
        sh.append("p='/data/local/tmp/wbd-next-selftest'; ");
        sh.append("if [ \"$(id -u)\" != 0 ]; then echo WBD_SELFTEST_ROOT_FAIL; exit 51; fi; ");
        sh.append("echo WBD_SELFTEST_ROOT_PASS; ");
        // Fail closed, including leftover root product owner. No accidental
        // overwrite of an active Root Go app and no foreign/symlink staging.
        sh.append("if [ -r /data/local/tmp/wbd-next-root/owner.pid ]; then ");
        sh.append("echo WBD_SELFTEST_SELFTEST_REFUSED; exit 52; fi; ");
        sh.append("if [ -L \"$p\" ]; then echo WBD_SELFTEST_SELFTEST_REFUSED; exit 53; fi; ");
        sh.append("if [ ! -e \"$p\" ]; then mkdir -m 700 \"$p\" || exit 54; fi; ");
        sh.append("if [ ! -d \"$p\" ] || [ \"$(stat -c %u \"$p\")\" != 0 ] || ");
        sh.append("[ \"$(stat -c %a \"$p\")\" != 700 ]; then ");
        sh.append("echo WBD_SELFTEST_SELFTEST_REFUSED; exit 55; fi; ");
        sh.append("if ! mkdir \"$p/.lock\" 2>/dev/null; then ");
        sh.append("echo WBD_SELFTEST_SELFTEST_REFUSED; exit 56; fi; ");
        sh.append("route_added=0; rule_added=0; ");
        // Cleanup is exact-match only: never delete a foreign table/rule.
        sh.append("cleanup() { ");
        sh.append("if [ \"$rule_added\" = 1 ]; then ");
        sh.append("ip -4 rule del pref 9699 uidrange ").append(ownUid).append("-").append(ownUid);
        sh.append(" lookup 19843 >/dev/null 2>&1 || :; fi; ");
        sh.append("if [ \"$route_added\" = 1 ]; then ");
        sh.append("ip -4 route del 192.0.2.1/32 dev lo table 19843 >/dev/null 2>&1 || :; fi; ");
        sh.append("if ip -4 rule show 2>/dev/null | grep -Eq '^ *9699:'; then ");
        sh.append("echo WBD_SELFTEST_ROUTE_ROLLBACK_FAIL; ");
        sh.append("elif ip -4 route show table 19843 2>/dev/null | grep -q '[^[:space:]]'; then ");
        sh.append("echo WBD_SELFTEST_ROUTE_ROLLBACK_FAIL; ");
        sh.append("else echo WBD_SELFTEST_ROUTE_ROLLBACK_PASS; fi; ");
        sh.append("rm -f \"$p/.help.log\"; rmdir \"$p/.lock\" 2>/dev/null || :; }; ");
        sh.append("trap cleanup EXIT; trap 'exit 59' HUP INT TERM; ");
        // Copy only previously SHA-verified files from APK private staging.
        sh.append("if ! cp ").append(q(nativeClient.getAbsolutePath()));
        sh.append(" \"$p/.go\" || ! cp ").append(q(originalRust.getAbsolutePath()));
        sh.append(" \"$p/.rust\" || ! cp ").append(q(probe.getAbsolutePath()));
        sh.append(" \"$p/.test\"; then echo WBD_SELFTEST_SELFTEST_REFUSED; exit 57; fi; ");
        sh.append("chmod 700 \"$p/.go\" \"$p/.test\"; chmod 600 \"$p/.rust\"; ");
        sh.append("mv -f \"$p/.go\" \"$p/wbd-v4-client-arm64\"; ");
        sh.append("mv -f \"$p/.rust\" \"$p/libwbd_engine.so\"; ");
        sh.append("mv -f \"$p/.test\" \"$p/device-selftest-arm64\"; ");
        // Same original ARM64 Go ELF as official APK. ErrHelp may cause
        // exit=1 via main's log.Fatal: success requires REAL usage content.
        sh.append("LD_LIBRARY_PATH=\"$p\"; export LD_LIBRARY_PATH; ");
        sh.append("\"$p/wbd-v4-client-arm64\" --help >\"$p/.help.log\" 2>&1; go_rc=$?; ");
        sh.append("if [ \"$go_rc\" = 139 ]; then echo WBD_SELFTEST_GO_ELF_SIGSEGV; ");
        sh.append("elif [ \"$go_rc\" = 132 ]; then echo WBD_SELFTEST_GO_ELF_SIGILL; ");
        sh.append("elif [ \"$go_rc\" -le 1 ] && ");
        sh.append("grep -q 'android-network-handle' \"$p/.help.log\"; then ");
        sh.append("echo WBD_SELFTEST_GO_ELF_HELP_PASS; ");
        sh.append("else echo WBD_SELFTEST_GO_ELF_HELP_FAIL; fi; ");
        sh.append("if \"$p/device-selftest-arm64\" --tun >/dev/null 2>&1; then ");
        sh.append("echo WBD_SELFTEST_TUN_PASS; else echo WBD_SELFTEST_TUN_FAIL; fi; ");
        sh.append("if \"$p/device-selftest-arm64\" --raw ").append(q(iface));
        sh.append(" >/dev/null 2>&1; then echo WBD_SELFTEST_RAW_PASS; ");
        sh.append("else echo WBD_SELFTEST_RAW_FAIL; fi; ");
        sh.append("if \"$p/device-selftest-arm64\" --underlay ").append(q(iface));
        sh.append(" >/dev/null 2>&1; then echo WBD_SELFTEST_UNDERLAY_PASS; ");
        sh.append("else echo WBD_SELFTEST_UNDERLAY_FAIL; fi; ");
        // Hard gate BEFORE adding any rule: do not touch pre-existing data
        // from any process, or original product table19842/pref9600..9607.
        sh.append("if ip -4 rule show 2>/dev/null | grep -Eq '^ *9699:' || ");
        sh.append("ip -4 route show table 19843 2>/dev/null | grep -q '[^[:space:]]'; then ");
        sh.append("echo WBD_SELFTEST_ROUTE_UID_COLLISION; ");
        sh.append("else ");
        sh.append("if ip -4 route add 192.0.2.1/32 dev lo table 19843 >/dev/null 2>&1; then ");
        sh.append("route_added=1; ");
        sh.append("if ip -4 rule add pref 9699 uidrange ").append(ownUid).append("-");
        sh.append(ownUid).append(" lookup 19843 >/dev/null 2>&1; then ");
        sh.append("rule_added=1; ");
        sh.append("if ip -4 rule show | grep -Eq '^ *9699:' && ");
        sh.append("ip -4 route show table 19843 | grep -q '192.0.2.1'; then ");
        sh.append("echo WBD_SELFTEST_ROUTE_UID_PASS; ");
        sh.append("else echo WBD_SELFTEST_ROUTE_UID_FAIL; fi; ");
        sh.append("else echo WBD_SELFTEST_ROUTE_UID_FAIL; fi; ");
        sh.append("else echo WBD_SELFTEST_ROUTE_UID_FAIL; fi; fi; ");
        sh.append("echo WBD_SELFTEST_SELFTEST_SCRIPT_DONE; ");
        return sh.toString();
    }
    static String run(Context ctx,PhysicalNetwork chosen){
        List<String> events=new ArrayList<>();
        events.add("REAL_TLS_AUTH_LEASE=NOT_RUN (needs real server and credentials)");
        events.add("REAL_M3_M4_APP_DATA=NOT_RUN (needs authenticated session)");
        events.add("SYSTEM_DNS_TAKEOVER=NOT_RUN (safety gates remain false)");
        // Do not mistake an x86_64 Android16 NativeBridge advertising
        // arm64-v8a for a real ARM64 kernel. Real C-layer qualification
        // requires uname -m from the running guest kernel.
        boolean arm64Kernel=false;
        try{
            Process kernel=new ProcessBuilder("uname","-m").start();
            try(BufferedReader r=new BufferedReader(
                new InputStreamReader(kernel.getInputStream(),StandardCharsets.US_ASCII))){
                String arch=r.readLine();
                arm64Kernel="aarch64".equals(arch)||"arm64".equals(arch);
            }
            arm64Kernel=arm64Kernel&&kernel.waitFor()==0;
        }catch(Exception ignored){arm64Kernel=false;}
        if(!arm64Kernel||Build.SUPPORTED_ABIS.length==0||
           !"arm64-v8a".equals(Build.SUPPORTED_ABIS[0])){
            events.add("NATIVE_ARM64_KERNEL=FAIL (requires actual aarch64 kernel+primary ABI)");
            return String.join("\n",events);
        }
        if(chosen==null||PhysicalNetwork.exact(ctx,chosen.handle,
           chosen.interfaceName,chosen.ifindex,chosen.mtu,chosen.address)==null){
            events.add("PHYSICAL_NETWORK=FAIL (refresh real Wi-Fi/cellular/Ethernet IPv4 Network)");
            return String.join("\n",events);
        }
        events.add("NATIVE_ARM64_KERNEL=PASS (actual uname aarch64)");
        events.add("PHYSICAL_NETWORK=PASS (Android Network exact readback)");
        try{
            NativePayload original=NativePayload.stage(ctx);
            File diag=NativePayload.stageDeviceSelfTest(ctx);
            events.add("SOURCE_AND_APK_ASSET_SHA=PASS");
            String shell=script(original.client,original.engine,diag,
                                chosen.interfaceName,android.os.Process.myUid());
            Process child=new ProcessBuilder("su","-c",shell)
                .redirectErrorStream(true).start();
            try(BufferedReader lines=new BufferedReader(
                new InputStreamReader(child.getInputStream(),StandardCharsets.UTF_8))){
                String line;
                while((line=lines.readLine())!=null){
                    line=line.trim();
                    if(line.startsWith("WBD_SELFTEST_")){
                        String code=line.substring("WBD_SELFTEST_".length());
                        if(allowed(code)&&!events.contains(code))events.add(code);
                    }
                    // Never echo untrusted root/native stdout, tokens, app
                    // package names, route UIDs, env, or shell failure text.
                }
            }
            int rc=child.waitFor();
            if(rc!=0)events.add("ROOT_RUN_EXIT_NONZERO");
            if(!events.contains("ROUTE_ROLLBACK_PASS")&&
               !events.contains("ROUTE_ROLLBACK_FAIL"))events.add("ROUTE_ROLLBACK=NOT_VERIFIED");
            realUidTunPacketTest(diag,android.os.Process.myUid(),events);
        }catch(Exception e){
            events.add("ROOT_TEST_LAUNCH=FAIL ("+e.getClass().getSimpleName()+")");
        }
        return String.join("\n",events);
    }
}
