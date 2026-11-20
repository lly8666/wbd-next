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
    private static final String ROOT="/data/local/tmp/wbd-next-root";
    private static final String CHANNEL="wbd-root-native";
    public static volatile String status="NOT_RUNNING (actual device NOT_QUALIFIED)";
    private final AtomicBoolean running=new AtomicBoolean(false);
    private final AtomicBoolean stopping=new AtomicBoolean(false);
    private final AtomicBoolean stopSignalDispatched=new AtomicBoolean(false);
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
    // Fixed-enum events only. No network endpoint, package name, password,
    // generation token, route key, TLS transcript or raw native stdout.
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
                boolean valid=caps!=null&&
                    caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)&&
                    !caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)&&
                    (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)||
                     caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR));
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
        // Register ALL physical candidates, not only the default network.
        // A different Network's event cannot revoke our selected handle.
        NetworkRequest request=new NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET).build();
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
            if(!running.get())stopSelf(startId);
            return START_NOT_STICKY;
        }
        if(!START.equals(intent.getAction())||!running.compareAndSet(false,true)){
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
            String sni=intent.getStringExtra("sni");
            String user=intent.getStringExtra("user");
            int port=intent.getIntExtra("port",0);
            boolean allApps=intent.getBooleanExtra("all_apps",false);
            int[] targetUids=intent.getIntArrayExtra("target_uids");
            String[] targetPackages=intent.getStringArrayExtra("target_packages");
            int[] excludedAppIDs=intent.getIntArrayExtra("exclude_appids");
            String[] managerPackages=intent.getStringArrayExtra("manager_packages");
            boolean hasCA=intent.getBooleanExtra("has_ca",false);
            boolean validatedScope=allApps
                ? targetUids==null&&targetPackages==null&&
                  AllAppRouteScope.same(this,excludedAppIDs,managerPackages)
                : excludedAppIDs==null&&managerPackages==null&&
                  InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids);
            if(!validatedScope)trace(RootDiagnosticReceipt.Event.START_FAILED_UID_SCOPE);
            if(peer==null||sni==null||user==null||
                !ServerAddress.valid(peer)||
                sni.length()==0||user.length()==0||
                port<1||port>65535||!validatedScope){
                throw new IllegalArgumentException("Verified full-app or selected-app scope changed");
            }
            trace(RootDiagnosticReceipt.Event.APP_UID_GROUP_VERIFIED);
            trace(allApps?RootDiagnosticReceipt.Event.ROUTE_SCOPE_ALL_ORDINARY_APPS_IPV4:
                RootDiagnosticReceipt.Event.ROUTE_SCOPE_SELECTED_APPS_IPV4);
            selection=chosen;
            ownerToken=newOwnerToken();
            watchPhysicalNetwork(chosen);
            watchSelectedPackages(allApps?managerPackages:targetPackages);
            if(PhysicalNetwork.exact(this,chosen.handle,chosen.interfaceName,
                chosen.ifindex,chosen.mtu,chosen.address)==null)
                throw new IllegalStateException("Physical Network changed during callback registration");
            trace(RootDiagnosticReceipt.Event.ROOT_STAGE_REQUESTED);
            status="AUTHORIZING_ROOT — native credentials not yet verified";
            Thread owner=new Thread(()->runRoot(chosen,peer,sni,user,
                port,targetUids,targetPackages,allApps,excludedAppIDs,
                managerPackages,hasCA),"wbd-native-root-owner");
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
                                 String user,int peerPort,int[] targetUids,
                                 boolean allApps,int[] excludedAppIDs,
                                 boolean hasCA,String token){
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
            hasCA?new File(getFilesDir(),"wbd-server-ca.pem").getAbsolutePath():null);
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
                         int port,int[] targetUids,String[] targetPackages,
                         boolean allApps,int[] excludedAppIDs,String[] managerPackages,
                         boolean hasCA){
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
            status="ROOT_STARTING — exact native SOURCE "+code.source.substring(0,12);
            Process p;
            synchronized(ownerLaunchLock){
                if(stopping.get())
                    throw new IllegalStateException("Root launch withdrawn before native start");
                if(!(allApps
                   ? AllAppRouteScope.same(this,excludedAppIDs,managerPackages)
                   : InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids)))
                    throw new IllegalStateException("Verified Android UID scope changed before Root grant");
                trace(RootDiagnosticReceipt.Event.ROOT_GRANT_REQUESTED);
                p=new ProcessBuilder("su","-c",
                    launchCommand(code,net,peer,sni,user,port,targetUids,allApps,excludedAppIDs,hasCA,ownerToken))
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
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=PEER_CLOSED"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_PEER_CLOSED);
                    if(OriginalGoMilestones.matches(line,"V4_PUBLIC_ANDROID_TLS_HANDSHAKE_FAILED role=client class=OTHER"))
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER);
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
            status="ROOT_OR_NATIVE_FAILURE: "+e.getClass().getSimpleName()+
                " (no claimed native readiness)";
        }finally{
            // Original Go parses and retains secrets only in its own
            // authenticated process. Never persist plaintext user password
            // or route key after that process has exited.
            new File(getFilesDir(),"wbd-pass.secret").delete();
            new File(getFilesDir(),"wbd-route.secret").delete();
            root=null;
            selection=null;
            ownerToken=null;
            running.set(false);
            stopping.set(false);
            stopWatchingPhysicalNetwork();
            stopWatchingSelectedPackage();
            trace(RootDiagnosticReceipt.Event.OWNER_CLEANUP_FINISHED);
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
