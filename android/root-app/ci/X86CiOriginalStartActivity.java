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
            if("stop".equals(command)){
                Intent intent=new Intent(this,RootClientService.class);
                intent.setAction(RootClientService.STOP);
                startService(intent);
                event("ORIGINAL_ROOT_SERVICE_STOP_REQUESTED");
                return;
            }
            if(!"start".equals(command))
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
            List<InstalledAppTarget> applications=InstalledAppCatalog.launchable(this);
            if(applications.isEmpty())
                throw new IllegalStateException("no separate installed user App UID");
            SelectedAppGroup uidGroup=SelectedAppGroup.from(
                Collections.singletonList(applications.get(0)),
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
            request.putExtra("has_ca",true);
            startForegroundService(request);
            event("ORIGINAL_ROOT_SERVICE_START_REQUESTED");
        }catch(Exception blocked){
            // Enum only. No raw Exception: may contain IP/UID/credential paths.
            event("ORIGINAL_ROOT_SERVICE_CI_START_BLOCKED");
        }finally{finish();}
    }
}
