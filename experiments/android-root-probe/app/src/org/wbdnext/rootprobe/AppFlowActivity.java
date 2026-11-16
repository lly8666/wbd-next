package org.wbdnext.rootprobe;

import android.app.Activity;
import android.os.Bundle;
import android.os.Process;
import android.os.SystemClock;
import android.util.Log;
import android.widget.TextView;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

/** Real ordinary App DatagramSocket -> narrowly scoped KSU-owned kernel TUN. */
public final class AppFlowActivity extends Activity {
    private static final String TAG="WBD_APP_FLOW";
    private static final String BIN="/data/local/tmp/wbd-app-native";
    private TextView label;
    private static String read(String path) {
        try (FileInputStream in=new FileInputStream(path)) {
            byte[] b=new byte[256];
            int n=in.read(b);
            return n>0?new String(b,0,n,StandardCharsets.UTF_8).trim():"";
        } catch(Exception e){return "UNAVAILABLE:"+e.getClass().getSimpleName();}
    }
    private JSONObject execute() throws Exception {
        JSONObject j=new JSONObject();
        int uid=Process.myUid();
        String token=UUID.randomUUID().toString().replace("-","");
        j.put("schema","android-real-app-uid-tun/v1");
        j.put("app_uid",uid);
        j.put("app_selinux",read("/proc/self/attr/current"));
        j.put("app_pid",Process.myPid());
        j.put("target_sdk",getApplicationInfo().targetSdkVersion);
        j.put("nonce",token);
        j.put("execution_path","real ordinary app DatagramSocket -> exact UID rule -> KSU root-owned TUN");
        long start=SystemClock.elapsedRealtime();
        java.lang.Process root=null;
        try {
            // KSU's real su uses the Manager's explicitly approved app UID.
            root=new ProcessBuilder("su","-c",BIN+" appflow "+uid+" "+token)
                .redirectErrorStream(true).start();
            java.lang.Process p=root;
            LinkedBlockingQueue<String> lines=new LinkedBlockingQueue<>(256);
            StringBuilder raw=new StringBuilder();
            Thread reader=new Thread(()->{
                try (BufferedReader br=new BufferedReader(new InputStreamReader(
                    p.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line=br.readLine())!=null) {
                        synchronized(raw) {
                            if(raw.length()<16000)raw.append(line,0,Math.min(line.length(),16000-raw.length())).append('\n');
                        }
                        lines.offer(line);
                    }
                } catch(Exception e){lines.offer("READER_ERROR "+e);}
            },"ksu-native-output");
            reader.setDaemon(true);reader.start();
            boolean ready=false;
            long deadline=SystemClock.elapsedRealtime()+14000;
            while(SystemClock.elapsedRealtime()<deadline) {
                String line=lines.poll(500,TimeUnit.MILLISECONDS);
                if(line==null)continue;
                if(line.equals("WBD_APPFLOW_READY "+token)){ready=true;break;}
                if(line.startsWith("WBD_APPFLOW_RESULT "))break;
            }
            j.put("root_ready",ready);
            if(ready) {
                byte[] payload=("wbd-app-"+token).getBytes(StandardCharsets.US_ASCII);
                try (DatagramSocket socket=new DatagramSocket()) {
                    InetAddress dest=InetAddress.getByAddress(new byte[]{(byte)198,18,(byte)254,2});
                    socket.send(new DatagramPacket(payload,payload.length,dest,49492));
                    j.put("app_udp_sent_bytes",payload.length);
                    j.put("app_udp_destination","198.18.254.2:49492");
                } catch(Exception e) {
                    j.put("app_udp_error",e.toString());
                }
            }
            boolean finished=root.waitFor(19,TimeUnit.SECONDS);
            if(!finished) {
                root.destroy();
                if(!root.waitFor(2,TimeUnit.SECONDS))root.destroyForcibly();
            }
            reader.join(1200);
            j.put("su_exit",finished?root.exitValue():-1);
            j.put("elapsed_ms",SystemClock.elapsedRealtime()-start);
            String output;
            synchronized(raw){output=raw.toString();}
            j.put("root_output",output);
            int startResult=output.indexOf("WBD_APPFLOW_RESULT ");
            if(startResult<0) {
                j.put("status","APP_ROOT_NO_NATIVE_RESULT");
            } else {
                int from=startResult+"WBD_APPFLOW_RESULT ".length();
                int stop=output.indexOf('\n',from);
                JSONObject nativeReport=new JSONObject(output.substring(from,stop<0?output.length():stop));
                j.put("native",nativeReport);
                JSONObject ev=nativeReport.optJSONObject("evidence");
                JSONObject cleanup=nativeReport.optJSONObject("cleanup");
                boolean verified=ready && finished && root.exitValue()==0 &&
                    uid>=10000 && nativeReport.optInt("app_uid",-1)==uid &&
                    nativeReport.optInt("root_uid",-1)==0 &&
                    "SUPPORTED_IN_SCOPE".equals(nativeReport.optString("status")) &&
                    ev!=null && ev.optBoolean("app_payload_on_tun") &&
                    ("wbd-app-"+token).equals(ev.optString("payload")) &&
                    cleanup!=null && cleanup.optBoolean("ok") &&
                    cleanup.optBoolean("rules_equal") && cleanup.optBoolean("routes_equal") &&
                    cleanup.optBoolean("tun_gone") &&
                    j.optInt("app_udp_sent_bytes",0)>0;
                j.put("status",verified?"APP_UID_TUN_FLOW_PASS":"APP_UID_TUN_FLOW_FAIL");
            }
        } catch(IOException e) {
            j.put("status","SU_EXEC_UNAVAILABLE");
            j.put("su_error",e.toString());
        } finally {
            if(root!=null)root.destroy();
        }
        return j;
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        label=new TextView(this);
        label.setText("App UID "+Process.myUid()+" -> KSU -> owned TUN");
        label.setTextSize(16);
        label.setPadding(24,24,24,24);
        setContentView(label);
        new Thread(()->{
            JSONObject result;
            try {result=execute();}
            catch(Exception e){
                result=new JSONObject();
                try {result.put("status","APP_EXCEPTION");result.put("error",e.toString());}
                catch(Exception ignored){}
            }
            try (FileOutputStream out=openFileOutput("flow-result.json",MODE_PRIVATE)){
                out.write(result.toString(2).getBytes(StandardCharsets.UTF_8));
            } catch(Exception e){Log.e(TAG,"private result write error",e);}
            String display=result.optString("status")+" (app UID "+Process.myUid()+")";
            Log.i(TAG,display);
            runOnUiThread(()->label.setText(display));
        },"normal-app-udp-flow").start();
    }
}
