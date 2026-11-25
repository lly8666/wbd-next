package org.wbdnext.rootclient;

import android.app.Activity;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import java.io.File;
import java.util.Collections;
import java.util.List;

/**
 * CI-ONLY signed x86_64 Android entrypoint for the UNMODIFIED production
 * RootClientService START/STOP. Not present in the ARM64 release APK.
 * No TLS implementation, no TUN reader, no packet loop or UID spoofing.
 * Ephemeral CI credentials are provisioned as 0600 files in the App sandbox.
 */
public final class X86CiOriginalStartActivity extends Activity {
    private static final String TAG="WBD_X86_CI_ORIGINAL";
    private static void event(String token){Log.i(TAG,token);}
    private static boolean isX86App(){
        if(android.os.Process.myUid()<10000)return false;
        for(String abi:Build.SUPPORTED_64_BIT_ABIS)
            if("x86_64".equals(abi))return true;
        return false;
    }
    private boolean privateInput(String filename){
        File dir=getFilesDir();
        File p=new File(dir,filename);
        return p.isFile() && p.canRead() && p.length()>0 && p.length()<65536
            && p.getParentFile().equals(dir);
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        try{
            if(!isX86App())throw new IllegalStateException("CI requires ordinary x86 App UID");
            String command=getIntent().getStringExtra("ci_step");
            if("lifecycle_watch".equals(command)){
                final android.net.ConnectivityManager cm=getSystemService(android.net.ConnectivityManager.class);
                final List<PhysicalNetwork> nets=PhysicalNetwork.available(this);
                if(cm==null||nets.isEmpty())throw new IllegalStateException("no selected Network");
                final long selected=nets.get(0).handle;
                final android.net.ConnectivityManager.NetworkCallback cb=new android.net.ConnectivityManager.NetworkCallback(){
                    @Override public void onLost(android.net.Network n){
                        if(n.getNetworkHandle()==selected)event("B93_SELECTED_NETWORK_LOST");
                    }
                    @Override public void onAvailable(android.net.Network n){
                        event(n.getNetworkHandle()==selected?"B93_SELECTED_NETWORK_AVAILABLE":"B93_OTHER_NETWORK_AVAILABLE");
                    }
                };
                android.net.NetworkRequest req=new android.net.NetworkRequest.Builder()
                    .addTransportType(android.net.NetworkCapabilities.TRANSPORT_WIFI)
                    .addTransportType(android.net.NetworkCapabilities.TRANSPORT_CELLULAR)
                    .addTransportType(android.net.NetworkCapabilities.TRANSPORT_ETHERNET).build();
                cm.registerNetworkCallback(req,cb);
                new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(()->{
                    try{cm.unregisterNetworkCallback(cb);}catch(IllegalArgumentException ignored){}
                },45000);
                event("B93_NETWORK_WATCH_ARMED "+Long.toUnsignedString(selected));
                return;
            }
            if("lifecycle_state".equals(command)){
                event("B92_LIFECYCLE_STATE active="+RootClientService.sessionOwnerActive+
                    " ready="+RootClientService.sessionUiReady+
                    " physical_stop="+RootClientService.networkStopRequested+
                    " old_stop_verified="+RootClientService.previousOwnerStopConfirmed);
                return;
            }
            if("stop".equals(command)){
                Intent intent=new Intent(this,RootClientService.class);
                intent.setAction(RootClientService.STOP);
                startService(intent);
                event("ORIGINAL_ROOT_SERVICE_STOP_REQUESTED");
                return;
            }
            if(!"start".equals(command)&&!"specialty_scope".equals(command))
                throw new IllegalArgumentException("CI exact step required");
            NativePayload.stage(this);
            event("ORIGINAL_SIGNED_GO_RUST_ASSETS_VERIFIED");
            List<PhysicalNetwork> available=PhysicalNetwork.available(this);
            if(available.isEmpty())
                throw new IllegalStateException("no exact physical Network");
            PhysicalNetwork chosen=available.get(0);
            if(PhysicalNetwork.exact(this,chosen.handle,chosen.interfaceName,
                 chosen.ifindex,chosen.mtu,chosen.address)==null)
                throw new IllegalStateException("physical Network changed");
            if("specialty_scope".equals(command)){
                event("B90_SCOPE "+Long.toUnsignedString(chosen.handle)+" "+
                    chosen.interfaceName+" "+chosen.ifindex+" "+chosen.mtu+" "+chosen.address);
                return;
            }
            // CI-only fixed enum: this is the actually selected
            // ConnectivityManager Network interface, not a guessed TAP link.
            if("wlan0".equals(chosen.interfaceName))
                event("CI_SELECTED_PHYSICAL_IFACE_WLAN0");
            else if("eth0".equals(chosen.interfaceName))
                event("CI_SELECTED_PHYSICAL_IFACE_ETH0");
            else event("CI_SELECTED_PHYSICAL_IFACE_OTHER");
            List<InstalledAppTarget> applications=InstalledAppCatalog.discoverable(this);
            InstalledAppTarget ciTarget=null;
            String target="traffic".equals(getIntent().getStringExtra("ci_target"))?
                "org.wbdnext.testtraffic":"org.wbdnext.rootprobe";
            for(InstalledAppTarget app:applications){
                if(target.equals(app.packageName)){
                    ciTarget=app;
                    break;
                }
            }
            // The KernelSU Manager itself must NEVER become a tunnel UID.
            if(ciTarget==null)throw new IllegalStateException("CI target probe App not installed");
            SelectedAppGroup uidGroup=SelectedAppGroup.from(
                Collections.singletonList(ciTarget),
                android.os.Process.myUid(),getPackageName());
            if(!InstalledAppCatalog.stillSameGroup(this,uidGroup.packages,uidGroup.uids))
                throw new IllegalStateException("target app UID changed");
            // Secrets are never Intent extras, application logs or process args.
            if(!privateInput("wbd-pass.secret")||
               !privateInput("wbd-route.secret")||
               !privateInput("wbd-server-ca.pem"))
                throw new IllegalStateException("CI ephemeral private test inputs missing");
            Intent request=new Intent(this,RootClientService.class);
            request.setAction(RootClientService.START);
            request.putExtra("handle",chosen.handle);
            request.putExtra("iface",chosen.interfaceName);
            request.putExtra("index",chosen.ifindex);
            request.putExtra("mtu",chosen.mtu);
            request.putExtra("local",chosen.address);
            // 10.0.2.2 is the Android Emulator's host loopback alias; no
            // public endpoint and no route change beyond the original owner.
            request.putExtra("peer","10.0.2.2");
            request.putExtra("port",443);
            request.putExtra("sni","wbd-v4.example.test");
            request.putExtra("user","wbd-ci-session");
            request.putExtra("target_uids",uidGroup.uids);
            request.putExtra("target_packages",uidGroup.packages);
            // The normal historical fixture uses its CA. Wiring matrix
            // explicitly follows the earlier physical Normal/off defaults.
            String mode=getIntent().getStringExtra("ci_mode");
            boolean verify=mode==null||"traffic".equals(getIntent().getStringExtra("ci_target"));
            if(mode==null)mode="normal";
            if(!java.util.Arrays.asList("normal","fec-fixed","fec-auto","game2",
                "game2-fixed","game4","game4-fixed").contains(mode))
                throw new IllegalArgumentException("unknown CI mode");
            request.putExtra("fec_mode",mode);
            request.putExtra("fec_profile",6);
            request.putExtra("has_ca",verify);
            request.putExtra("tls_verify_server",verify);
            String scenario=getIntent().getStringExtra("ci_scenario");
            request.putExtra("tunnel_dns","tunnel_dns".equals(scenario));
            if("tunnel_dns".equals(scenario))request.putExtra("tunnel_dns_upstream","10.66.0.1");
            request.putExtra("background_network_recovery","auto_reconnect".equals(scenario));
            request.putExtra("physical_dns",false);
            request.putExtra("cn_dns_split",false);
            request.putExtra("outer_repair",false);
            startForegroundService(request);
            event("ORIGINAL_ROOT_SERVICE_START_REQUESTED");
        }catch(Exception blocked){
            // Enum only. No raw Exception: may contain IP/UID/credential paths.
            event("ORIGINAL_ROOT_SERVICE_CI_START_BLOCKED");
        }finally{finish();}
    }
}
