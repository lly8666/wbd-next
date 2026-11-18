package org.wbdnext.rootclient;

import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.concurrent.TimeUnit;

/**
 * CI-ONLY Android16 x86_64 test Activity, compiled ONLY into CI test APK.
 * It invokes real KernelSU as this signed controller package's unprivileged
 * App UID. It never authenticates WBD, handles traffic, changes a route,
 * opens a TUN, captures DNS, or claims a production Root Start/Stop.
 */
public final class X86CiAppSuActivity extends Activity {
    private static final String TAG="WBD_X86_CI_APP_SU";
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        new Thread(()->{
            boolean passed=false;
            try{
                boolean abi=false;
                for(String installed:Build.SUPPORTED_64_BIT_ABIS)
                    if("x86_64".equals(installed))abi=true;
                if(!abi||android.os.Process.myUid()<10000)
                    throw new IllegalStateException("not ordinary x86 App UID");
                // This is EXACTLY the production native source/SHA/provenance
                // checker, not a test-only hash bypass or independent payload.
                NativePayload.stage(this);
                Log.i(TAG,"ORIGINAL_SIGNED_NATIVE_ASSETS_VERIFIED");
                Process p=new ProcessBuilder("su","-c","id -u")
                    .redirectErrorStream(true).start();
                if(p.waitFor(110,TimeUnit.SECONDS)){
                    String identity;
                    try(BufferedReader reader=new BufferedReader(
                        new InputStreamReader(p.getInputStream()))){
                        identity=reader.readLine();
                    }
                    passed=p.exitValue()==0&&"0".equals(identity);
                }else{
                    p.destroy();
                }
            }catch(Exception ignored){
                // Never print subprocess output, package identity or secrets.
            }finally{
                Log.i(TAG,passed?"APP_UID_SU_PASS":"APP_UID_SU_NOT_PROVEN");
                runOnUiThread(()->finish());
            }
        },"wbd-x86-ci-app-su-only").start();
    }
}
