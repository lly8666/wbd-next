package org.wbdnext.rootclient;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.IntentFilter;
import android.net.Uri;
import android.net.ConnectivityManager;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.File;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

// The foreground APP supervises one root Go OS process. Neither this
// Service nor Java owns/authenticates/forges any data packet or VPN route.
// Go/Rust's true TLS/lease/M4, kernel rule journal and joined Stop own it.
public final class RootClientService extends Service {
    static final String START="org.wbdnext.rootclient.START";
    static final String STOP="org.wbdnext.rootclient.STOP";
    static final String RESTORE="org.wbdnext.rootclient.RESTORE";
    private static final String ROOT="/data/local/tmp/wbd-next-root";
    private static final String CHANNEL="wbd-root-native";
    public static volatile String status="NOT_RUNNING (actual device NOT_QUALIFIED)";
    // Actual original Go -> Rust M3/M4 mode revision; separate from
    // generic Root/TUN readiness and never evidence of phone E2E.
    public static volatile String fecStatus="FEC: 尚无本会话原生状态";
    private final AtomicBoolean running=new AtomicBoolean(false);
    private final AtomicBoolean stopping=new AtomicBoolean(false);
    private final AtomicBoolean stopSignalDispatched=new AtomicBoolean(false);
    private final AtomicBoolean restoring=new AtomicBoolean(false);
    private final Object ownerLaunchLock=new Object();
    private final Handler networkEvents=new Handler(Looper.getMainLooper());
    private volatile Process root;
    private volatile PhysicalNetwork selection;
    private volatile String ownerToken;
    private volatile String ownerExecutable="wbd-v4-client-arm64";
    private ConnectivityManager watchedManager;
    private ConnectivityManager.NetworkCallback watchedCallback;
    private NetworkScopeGate watchedGate;
    private BroadcastReceiver installedPackageWatch;
    // Fixed-enum stage events plus A47 strictly typed numeric original
    // Rust RAW header snapshots (numeric IP/ports permitted by user).
    // Never persist credentials, TLS transcript, or arbitrary native stdout.
    private RootDiagnosticReceipt diagnostics;
    @Override public void onCreate(){
        super.onCreate();
        diagnostics=new RootDiagnosticReceipt(
            new File(getFilesDir(),"wbd-root-diagnostic.txt"));
    }
    private void trace(RootDiagnosticReceipt.Event event){
        if(diagnostics!=null)diagnostics.record(event);
        Log.i("WBD_ROOT_DIAG",event.name());
    }

