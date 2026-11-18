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
        // One POSIX shell token, including otherwise untrusted CLI labels.
        return "'"+s.replace("'","'\\''")+"'";
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
        try{
            notification();
            long handle=intent.getLongExtra("handle",0);
            String iface=intent.getStringExtra("iface");
            int index=intent.getIntExtra("index",0);
            int mtu=intent.getIntExtra("mtu",0);
            String local=intent.getStringExtra("local");
            if(iface==null||local==null)throw new IllegalStateException("Missing actual Network");
            PhysicalNetwork chosen=PhysicalNetwork.exact(this,handle,iface,index,mtu,local);
            if(chosen==null)throw new IllegalStateException("ConnectivityManager Network changed");
            trace(RootDiagnosticReceipt.Event.NETWORK_SCOPE_VERIFIED);
            String peer=intent.getStringExtra("peer");
            String sni=intent.getStringExtra("sni");
            String user=intent.getStringExtra("user");
            int port=intent.getIntExtra("port",0);
            int[] targetUids=intent.getIntArrayExtra("target_uids");
            String[] targetPackages=intent.getStringArrayExtra("target_packages");
            boolean hasCA=intent.getBooleanExtra("has_ca",false);
            if(peer==null||sni==null||user==null||
                !ServerAddress.valid(peer)||
                sni.length()==0||user.length()==0||
                port<1||port>65535||
               !InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids)){
                throw new IllegalArgumentException("Selected installed package/UID group changed or invalid");
            }
            trace(RootDiagnosticReceipt.Event.APP_UID_GROUP_VERIFIED);
            selection=chosen;
            ownerToken=newOwnerToken();
            watchPhysicalNetwork(chosen);
            watchSelectedPackages(targetPackages);
            if(PhysicalNetwork.exact(this,chosen.handle,chosen.interfaceName,
                chosen.ifindex,chosen.mtu,chosen.address)==null)
                throw new IllegalStateException("Physical Network changed during callback registration");
            trace(RootDiagnosticReceipt.Event.ROOT_STAGE_REQUESTED);
            status="AUTHORIZING_ROOT — native credentials not yet verified";
            Thread owner=new Thread(()->runRoot(chosen,peer,sni,user,
                port,targetUids,targetPackages,hasCA),"wbd-native-root-owner");
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
                                 boolean hasCA,String token){
        List<String> args=new ArrayList<>();
        String serverAddressFlag=ServerAddress.isIPv4Literal(peer)?"--peer-ip":"--peer-host";
        String[] fixed={
            "--mode","normal","--auto-ip",
            "--raw-interface",net.interfaceName,
            "--android-network-handle",Long.toUnsignedString(net.handle),
            "--local-ip",net.address,
            serverAddressFlag,peer,
            "--peer-port",Integer.toString(peerPort),
            "--local-port",Integer.toString(40000+new SecureRandom().nextInt(20000)),
            "--tun-name","wbdv40",
            "--server-name",sni,
            "--username",user,
            "--password-file",new File(getFilesDir(),"wbd-pass.secret").getAbsolutePath(),
            "--route-key-hex-file",new File(getFilesDir(),"wbd-route.secret").getAbsolutePath(),
            "--installation-id-file",new File(getFilesDir(),"wbd-installation-id").getAbsolutePath(),
            "--tun-fq-maxrate-mbps","0",
            "--tun-txqlen-packets","500",
            "--outer-repair","off",
            // Verified CN8503 source is a cold-only admission prerequisite.
            // DNS packets are NOT yet intercepted or forwarded from this
            // Android Root process; this is not a DNS availability flag.
            "--android-cn-geosite-file",nativeCode.cnGeosite.getAbsolutePath(),
        };
        for(String a:fixed)args.add(q(a));
        if(targetUids.length==1){
            args.add(q("--android-route-uid"));
            args.add(q(Integer.toString(targetUids[0])));
        }else{
            args.add(q("--android-route-uids"));
            StringBuilder group=new StringBuilder();
            for(int uid:targetUids){
                if(group.length()>0)group.append(',');
                group.append(uid);
            }
            args.add(q(group.toString()));
        }
        if(hasCA){
            args.add(q("--tls-ca-pem"));
            args.add(q(new File(getFilesDir(),"wbd-server-ca.pem").getAbsolutePath()));
        }
        StringBuilder shell=new StringBuilder("set -eu; umask 077; ");
        shell.append("p=").append(q(ROOT)).append("; ");
        // /data/local/tmp may be writable to shell/other actors.
        // A pre-existing symlink or non-root directory must NEVER be
        // chmod'ed, followed, or used for root binary installation.
        shell.append("test ! -L \"$p\"; ");
        shell.append("if [ ! -e \"$p\" ]; then mkdir -m 700 \"$p\"; fi; ");
        shell.append("test -d \"$p\" && test ! -L \"$p\"; ");
        shell.append("test \"$(stat -c %u \"$p\")\" = 0; ");
        shell.append("test \"$(stat -c %a \"$p\")\" = 700; ");
        // Verify prior root PID is not still live BEFORE replacing a
        // previous owner's lockless cold stage or installing a second TUN.
        shell.append("if [ -f \"$p/owner.pid\" ]; then ");
        shell.append("read oldpid oldstart oldgeneration < \"$p/owner.pid\"; ");
        shell.append("case \"$oldpid\" in ''|*[!0-9]*) exit 43;; esac; ");
        shell.append("if [ -r \"/proc/$oldpid/stat\" ]; then ");
        shell.append("set -- $(cat \"/proc/$oldpid/stat\"); ");
        shell.append("if [ \"${22}\" = \"$oldstart\" ]; then exit 44; fi; ");
        shell.append("fi; fi; ");
        // Every verified asset goes via a root-owned private directory:
        // Android 10+ disallows execution from writable app-private data.
        shell.append("cp ").append(q(nativeCode.client.getAbsolutePath()))
            .append(" \"$p/.client.tmp\"; ");
        shell.append("cp ").append(q(nativeCode.engine.getAbsolutePath()))
            .append(" \"$p/.engine.tmp\"; ");
        shell.append("chmod 700 \"$p/.client.tmp\"; chmod 600 \"$p/.engine.tmp\"; ");
        shell.append("mv -f \"$p/.client.tmp\" \"$p/").append(nativeCode.executableName).append("\"; ");
        shell.append("mv -f \"$p/.engine.tmp\" \"$p/libwbd_engine.so\"; ");
        // Shell exec preserves $$ + proc stat starttime as real native
        // Go process PID; Stop checks the same exact process, not pkill -f.
        shell.append("set -- $(cat /proc/$$/stat); native_start=${22}; ");
        shell.append("printf '%s %s %s\\n' \"$$\" \"$native_start\" ").append(q(token)).append(" > \"$p/owner.pid\"; ");
        shell.append("chmod 600 \"$p/owner.pid\"; ");
        shell.append("LD_LIBRARY_PATH=\"$p\"; export LD_LIBRARY_PATH; ");
        shell.append("exec \"$p/").append(nativeCode.executableName).append("\" ");
        shell.append(String.join(" ",args));
        return shell.toString();
    }
    private void runRoot(PhysicalNetwork net,String peer,String sni,String user,
                         int port,int[] targetUids,String[] targetPackages,boolean hasCA){
        boolean nativeReady=false,uidReady=false,readyRecorded=false;
        boolean tunConfigured=false,rawReady=false,synackSeen=false,leaseReadback=false;
        try{
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
                if(!InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids))
                    throw new IllegalStateException("Selected UID group changed before Root grant");
                trace(RootDiagnosticReceipt.Event.ROOT_GRANT_REQUESTED);
                p=new ProcessBuilder("su","-c",
                    launchCommand(code,net,peer,sni,user,port,targetUids,hasCA,ownerToken))
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
                    if(!synackSeen&&OriginalGoMilestones.matches(
                        line,"V4_PUBLIC_ACTUAL_PEER_SYNACK_MSS_V1 side=client")){
                        synackSeen=true;
                        trace(RootDiagnosticReceipt.Event.ORIGINAL_GO_TCP_SYNACK_SEEN);
                    }
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
                        status="NATIVE_M4_READY + OWNED_UID_GROUP_READBACK; real Android traffic unverified";
                    }
                    // Deliberately don't echo username, auth errors, route
                    // key, password, TLS transcript or full native stdout.
                }
            }
            int exit=p.waitFor();
            trace(exit==0?RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_ZERO:
                RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_NONZERO);
            if(exit==139)trace(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_139);
            if(exit==132)trace(RootDiagnosticReceipt.Event.ROOT_PROCESS_EXIT_132);
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
