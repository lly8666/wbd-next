package org.wbdnext.rootclient;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
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
    private final Handler timer=new Handler(Looper.getMainLooper());
    private volatile Process root;
    private volatile PhysicalNetwork selection;

    private final Runnable networkWatch=new Runnable(){
        @Override public void run(){
            if(running.get()&&!stopping.get()&&selection!=null){
                PhysicalNetwork current=PhysicalNetwork.exact(
                    RootClientService.this,selection.handle,
                    selection.interfaceName,selection.ifindex,
                    selection.mtu,selection.address);
                if(current==null){
                    requestStop("PHYSICAL_NETWORK_LOST — withdrawing UID policy");
                }
            }
            if(running.get())timer.postDelayed(this,1000);
        }
    };
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
            status="AUTHORIZING_ROOT — native credentials not yet verified";
            Thread owner=new Thread(()->runRoot(chosen,peer,sni,user,
                port,uid,hasCA),"wbd-native-root-owner");
            owner.start();
            timer.post(networkWatch);
        }catch(Exception e){
            status="START_REFUSED: "+e.getMessage();
            running.set(false);
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
                                 boolean hasCA){
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
        shell.append("printf '%s %s\\n' \"$$\" \"$native_start\" > \"$p/owner.pid\"; ");
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
            Process p=new ProcessBuilder("su","-c",
                launchCommand(code,net,peer,sni,user,port,uid,hasCA))
                .redirectErrorStream(true).start();
            root=p;
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
            running.set(false);
            stopping.set(false);
            timer.removeCallbacks(networkWatch);
            stopForeground(true);
            stopSelf();
        }
    }
    private static String stopCommand(){
        // Never kill by name/wildcard; only exact root-owned PID + kernel
        // process starttime + real executable identity. GO handles
        // SIGTERM through its existing signal.NotifyContext -> owner Stop.
        return "set -eu; p="+q(ROOT)+"; "+
            "read pid expected < \"$p/owner.pid\"; "+
            "case \"$pid\" in ''|*[!0-9]*) exit 51;; esac; "+
            "test -r \"/proc/$pid/stat\"; "+
            "set -- $(cat \"/proc/$pid/stat\"); "+
            "test \"${22}\" = \"$expected\"; "+
            "actual=$(readlink \"/proc/$pid/exe\"); "+
            "test \"$actual\" = \"$p/wbd-v4-client-arm64\"; "+
            "kill -TERM \"$pid\"";
    }
    private void requestStop(String why){
        if(!running.get()||!stopping.compareAndSet(false,true)){
            return;
        }
        status="STOP_REQUESTED ("+why+") — waiting for original Go/Rust joined Stop";
        new Thread(()->{
            try{
                Process p=new ProcessBuilder("su","-c",stopCommand())
                    .redirectErrorStream(true).start();
                try(BufferedReader r=new BufferedReader(
                    new InputStreamReader(p.getInputStream()))){
                    while(r.readLine()!=null){/* bounded pipe drain */}
                }
                int code=p.waitFor();
                if(code!=0){
                    status="STOP_NOT_CONFIRMED ("+code+") — exact root PID check failed";
                    stopping.set(false);
                }
                // Successful kill(SIGTERM) is NOT a completion receipt;
                // only real original Go/Rust process exit proves join.
            }catch(Exception e){
                status="STOP_NOT_CONFIRMED — unable to signal actual root process";
                stopping.set(false);
            }
        },"wbd-root-stop-signal").start();
    }
    @Override public void onTaskRemoved(Intent rootIntent){
        requestStop("APP_TASK_REMOVED");
        super.onTaskRemoved(rootIntent);
    }
    @Override public void onDestroy(){
        requestStop("SERVICE_DESTROYED");
        timer.removeCallbacks(networkWatch);
        super.onDestroy();
    }
}