    private static String newOwnerToken(){
        byte[] bytes=new byte[16];
        new SecureRandom().nextBytes(bytes);
        StringBuilder out=new StringBuilder(32);
        for(byte b:bytes){
            int v=b&0xff;
            out.append(Character.forDigit(v>>>4,16));
            out.append(Character.forDigit(v&15,16));
        }
        return out.toString();
    }
    private void watchPhysicalNetwork(final PhysicalNetwork chosen){
        ConnectivityManager cm=getSystemService(ConnectivityManager.class);
        if(cm==null)throw new IllegalStateException("ConnectivityManager unavailable");
        final NetworkScopeGate gate=new NetworkScopeGate(chosen.handle);
        ConnectivityManager.NetworkCallback callback=new ConnectivityManager.NetworkCallback(){
            @Override public void onLost(Network network){
                if(gate.lost(network.getNetworkHandle()))
                    requestStop("PHYSICAL_NETWORK_LOST — withdrawing UID policy");
            }
            @Override public void onCapabilitiesChanged(Network network,NetworkCapabilities caps){
                boolean valid=PhysicalNetwork.physicalUnderlay(caps);
                if(gate.changed(network.getNetworkHandle(),valid))
                    requestStop("PHYSICAL_NETWORK_CAPABILITIES_CHANGED");
            }
            @Override public void onLinkPropertiesChanged(Network network,LinkProperties link){
                if(gate.selected(network.getNetworkHandle())&&
                   gate.changed(network.getNetworkHandle(),chosen.matchesLinkProperties(link)))
                    requestStop("PHYSICAL_NETWORK_LINK_CHANGED");
            }
            @Override public void onBlockedStatusChanged(Network network,boolean blocked){
                if(gate.blocked(network.getNetworkHandle(),blocked))
                    requestStop("PHYSICAL_NETWORK_BLOCKED");
            }
        };
        // Listen to the exact selected WiFi/cell/Ethernet even when the
        // selected LAN has NO INTERNET capability. Android INTERNET
        // capability changing alone must not silently kill a valid
        // physically-bound original Go/Rust session.
        NetworkRequest request=new NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .addTransportType(NetworkCapabilities.TRANSPORT_CELLULAR)
            .addTransportType(NetworkCapabilities.TRANSPORT_ETHERNET)
            .build();
        cm.registerNetworkCallback(request,callback,networkEvents);
        synchronized(this){
            watchedManager=cm;
            watchedCallback=callback;
            watchedGate=gate;
        }
    }
    private void stopWatchingPhysicalNetwork(){
        ConnectivityManager cm;
        ConnectivityManager.NetworkCallback cb;
        synchronized(this){
            cm=watchedManager;cb=watchedCallback;
            if(watchedGate!=null)watchedGate.close();
            watchedManager=null;watchedCallback=null;watchedGate=null;
        }
        if(cm!=null&&cb!=null){
            try{cm.unregisterNetworkCallback(cb);}
            catch(IllegalArgumentException ignored){/* already unregistered */ }
        }
    }
    // Package removal/replacement is a protected Android system broadcast.
    // This is event-driven: a re-used UID must not remain routed to WBD.
    private void watchSelectedPackages(final String[] selectedPackages){
        final String generation=ownerToken;
        final String[] owned=selectedPackages.clone();
        IntentFilter filter=new IntentFilter();
        filter.addAction(Intent.ACTION_PACKAGE_REMOVED);
        filter.addAction(Intent.ACTION_PACKAGE_CHANGED);
        filter.addAction(Intent.ACTION_PACKAGE_REPLACED);
        filter.addDataScheme("package");
        BroadcastReceiver receiver=new BroadcastReceiver(){
            @Override public void onReceive(Context ctx,Intent event){
                Uri changed=event==null?null:event.getData();
                if(changed==null||generation==null||
                   !generation.equals(ownerToken))return;
                String actual=changed.getSchemeSpecificPart();
                for(String target:owned){
                    if(target.equals(actual)){
                        requestStop("SELECTED_APPLICATION_CHANGED — withdrawing all owned UID rules");
                        return;
                    }
                }
            }
        };
        // Events from Android itself, no periodic package enumeration.
        registerReceiver(receiver,filter);
        installedPackageWatch=receiver;
    }
    private static String[] watchedAllAppPackages(String[] manager,String[] bypass){
        if(manager==null||bypass==null)throw new IllegalArgumentException("unknown Root app scope");
        String[] out=new String[manager.length+bypass.length];
        System.arraycopy(manager,0,out,0,manager.length);
        System.arraycopy(bypass,0,out,manager.length,bypass.length);
        return out;
    }
    private void stopWatchingSelectedPackage(){
        BroadcastReceiver receiver=installedPackageWatch;
        installedPackageWatch=null;
        if(receiver!=null){
            try{unregisterReceiver(receiver);}
            catch(IllegalArgumentException ignored){/* already unregistered */}
        }
    }
    @Override public IBinder onBind(Intent i){return null;}
    private static String q(String s){
        // The host JVM tests this exact POSIX escaping implementation.
        return OriginalGoCommandArgs.shellQuote(s);
    }
    private void notification(){
        NotificationManager nm=getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(
            CHANNEL,"WBD Root original Go/Rust",
            NotificationManager.IMPORTANCE_LOW));
        Notification n=new Notification.Builder(this,CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle("WBD Root Native")
            .setContentText("Authenticating original Go / supervising Rust M4")
            .setOngoing(true).build();
        startForeground(5402,n);
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent==null){requestStop("Android restarted without original cold authorization");return START_NOT_STICKY;}
        if(STOP.equals(intent.getAction())){
            requestStop("USER_REQUESTED");
            if(!running.get()&&!restoring.get())stopSelf(startId);
            return START_NOT_STICKY;
        }
        if(RESTORE.equals(intent.getAction())){
            if(restoring.compareAndSet(false,true)){
                notification();
                trace(RootDiagnosticReceipt.Event.ROOT_RESTORE_REQUESTED);
                requestStop("USER_RESTORE_OWNED_KERNEL");
                new Thread(this::restoreOwnedRootNetwork,"wbd-root-restore").start();
            }
            return START_NOT_STICKY;
        }
        if(!START.equals(intent.getAction())||restoring.get()||
           !running.compareAndSet(false,true)){
            return START_NOT_STICKY;
        }
        stopping.set(false);
        stopSignalDispatched.set(false);
        trace(RootDiagnosticReceipt.Event.START_REQUESTED);
        trace(RootDiagnosticReceipt.Event.START_DIAGNOSTIC_STAGES_V2);
        try{
            notification();
            long handle=intent.getLongExtra("handle",0);
            String iface=intent.getStringExtra("iface");
            int index=intent.getIntExtra("index",0);
            int mtu=intent.getIntExtra("mtu",0);
            String local=intent.getStringExtra("local");
            if(iface==null||local==null)throw new IllegalStateException("Missing actual Network");
            PhysicalNetwork chosen=PhysicalNetwork.exact(this,handle,iface,index,mtu,local);
            if(chosen==null){
                trace(RootDiagnosticReceipt.Event.START_FAILED_EXACT_NETWORK);
                throw new IllegalStateException("ConnectivityManager Network changed");
            }
            trace(RootDiagnosticReceipt.Event.NETWORK_SCOPE_VERIFIED);
            String peer=intent.getStringExtra("peer");
            String directCIDRs=RootDirectIPv4.canonicalCSV(intent.getStringExtra("direct_cidrs"));
            if(intent.getBooleanExtra("direct_lan_auto",false)){
                // Cold original selected-Network route source must remain
                // identical to App START. No per-packet check or new FIB owner.
                String localSubnet=PhysicalNetwork.selectedConnectedIPv4Subnet(this,chosen);
                if(!RootDirectIPv4.includes(directCIDRs,localSubnet))
                    throw new IllegalArgumentException("实体Network直连子网已变化，请重新START");
            }
            String physicalDnsIPv4=RootPhysicalDNSUpstream.canonical(
                intent.getStringExtra("physical_dns_upstream"));
            if(intent.getBooleanExtra("physical_dns_follow_network",false)&&
               !physicalDnsIPv4.equals(PhysicalNetwork.selectedDNSIPv4(this,chosen)))
                throw new IllegalArgumentException("选定Network DNS发生变化，请重新START");
            String sni=intent.getStringExtra("sni");
            String user=intent.getStringExtra("user");
            String cipherExtra=intent.getStringExtra("record_cipher");
            final String recordCipher=cipherExtra==null?"chacha20-poly1305":cipherExtra;
            String paddingExtra=intent.getStringExtra("startup_padding");
            final String paddingMode=paddingExtra==null?"off":paddingExtra;
            String modeExtra=intent.getStringExtra("fec_mode");
            final String fecMode=modeExtra==null?"normal":modeExtra;
            final int fecProfile=intent.getIntExtra("fec_profile",1);
            final int nativeHealthSeconds=intent.getIntExtra("native_health_seconds",15);
            if(nativeHealthSeconds!=15&&nativeHealthSeconds!=30)
                throw new IllegalArgumentException("unsupported original Rust Health interval");
            if((!"normal".equals(fecMode)&&!"fec-fixed".equals(fecMode)&&
                !"fec-auto".equals(fecMode))||
               fecProfile<0||fecProfile>6||
               (!"normal".equals(fecMode)&&!"off".equals(paddingMode)))
                throw new IllegalArgumentException("unsupported Fixed/Normal selection");
            fecStatus="normal".equals(fecMode)
                ?"FEC: Normal/off（默认；无FEC修复）"
                :"FEC: "+fecMode+" 已选择，等待原Go/Rust的真实版本读回";
            if(!"off".equals(paddingMode)&&!"tls".equals(paddingMode)&&
               !"flows".equals(paddingMode))
                throw new IllegalArgumentException("unsupported original Normal startup padding");
            int port=intent.getIntExtra("port",0);
            int requestedOuterMTU=intent.getIntExtra("outer_mtu",1460);
            int requestedTunQueue=intent.getIntExtra("tun_txqlen",500);
            boolean allApps=intent.getBooleanExtra("all_apps",false);
            int[] targetUids=intent.getIntArrayExtra("target_uids");
            String[] targetPackages=intent.getStringArrayExtra("target_packages");
            int[] excludedAppIDs=intent.getIntArrayExtra("exclude_appids");
            String[] managerPackages=intent.getStringArrayExtra("manager_packages");
            String[] rawBypassPackages=intent.getStringArrayExtra("bypass_packages");
            int[] rawBypassUIDs=intent.getIntArrayExtra("bypass_uids");
            final String[] bypassPackages=rawBypassPackages==null&&rawBypassUIDs==null
                ?new String[0]:rawBypassPackages;
            final int[] bypassUIDs=rawBypassPackages==null&&rawBypassUIDs==null
                ?new int[0]:rawBypassUIDs;
            boolean hasCA=intent.getBooleanExtra("has_ca",false);
            boolean verifyTLS=intent.getBooleanExtra("tls_verify_server",false);
            boolean tunnelDNS=intent.getBooleanExtra("tunnel_dns",false);
            boolean physicalDNS=intent.getBooleanExtra("physical_dns",false);
            boolean cnSplitDNS=intent.getBooleanExtra("cn_dns_split",false);
            if(hasCA&&!verifyTLS)throw new IllegalArgumentException("CA requires strict TLS verification");
            boolean validatedScope=allApps
                ? targetUids==null&&targetPackages==null&&
                  AllAppRouteScope.same(this,excludedAppIDs,managerPackages,
                       bypassPackages,bypassUIDs)
                : excludedAppIDs==null&&managerPackages==null&&
                  rawBypassPackages==null&&rawBypassUIDs==null&&
                  InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids);
            if(!validatedScope)trace(RootDiagnosticReceipt.Event.START_FAILED_UID_SCOPE);
            if(peer==null||sni==null||user==null||
                !ServerAddress.valid(peer)||
                sni.length()==0||user.length()==0||
                port<1||port>65535||requestedOuterMTU<576||requestedOuterMTU>1500||
                 (requestedTunQueue!=500&&requestedTunQueue!=2048)||!validatedScope){
                throw new IllegalArgumentException("Verified full-app or selected-app scope changed");
            }
            trace(RootDiagnosticReceipt.Event.APP_UID_GROUP_VERIFIED);
            trace(allApps?RootDiagnosticReceipt.Event.ROUTE_SCOPE_ALL_ORDINARY_APPS_IPV4:
                RootDiagnosticReceipt.Event.ROUTE_SCOPE_SELECTED_APPS_IPV4);
            selection=chosen;
            ownerToken=newOwnerToken();
            watchPhysicalNetwork(chosen);
            watchSelectedPackages(allApps
                ?watchedAllAppPackages(managerPackages,bypassPackages):targetPackages);
            if(PhysicalNetwork.exact(this,chosen.handle,chosen.interfaceName,
                chosen.ifindex,chosen.mtu,chosen.address)==null)
                throw new IllegalStateException("Physical Network changed during callback registration");
            trace(RootDiagnosticReceipt.Event.ROOT_STAGE_REQUESTED);
            status="AUTHORIZING_ROOT — native credentials not yet verified";
            Thread owner=new Thread(()->runRoot(chosen,peer,sni,user,
                port,requestedOuterMTU,recordCipher,requestedTunQueue,paddingMode,fecMode,fecProfile,targetUids,targetPackages,allApps,excludedAppIDs,
                managerPackages,bypassPackages,bypassUIDs,
                hasCA,verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,directCIDRs,physicalDnsIPv4,nativeHealthSeconds),"wbd-native-root-owner");
            owner.start();
        }catch(Exception e){
            trace(RootDiagnosticReceipt.Event.START_REFUSED);
            status="START_REFUSED: "+e.getMessage();
            running.set(false);
            stopWatchingPhysicalNetwork();
            stopWatchingSelectedPackage();
            selection=null;
            ownerToken=null;
            new File(getFilesDir(),"wbd-pass.secret").delete();
            new File(getFilesDir(),"wbd-route.secret").delete();
            stopForeground(true);
            stopSelf(startId);
        }
        return START_NOT_STICKY;
    }
    private String launchCommand(NativePayload nativeCode,
                                 PhysicalNetwork net,String peer,String sni,
                                 String user,int peerPort,int requestedOuterMTU,String recordCipher,int requestedTunQueue,String paddingMode,String fecMode,int fecProfile,int[] targetUids,
                                 boolean allApps,int[] excludedAppIDs,
                                 boolean hasCA,boolean verifyTLS,boolean tunnelDNS,boolean physicalDNS,boolean cnSplitDNS,String token,String directCIDRs,String physicalDnsIPv4,int nativeHealthSeconds){
        // The host-tested argv is also the exact argv passed to original Go.
        // Secret *values* never appear here, only app-private file paths.
        List<String> args=OriginalGoCommandArgs.build(
            net.interfaceName,net.handle,net.address,peer,peerPort,
            40000+new SecureRandom().nextInt(20000),sni,user,
            new File(getFilesDir(),"wbd-pass.secret").getAbsolutePath(),
            new File(getFilesDir(),"wbd-route.secret").getAbsolutePath(),
            new File(getFilesDir(),"wbd-installation-id").getAbsolutePath(),
            nativeCode.cnGeosite.getAbsolutePath(),targetUids,allApps,
            excludedAppIDs,
            hasCA?new File(getFilesDir(),"wbd-server-ca.pem").getAbsolutePath():null,
            verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,requestedOuterMTU,recordCipher,requestedTunQueue,paddingMode,fecMode,fecProfile,directCIDRs,physicalDnsIPv4,nativeHealthSeconds);
        List<String> quotedArgs=new ArrayList<>();
        for(String a:args)quotedArgs.add(q(a));
        StringBuilder shell=new StringBuilder("set -eu; umask 077; ");
        shell.append("echo WBD_PUBLIC_ROOT_SHELL_ENTERED; ");
        // Fail closed even if a su provider returned an unprivileged shell:
        // this is a stage check, NOT proof of Root Manager identity.
        shell.append("test \"$(id -u)\" = 0; ");
        shell.append("echo WBD_PUBLIC_ROOT_UID_VERIFIED; ");
        shell.append("p=").append(q(ROOT)).append("; ");
        // /data/local/tmp may be writable to shell/other actors.
        // A pre-existing symlink or non-root directory must NEVER be
        // chmod'ed, followed, or used for root binary installation.
        shell.append("test ! -L \"$p\"; ");
        shell.append("if [ ! -e \"$p\" ]; then mkdir -m 700 \"$p\"; fi; ");
        shell.append("test -d \"$p\" && test ! -L \"$p\"; ");
        shell.append("test \"$(stat -c %u \"$p\")\" = 0; ");
        shell.append("test \"$(stat -c %a \"$p\")\" = 700; ");
        shell.append("echo WBD_PUBLIC_ROOT_PRIVATE_DIR_VERIFIED; ");
        // Verify prior root PID is not still live BEFORE replacing a
        // previous owner's lockless cold stage or installing a second TUN.
        shell.append("if [ -f \"$p/owner.pid\" ]; then ");
        shell.append("read oldpid oldstart oldgeneration < \"$p/owner.pid\"; ");
        shell.append("case \"$oldpid\" in ''|*[!0-9]*) exit 43;; esac; ");
        shell.append("if [ -r \"/proc/$oldpid/stat\" ]; then ");
        shell.append("set -- $(cat \"/proc/$oldpid/stat\"); ");
        shell.append("if [ \"${22}\" = \"$oldstart\" ]; then exit 44; fi; ");
        shell.append("fi; fi; ");
        shell.append("echo WBD_PUBLIC_ROOT_OWNER_GUARD_PASSED; ");
        // Every verified asset goes via a root-owned private directory:
        // Android 10+ disallows execution from writable app-private data.
        shell.append("cp ").append(q(nativeCode.client.getAbsolutePath()))
            .append(" \"$p/.client.tmp\"; ");
        shell.append("cp ").append(q(nativeCode.engine.getAbsolutePath()))
            .append(" \"$p/.engine.tmp\"; ");
        shell.append("chmod 700 \"$p/.client.tmp\"; chmod 600 \"$p/.engine.tmp\"; ");
        shell.append("mv -f \"$p/.client.tmp\" \"$p/").append(nativeCode.executableName).append("\"; ");
        shell.append("mv -f \"$p/.engine.tmp\" \"$p/libwbd_engine.so\"; ");
        shell.append("echo WBD_PUBLIC_ROOT_NATIVE_FILES_STAGED; ");
        // Shell exec preserves $$ + proc stat starttime as real native
        // Go process PID; Stop checks the same exact process, not pkill -f.
        shell.append("set -- $(cat /proc/$$/stat); native_start=${22}; ");
        shell.append("printf '%s %s %s\\n' \"$$\" \"$native_start\" ").append(q(token)).append(" > \"$p/owner.pid\"; ");
        shell.append("chmod 600 \"$p/owner.pid\"; ");
        shell.append("echo WBD_PUBLIC_ROOT_OWNER_PID_WRITTEN; ");
        shell.append("LD_LIBRARY_PATH=\"$p\"; export LD_LIBRARY_PATH; ");
        shell.append("echo WBD_PUBLIC_ROOT_EXEC_ATTEMPTED; ");
        shell.append("exec \"$p/").append(nativeCode.executableName).append("\" ");
        shell.append(String.join(" ",quotedArgs));
        return shell.toString();
    }
    private void runRoot(PhysicalNetwork net,String peer,String sni,String user,
                         int port,int requestedOuterMTU,String recordCipher,int requestedTunQueue,String paddingMode,String fecMode,int fecProfile,int[] targetUids,String[] targetPackages,
                         boolean allApps,int[] excludedAppIDs,String[] managerPackages,
                         String[] bypassPackages,int[] bypassUIDs,
                         boolean hasCA,boolean verifyTLS,boolean tunnelDNS,boolean physicalDNS,boolean cnSplitDNS,String directCIDRs,String physicalDnsIPv4,int nativeHealthSeconds){
        boolean nativeReady=false,uidReady=false,readyRecorded=false;
        boolean tunConfigured=false,rawReady=false,synackSeen=false,leaseReadback=false;
        boolean coldSynTxRecorded=false,coldUntrustedRSTSeen=false;
        try{
            // The app-private Android file mode is checked BEFORE asking su
            // to exec the real Go ELF. No secret bytes enter receipts.
            try{
                RootPrivateCredentialFiles.verifyAtStart(this,hasCA);
                trace(RootDiagnosticReceipt.Event.APP_PRIVATE_CREDENTIALS_0600_VERIFIED);
            }catch(Exception privateFileFailure){
                trace(RootDiagnosticReceipt.Event.APP_PRIVATE_CREDENTIALS_UNSAFE);
                throw privateFileFailure;
            }
            NativePayload code=NativePayload.stage(this);
            ownerExecutable=code.executableName;
            trace(RootDiagnosticReceipt.Event.NATIVE_SOURCE_VERIFIED);
            if(PhysicalNetwork.exact(this,net.handle,net.interfaceName,net.ifindex,
                  net.mtu,net.address)==null){
                throw new IllegalStateException("physical Android Network changed during staging");
            }
            // B28: only when Android does NOT validate this LAN as
            // Internet, resolve peer hostname using the SELECTED
            // Network's local DNS (off UI, before Root), not netd default.
            // The original Go FakeTCP/TLS gets a literal --peer-ip;
            // its protected SessionID SNI, credentials, M3/PN unchanged.
            // A configured physical DNS server belongs to this selected Network.
            // Let original Go resolve the hostname on its already-bound
            // UDP/TCP53 socket rather than first consulting Android netd.
            final String peerForGo=!RootPhysicalDNSUpstream.DEFAULT.equals(physicalDnsIPv4)
                &&!ServerAddress.isIPv4Literal(peer)
                ?peer:PhysicalNetwork.coldPeerIPv4(this,net,peer);
            status="ROOT_STARTING — exact native SOURCE "+code.source.substring(0,12);
            Process p;
            synchronized(ownerLaunchLock){
                if(stopping.get())
                    throw new IllegalStateException("Root launch withdrawn before native start");
                if(!(allApps
                   ? AllAppRouteScope.same(this,excludedAppIDs,managerPackages,
                       bypassPackages,bypassUIDs)
                   : InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids)))
                    throw new IllegalStateException("Verified Android UID scope changed before Root grant");
                trace(RootDiagnosticReceipt.Event.ROOT_GRANT_REQUESTED);
                p=new ProcessBuilder("su","-c",
                    launchCommand(code,net,peerForGo,sni,user,port,requestedOuterMTU,recordCipher,requestedTunQueue,paddingMode,fecMode,fecProfile,targetUids,allApps,excludedAppIDs,hasCA,verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,ownerToken,directCIDRs,physicalDnsIPv4,nativeHealthSeconds))
                    .redirectErrorStream(true).start();
                root=p;
                trace(RootDiagnosticReceipt.Event.ROOT_PROCESS_LAUNCHED);
            }
            if(stopping.get())signalRootStopIfStarted();
            try(BufferedReader lines=new BufferedReader(
                new InputStreamReader(p.getInputStream()))){
                String line;
                while((line=lines.readLine())!=null){
                    if(line.length()>4096)line=line.substring(0,4096);
                    int forensic=line.indexOf("V4_PUBLIC_ANDROID_M4_DIAG role=client kind=");
                    if(forensic>=0&&diagnostics!=null)
                        diagnostics.recordNativeSnapshot(line.substring(forensic));
                    int dnsB6=line.indexOf("V4_PUBLIC_ANDROID_DNS_B6_DIAG role=client ");
                    if(dnsB6>=0&&diagnostics!=null)
                        diagnostics.recordDNSB6Snapshot(line.substring(dnsB6));
                    // B20: native FEC revision is read from the same
                    // original Go session, not the user's UI selection.
                    String fecBrief=RootFecStateBrief.fromGoLine(line);
                    if(fecBrief!=null)fecStatus=fecBrief;
                    // Fixed allowlisted shell/Go entry markers expose only
                    // proven pre-TUN boundaries, never stderr, argv or keys.
                    if(OriginalGoMilestones.matches(line,"WBD_PUBLIC_ROOT_SHELL_ENTERED"))
                        trace(RootDiagnosticReceipt.Event.ROOT_SHELL_ENTERED);
                    if(OriginalGoMilestones.matches(line,"WBD_PUBLIC_ROOT_UID_VERIFIED"))
                        trace(RootDiagnosticReceipt.Event.ROOT_SHELL_ROOT_UID_VERIFIED);
                    if(OriginalGoMilestones.matches(line,"WBD_PUBLIC_ROOT_PRIVATE_DIR_VERIFIED"))
                        trace(RootDiagnosticReceipt.Event.ROOT_SHELL_PRIVATE_DIR_VERIFIED);
                    if(OriginalGoMilestones.matches(line,"WBD_PUBLIC_ROOT_OWNER_GUARD_PASSED"))
                        trace(RootDiagnosticReceipt.Event.ROOT_SHELL_OWNER_GUARD_PASSED);
                    if(OriginalGoMilestones.matches(line,"WBD_PUBLIC_ROOT_NATIVE_FILES_STAGED"))
                        trace(RootDiagnosticReceipt.Event.ROOT_SHELL_NATIVE_FILES_STAGED);
                    if(OriginalGoMilestones.matches(line,"WBD_PUBLIC_ROOT_OWNER_PID_WRITTEN"))
                        trace(RootDiagnosticReceipt.Event.ROOT_SHELL_OWNER_PID_WRITTEN);
                    if(OriginalGoMilestones.matches(line,"WBD_PUBLIC_ROOT_EXEC_ATTEMPTED"))
                        trace(RootDiagnosticReceipt.Event.ROOT_SHELL_EXEC_ATTEMPTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ENTRY role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_ENTRY);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_REJECTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=FLAG_SYNTAX"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_FLAG_SYNTAX);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=PASSWORD_FILE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_PASSWORD_FILE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ROUTE_KEY_FILE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_ROUTE_KEY_FILE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ROUTE_KEY_VALUE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_ROUTE_KEY_VALUE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=INSTALLATION_ID"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_INSTALLATION_ID);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=CN_GEOSITE_FILE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_CN_GEOSITE_FILE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=TLS_CA_FILE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_TLS_CA_FILE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ALL_APP_EXCLUSIONS"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_ALL_APP_EXCLUSIONS);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ANDROID_NETWORK_SCOPE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_ANDROID_NETWORK_SCOPE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=PEER_ADDRESS"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_PEER_ADDRESS);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=REQUIRED_COLD_SETTINGS"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_REQUIRED_COLD_SETTINGS);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=POLICY"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_POLICY);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=OTHER"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PARSE_OTHER);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_ARGS_ACCEPTED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_ARGS_ACCEPTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_INTERFACE_FOUND role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_INTERFACE_FOUND);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_TUN_OPEN_ATTEMPTED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_OPEN_ATTEMPTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_GO_TUN_OPENED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_OPENED);
                    // ORIGINAL-Go emits these only AFTER true TLS lease
                    // kernel readback, Rust M4 handoff or successful joined
                    // cleanup. We record no variable part of native stdout.
                    if(!tunConfigured&&OriginalGoMilestones.matches(
                        line,"V4_PUBLIC_TUN_TXQLEN role=client")){
                        tunConfigured=true;
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_KERNEL_CONFIGURED);
                    }
                    if(!rawReady&&OriginalGoMilestones.matches(
                        line,"V4_PUBLIC_RAW_AF_PACKET_READY role=client")){
                        rawReady=true;
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_RAW_SOCKET_READY);
                    }
                    // Fixed categories emitted from the unchanged original
                    // ClientAssociation.Start()/Sendto path: NEVER raw stderr,
                    // IP, UID, route key, TLS transcript or credential bytes.
                    if(!coldSynTxRecorded){
                        RootDiagnosticReceipt.Event synEvent=null;
                        if(OriginalGoMilestones.matches(line,
                            "V4_PUBLIC_ANDROID_COLD_SYN_TX_OK role=client")){
                            synEvent=RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_OK;
                        }else if(OriginalGoMilestones.matches(line,
                            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=permission_denied")){
                            synEvent=RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_PERMISSION_DENIED;
                        }else if(OriginalGoMilestones.matches(line,
                            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=network_unreachable")){
                            synEvent=RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_NETWORK_UNREACHABLE;
                        }else if(OriginalGoMilestones.matches(line,
                            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=invalid_argument")){
                            synEvent=RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_INVALID_ARGUMENT;
                        }else if(OriginalGoMilestones.matches(line,
                            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=source_unavailable")){
                            synEvent=RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_SOURCE_UNAVAILABLE;
                        }else if(OriginalGoMilestones.matches(line,
                            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=buffer_pressure")){
                            synEvent=RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_BUFFER_PRESSURE;
                        }else if(OriginalGoMilestones.matches(line,
                            "V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=other")){
                            synEvent=RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_SYN_TX_OTHER_FAILURE;
                        }
                        if(synEvent!=null){
                            coldSynTxRecorded=true;
                            trace(synEvent);
                        }
                    }
                    if(!coldUntrustedRSTSeen&&OriginalGoMilestones.matches(
                        line,"V4_PUBLIC_ANDROID_COLD_UNAUTH_RST_RX role=client")){
                        coldUntrustedRSTSeen=true;
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_UNAUTH_RST_RX);
                    }
                    if(!synackSeen&&OriginalGoMilestones.matches(
                        line,"V4_PUBLIC_ACTUAL_PEER_SYNACK_MSS_V1 side=client")){
                        synackSeen=true;
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TCP_SYNACK_SEEN);
                    }
                    // A33: ORIGINAL Go emits each marker at its actual cold
                    // boundary. The Java Service never performs TLS itself.
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_ORIGINAL_ASSOC_ESTABLISHED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_ASSOC_ESTABLISHED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_PRODUCT_FAILED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_PRODUCT_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_PRODUCT_PREPARED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_PRODUCT_PREPARED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_ATTEMPTED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=TIMEOUT"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_TIMEOUT);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=CERTIFICATE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CERTIFICATE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_REASON role=client class=UNKNOWN_AUTHORITY"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_REASON_UNKNOWN_AUTHORITY);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_REASON role=client class=HOSTNAME_MISMATCH"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_REASON role=client class=EXPIRED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_REASON_EXPIRED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_REASON role=client class=NOT_YET_VALID"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_REASON_NOT_YET_VALID);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_REASON role=client class=INCOMPATIBLE_USAGE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_REASON_INCOMPATIBLE_USAGE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_REASON role=client class=INVALID_CERTIFICATE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_REASON_INVALID_CERTIFICATE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_REASON role=client class=OTHER_CERTIFICATE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_REASON_OTHER_CERTIFICATE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_VERIFY_MODE role=client class=DISABLED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_VERIFY_DISABLED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_VERIFY_MODE role=client class=ENABLED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_VERIFY_ENABLED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_VERIFY_EFFECTIVE role=client class=DISABLED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_DISABLED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_CERT_VERIFY_EFFECTIVE role=client class=ENABLED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_ENABLED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_TRUST_SOURCE role=client class=OS_STORE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_TRUST_SOURCE_OS_STORE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_TRUST_SOURCE role=client class=APP_PEM"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_TRUST_SOURCE_APP_PEM);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=PEER_CLOSED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_PEER_CLOSED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=OTHER"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_BOOTSTRAP_PAYLOAD_TX_OK role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RAW_PEER_PAYLOAD_RX role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_BOOTSTRAP_PAYLOAD_TX_NOT_OBSERVED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_NOT_OBSERVED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RAW_PEER_PAYLOAD_RX_NOT_OBSERVED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX_NOT_OBSERVED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_BOOTSTRAP_RTO_OBSERVED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_BOOTSTRAP_RTO_OBSERVED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=DEADLINE_ELAPSED_OTHER"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_DEADLINE_ELAPSED_OTHER);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=CANCELLED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_CANCELLED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=BOOTSTRAP_CLOSED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_BOOTSTRAP_CLOSED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_READY role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_READY);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_RECOVERED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_RECOVERED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_MATCHED_RST_DROP role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_MATCHED_RST_DROP);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_NO_RST_DROP role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_NO_RST_DROP);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_COUNTER_UNAVAILABLE role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_COUNTER_UNAVAILABLE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_STOP_CLEARED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_STOP_CLEARED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_STOP_UNVERIFIED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_STOP_UNVERIFIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=SCOPE_CONFLICT"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_FAILED_SCOPE_CONFLICT);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=OWNER_LOCKED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_FAILED_OWNER_LOCKED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=JOURNAL_UNSAFE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_FAILED_JOURNAL_UNSAFE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=READBACK_MISMATCH"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_FAILED_READBACK_MISMATCH);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=CLEANUP_UNVERIFIED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_FAILED_CLEANUP_UNVERIFIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_COLD_RST_GUARD_FAILED role=client class=IPTABLES_UNAVAILABLE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_COLD_RST_GUARD_FAILED_IPTABLES_UNAVAILABLE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_VERIFIED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REQUEST_WRITE_FAILED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REQUEST_WRITE_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REQUEST_WRITE_OK role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REQUEST_WRITE_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REPLY_FAILED role=client class=TIMEOUT"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_TIMEOUT);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REPLY_FAILED role=client class=AUTH_REJECTED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_AUTH_REJECTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REPLY_FAILED role=client class=VERSION_REJECTED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_VERSION_REJECTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REPLY_FAILED role=client class=PEER_CLOSED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_PEER_CLOSED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REPLY_FAILED role=client class=POLICY_REJECTED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_POLICY_REJECTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REPLY_FAILED role=client class=OTHER"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_FAILED_OTHER);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_PROTECTED_REPLY_PARSED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_PROTECTED_REPLY_PARSED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_ADMISSION_VERIFIED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_ADMISSION_VERIFIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=COLD_OK"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_COLD_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=DETACH_OK"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_DETACH_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=NATIVE_COMMIT_OK"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_NATIVE_COMMIT_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=LEASE_FIELD_OK"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_LEASE_FIELD_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=LEASE_OS_OK"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_LEASE_OS_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=NATIVE_IP_BOUND"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_NATIVE_IP_BOUND);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=UNDERLAY_OK"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_UNDERLAY_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=RAW_ATTACHED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_RAW_ATTACHED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=TUN_ATTACHED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_TUN_ATTACHED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=TUNNEL_DNS_ENABLED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_ENABLED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=TUNNEL_DNS_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=PHYSICAL_DNS_ENABLED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_PHYSICAL_DNS_ENABLED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=PHYSICAL_DNS_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_PHYSICAL_DNS_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=CN_DNS_SPLIT_ENABLED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_CN_DNS_SPLIT_ENABLED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=CN_DNS_SPLIT_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_CN_DNS_SPLIT_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=M4_STARTED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_M4_STARTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=COLD_RTO_STOP_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_COLD_RTO_STOP_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=DETACH_STATE_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_DETACH_STATE_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=GO_RX_FILTER_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_GO_RX_FILTER_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=GO_RX_FILTER_OK"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_GO_RX_FILTER_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=GO_RX_HANDOFF_OK"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_GO_RX_HANDOFF_OK);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=UID_ROUTE_ENTERED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_UID_ROUTE_ENTERED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=COLD_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_COLD_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=DETACH_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_DETACH_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=NATIVE_PREPARE_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_NATIVE_PREPARE_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=NATIVE_COMMIT_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_NATIVE_COMMIT_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=NATIVE_OTHER_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_NATIVE_OTHER_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=LEASE_FIELD_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_LEASE_FIELD_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=LEASE_ADD_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_LEASE_ADD_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=LEASE_DEL_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_LEASE_DEL_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=LEASE_READBACK_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_LEASE_READBACK_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=LEASE_MISMATCH"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_LEASE_MISMATCH);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=LEASE_OS_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_LEASE_OS_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=NATIVE_IP_BIND_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_NATIVE_IP_BIND_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=MTU_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_MTU_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=UNDERLAY_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_UNDERLAY_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=RAW_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_RAW_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=TUN_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_TUN_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=HEALTH_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_HEALTH_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=M4_START_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_M4_START_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_POSTAUTH role=client class=UID_ROUTE_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_POSTAUTH_UID_ROUTE_FAILED);
                    if(!leaseReadback&&OriginalGoMilestones.matches(
                        line,"V4_PUBLIC_LEASE_APPLIED role=client")){
                        leaseReadback=true;
                        trace(RootDiagnosticReceipt.Event.AUTHENTICATED_LEASE_OS_READBACK);
                    }
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_GO_RX_HANDOFF role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_RUST_HANDOFF);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_UID_ROUTE_STOP_DRAINED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_NATIVE_STOP_DRAINED role=client"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_RUST_STOP_JOINED);
                    if(OriginalGoMilestones.matches(line,
                        "V4_PUBLIC_ANDROID_PEER_THROW_ROUTE_READBACK role=client")){
                        trace(RootDiagnosticReceipt.Event.SERVER_PEER_THROW_PRIVATE_FIB_READBACK);
                    }
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=TUN_IPV4_SEEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_TUN_IPV4_SEEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=TUN_IPV4_REJECTED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_TUN_IPV4_REJECTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=APP_RAW_TX_COPIED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_APP_RAW_TX_COPIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=APP_REVERSE_TUN_WRITTEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_APP_REVERSE_TUN_WRITTEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_UDP53_TUN_SEEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_UDP53_TUN_SEEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_TCP53_TUN_SEEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_TCP53_TUN_SEEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_TUNNEL_RAW_COPIED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_TUNNEL_RAW_COPIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_TUNNEL_REVERSE_TUN_WRITTEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_TUNNEL_REVERSE_TUN_WRITTEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_PHYSICAL_UDP_COPIED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_PHYSICAL_UDP_COPIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_PHYSICAL_REVERSE_TUN_WRITTEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_PHYSICAL_REVERSE_TUN_WRITTEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_PHYSICAL_ERROR"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_PHYSICAL_ERROR);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_CN_PHYSICAL_SENT"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_CN_PHYSICAL_SENT);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_NONCN_TUNNEL_RAW_COPIED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_NONCN_TUNNEL_RAW_COPIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_TCP53_ORIGINAL_RAW_COPIED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_TCP53_ORIGINAL_RAW_COPIED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=DNS_PHYSICAL_TC_REPLY_TUN_WRITTEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_DNS_PHYSICAL_TC_REPLY_TUN_WRITTEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_UID_ROUTE_GET role=client class=MATCHED_TUN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_UID_ROUTE_GET_MATCHED_TUN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_UID_ROUTE_GET role=client class=MISMATCH"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_UID_ROUTE_GET_MISMATCH);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_UID_ROUTE_GET role=client class=UNAVAILABLE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_UID_ROUTE_GET_UNAVAILABLE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=RAW_SOCKET_READABLE"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_RAW_SOCKET_READABLE);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=RAW_PARSE_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_RAW_PARSE_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=RAW_PARSED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_RAW_PARSED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=RAW_AUTHENTICATED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_RAW_AUTHENTICATED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=RAW_AUTH_REJECTED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_RAW_AUTH_REJECTED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=REVERSE_TUN_WRITE_FAILED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_REVERSE_TUN_WRITE_FAILED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=TUN_ICMP_SEEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_TUN_ICMP_SEEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=TUN_TCP_SEEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_TUN_TCP_SEEN);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_BUSINESS role=client class=TUN_UDP_SEEN"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_RUST_TUN_UDP_SEEN);
                    if(!uidReady&&OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED")){
                        uidReady=true;
                        trace(RootDiagnosticReceipt.Event.UID_ROUTE_RECEIPT);
                    }
                    if(!nativeReady&&OriginalGoMilestones.matches(line,"V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client")){
                        nativeReady=true;
                        trace(RootDiagnosticReceipt.Event.NATIVE_M4_RECEIPT);
                    }
                    if(uidReady&&nativeReady&&!stopping.get()&&!readyRecorded){
                        readyRecorded=true;
                        trace(RootDiagnosticReceipt.Event.NATIVE_M4_AND_UID_READY);
                        status="NATIVE_M4_READY + VERIFIED_UID_ROUTE_READBACK; real Android traffic unverified";
                    }
                    // Deliberately don't echo username, auth errors, route
                    // key, password, TLS transcript or full native stdout.
                }
            }
            int exit=p.waitFor();
            trace(exit==0?RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_ZERO:
                RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            if(exit==1)trace(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_1);
            if(exit==139)trace(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_139);
            if(exit==132)trace(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_132);
            if(exit!=0&&!rawReady)
                trace(RootDiagnosticReceipt.Event.ROOT_EXIT_BEFORE_GO_RAW);
            if(exit!=0&&coldSynTxRecorded&&!synackSeen)
                trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_EXIT_BEFORE_PEER_SYNACK);
            // Only the LAST observed genuine original-Go stage. Never
            // imply that missing TLS, app packets or joined Stop passed.
            String lastStage=readyRecorded?"NATIVE_UID_READY":
                leaseReadback?"LEASE_OS_READBACK":
                synackSeen?"SYNACK_PRE_AUTH":
                rawReady?"RAW_PRE_SYNACK":
                tunConfigured?"TUN_PRE_RAW":"PRE_TUN";
            status=exit==0
                ?"ORIGINAL_NATIVE_EXITED_ZERO — phone data not independently verified"
                :"ROOT_OR_NATIVE_EXIT_"+exit+" after "+lastStage+
                 " — inspect fixed receipt; Android data unverified";
        }catch(Exception e){
            trace(RootDiagnosticReceipt.Event.ROOT_LAUNCH_FAILED);
            if(e instanceof java.net.UnknownHostException){
                status="LAN_SELECTED_NETWORK_CHANGED — 请检查同链路可达"+
                    "的服务器IPv4，并单独设置TLS SNI；未发起Root/TLS";
            }else{
                status="ROOT_OR_NATIVE_FAILURE: "+e.getClass().getSimpleName()+
                    " (no claimed native readiness)";
            }
        }finally{
            // Original Go parses and retains secrets only in its own
            // authenticated process. Never persist plaintext user password
            // or route key after that process has exited.
            new File(getFilesDir(),"wbd-pass.secret").delete();
            new File(getFilesDir(),"wbd-route.secret").delete();
            root=null;
            selection=null;
            ownerToken=null;
            fecStatus="会话已结束；"+fecStatus;
            running.set(false);
            stopping.set(false);
            stopWatchingPhysicalNetwork();
            stopWatchingSelectedPackage();
            trace(RootDiagnosticReceipt.Event.OWNER_CLEANUP_FINISHED);
            if(!restoring.get()){
                stopForeground(true);
                stopSelf();
            }
        }
    }
    // The Restore button never changes the firewall in Java. It stops
    // the exact old owner, then executes the same signed original-Go ELF
    // with a dedicated recovery-only CLI, no server credentials or SYN.
    private void restoreOwnedRootNetwork(){
        try{
            long until=android.os.SystemClock.elapsedRealtime()+25000;
            while(running.get()&&android.os.SystemClock.elapsedRealtime()<until)
                Thread.sleep(100);
            if(running.get()){
                trace(RootDiagnosticReceipt.Event.ROOT_RESTORE_REFUSED_LIVE_OWNER);
                status="RESTORE REFUSED: original native owner still stopping";
                return;
            }
            NativePayload signed=NativePayload.stage(this);
            String cmd=RootRecoveryCommand.build(signed.executableName,
                signed.client.getAbsolutePath(),signed.engine.getAbsolutePath());
            Process p=new ProcessBuilder("su","-c",cmd)
                .redirectErrorStream(true).start();
            boolean route=false,rst=false,complete=false;
            try(BufferedReader reader=new BufferedReader(
                    new InputStreamReader(p.getInputStream()))){
                String line;
                while((line=reader.readLine())!=null){
                    if(line.length()>4096)line=line.substring(0,4096);
                    if(OriginalGoMilestones.matches(line,
                        "V4_PUBLIC_ANDROID_RESTORE_ROUTE_CLEARED role=client")){
                        route=true;
                        trace(RootDiagnosticReceipt.Event.ROOT_RESTORE_ROUTE_CLEARED);
                    }
                    if(OriginalGoMilestones.matches(line,
                        "V4_PUBLIC_ANDROID_RESTORE_RST_CLEARED role=client")){
                        rst=true;
                        trace(RootDiagnosticReceipt.Event.ROOT_RESTORE_RST_CLEARED);
                    }
                    if(OriginalGoMilestones.matches(line,"WBD_PUBLIC_ROOT_RESTORE_COMPLETE"))
                        complete=true;
                }
            }
            int exit=p.waitFor();
            if(exit==0&&route&&rst&&complete){
                trace(RootDiagnosticReceipt.Event.ROOT_RESTORE_COMPLETE);
                status="RESTORE VERIFIED: WBD-only firewall/UID/private table cleared";
            }else{
                trace(RootDiagnosticReceipt.Event.ROOT_RESTORE_FAILED);
                status="RESTORE NOT VERIFIED — no broad flush; inspect safe TXT";
            }
        }catch(Exception failure){
            trace(RootDiagnosticReceipt.Event.ROOT_RESTORE_FAILED);
            status="RESTORE NOT VERIFIED — exact root owner/journal check failed";
        }finally{
            restoring.set(false);
            stopForeground(true);
            stopSelf();
        }
    }
    private void signalRootStopIfStarted(){
        if(root==null||ownerToken==null||
           !stopSignalDispatched.compareAndSet(false,true))return;
        final String token=ownerToken;
        trace(RootDiagnosticReceipt.Event.STOP_SIGNAL_STARTED);
        new Thread(()->{
            try{
                Process p=new ProcessBuilder("su","-c",RootStopCommand.build(token,ownerExecutable))
                    .redirectErrorStream(true).start();
                try(BufferedReader r=new BufferedReader(
                    new InputStreamReader(p.getInputStream()))){
                    while(r.readLine()!=null){/* bounded pipe drain */}
                }
                int code=p.waitFor();
                if(code!=0){
                    trace(RootDiagnosticReceipt.Event.STOP_SIGNAL_REFUSED);
                    status="STOP_NOT_CONFIRMED ("+code+") — exact root generation/PID check failed";
                    // Do not clear stopping and accidentally reauthorize.
                }else{
                    trace(RootDiagnosticReceipt.Event.STOP_SIGNAL_ACCEPTED);
                }
                // Signal delivery alone is NOT Go/Rust joined Stop.
            }catch(Exception e){
                trace(RootDiagnosticReceipt.Event.STOP_SIGNAL_ERROR);
                status="STOP_NOT_CONFIRMED — unable to signal exact root process";
            }
        },"wbd-root-stop-signal").start();
    }
    private void requestStop(String why){
        if(!running.get()||!stopping.compareAndSet(false,true))return;
        trace(RootDiagnosticReceipt.Event.STOP_REQUESTED);
        status="STOP_REQUESTED ("+why+") — waiting for original Go/Rust joined Stop";
        // Before su launch: runRoot cancels at ownerLaunchLock.
        // During su launch: runRoot signals after root is published.
        signalRootStopIfStarted();
    }
    @Override public void onTaskRemoved(Intent rootIntent){
        requestStop("APP_TASK_REMOVED");
        super.onTaskRemoved(rootIntent);
    }
    @Override public void onDestroy(){
        requestStop("SERVICE_DESTROYED");
        stopWatchingPhysicalNetwork();
        stopWatchingSelectedPackage();
        super.onDestroy();
    }
}
