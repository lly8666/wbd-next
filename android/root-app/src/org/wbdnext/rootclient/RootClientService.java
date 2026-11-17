package org.wbdnext.rootclient;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.net.ConnectivityManager;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
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
    private ConnectivityManager watchedManager;
    private ConnectivityManager.NetworkCallback watchedCallback;
    private NetworkScopeGate watchedGate;

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
            String peer=intent.getStringExtra("peer");
            String sni=intent.getStringExtra("sni");
            String user=intent.getStringExtra("user");
            int port=intent.getIntExtra("port",0);
            int uid=intent.getIntExtra("uid",0);
            boolean hasCA=intent.getBooleanExtra("has_ca",false);
            if(peer==null||sni==null||user==null||
                !peer.matches("[0-9.]{7,15}")||
                sni.length()==0||user.length()==0||
                port<1||port>65535||uid<10000||uid>1999999){
                throw new IllegalArgumentException("Invalid single-app root policy");
            }
            selection=chosen;
            ownerToken=newOwnerToken();
            watchPhysicalNetwork(chosen);
            if(PhysicalNetwork.exact(this,chosen.handle,chosen.interfaceName,
                chosen.ifindex,chosen.mtu,chosen.address)==null)
                throw new IllegalStateException("Physical Network changed during callback registration");
            status="AUTHORIZING_ROOT — native credentials not yet verified";
            Thread owner=new Thread(()->runRoot(chosen,peer,sni,user,
                port,uid,hasCA),"wbd-native-root-owner");
            owner.start();
        }catch(Exception e){
            status="START_REFUSED: "+e.getMessage();
            running.set(false);
            stopWatchingPhysicalNetwork();
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
                                 String user,int peerPort,int targetUid,
                                 boolean hasCA,String token){
        List<String> args=new ArrayList<>();
        String[] fixed={
            "--mode","normal","--auto-ip",
            "--raw-interface",net.interfaceName,
            "--android-network-handle",Long.toUnsignedString(net.handle),
            "--local-ip",net.address,
            "--peer-ip",peer,
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
            "--android-route-uid",Integer.toString(targetUid),
        };
        for(String a:fixed)args.add(q(a));
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
        shell.append("read oldpid oldstart < \"$p/owner.pid\"; ");
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
        shell.append("mv -f \"$p/.client.tmp\" \"$p/wbd-v4-client-arm64\"; ");
        shell.append("mv -f \"$p/.engine.tmp\" \"$p/libwbd_engine.so\"; ");
        // Shell exec preserves $$ + proc stat starttime as real native
        // Go process PID; Stop checks the same exact process, not pkill -f.
        shell.append("set -- $(cat /proc/$$/stat); native_start=${22}; ");
        shell.append("printf '%s %s %s\\n' \"$$\" \"$native_start\" ").append(q(token)).append(" > \"$p/owner.pid\"; ");
        shell.append("chmod 600 \"$p/owner.pid\"; ");
        shell.append("LD_LIBRARY_PATH=\"$p\"; export LD_LIBRARY_PATH; ");
        shell.append("exec \"$p/wbd-v4-client-arm64\" ");
        shell.append(String.join(" ",args));
        return shell.toString();
    }
    private void runRoot(PhysicalNetwork net,String peer,String sni,String user,
                         int port,int uid,boolean hasCA){
        boolean nativeReady=false,uidReady=false;
        try{
            NativePayload code=NativePayload.stage(this);
            if(PhysicalNetwork.exact(this,net.handle,net.interfaceName,net.ifindex,
                  net.mtu,net.address)==null){
                throw new IllegalStateException("physical Android Network changed during staging");
            }
            status="ROOT_STARTING — exact native SOURCE "+code.source.substring(0,12);
            Process p;
            synchronized(ownerLaunchLock){
                if(stopping.get())
                    throw new IllegalStateException("Root launch withdrawn before native start");
                p=new ProcessBuilder("su","-c",
                    launchCommand(code,net,peer,sni,user,port,uid,hasCA,ownerToken))
                    .redirectErrorStream(true).start();
                root=p;
            }
            if(stopping.get())signalRootStopIfStarted();
            try(BufferedReader lines=new BufferedReader(
                new InputStreamReader(p.getInputStream()))){
                String line;
                while((line=lines.readLine())!=null){
                    if(line.length()>4096)line=line.substring(0,4096);
                    if(line.contains("V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED"))
                        uidReady=true;
                    if(line.contains("V4_ORIGINAL_GO_CLIENT_NATIVE_READY"))
                        nativeReady=true;
                    if(uidReady&&nativeReady&&!stopping.get()){
                        status="NATIVE_M4_READY + ONE_UID_ROUTE_READBACK; real phone traffic unverified";
                    }
                    // Deliberately don't echo username, auth errors, route
                    // key, password, TLS transcript or full native stdout.
                }
            }
            int exit=p.waitFor();
            status=exit==0
                ?"ORIGINAL_NATIVE_EXITED_ZERO — phone data not independently verified"
                :"ROOT_OR_NATIVE_EXIT_"+exit+" — route/journal and Stop need inspection";
        }catch(Exception e){
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
            stopForeground(true);
            stopSelf();
        }
    }
    private static String stopCommand(String token){
        // Only signal THIS owner generation, even if a previous Root worker
        // still owns an older pid file after a refused overlapping launch.
        // Wait boundedly only during Stop for the su shell to write owner.pid.
        return "set -eu; p="+q(ROOT)+"; n=0; "+
            "while [ \"$n\" -lt 60 ]; do "+
            "if [ -r \"$p/owner.pid\" ]; then "+
            "read pid expected generation < \"$p/owner.pid\"; "+
            "if [ \"$generation\" = "+q(token)+" ]; then "+
            "case \"$pid\" in ''|*[!0-9]*) exit 51;; esac; "+
            "if [ -r \"/proc/$pid/stat\" ]; then "+
            "set -- $(cat \"/proc/$pid/stat\"); "+
            "if [ \"${22}\" = \"$expected\" ]; then "+
            "actual=$(readlink \"/proc/$pid/exe\"); "+
            "if [ \"$actual\" = \"$p/wbd-v4-client-arm64\" ]; then "+
            "kill -TERM \"$pid\"; exit 0; "+
            "fi; fi; fi; fi; "+
            "n=$((n+1)); sleep 0.2; done; exit 55";
    }
    private void signalRootStopIfStarted(){
        if(root==null||ownerToken==null||
           !stopSignalDispatched.compareAndSet(false,true))return;
        final String token=ownerToken;
        new Thread(()->{
            try{
                Process p=new ProcessBuilder("su","-c",stopCommand(token))
                    .redirectErrorStream(true).start();
                try(BufferedReader r=new BufferedReader(
                    new InputStreamReader(p.getInputStream()))){
                    while(r.readLine()!=null){/* bounded pipe drain */}
                }
                int code=p.waitFor();
                if(code!=0){
                    status="STOP_NOT_CONFIRMED ("+code+") — exact root generation/PID check failed";
                    // Do not clear stopping and accidentally reauthorize.
                }
                // Signal delivery alone is NOT Go/Rust joined Stop.
            }catch(Exception e){
                status="STOP_NOT_CONFIRMED — unable to signal exact root process";
            }
        },"wbd-root-stop-signal").start();
    }
    private void requestStop(String why){
        if(!running.get()||!stopping.compareAndSet(false,true))return;
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
        super.onDestroy();
    }
}
