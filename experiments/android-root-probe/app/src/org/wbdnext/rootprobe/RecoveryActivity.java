package org.wbdnext.rootprobe;
import android.app.Activity;
import android.os.Bundle;
import android.os.Process;
import android.os.SystemClock;
import android.util.Log;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

/** Explicit user click, never automatic recovery on App launch.
 * Only the older WBD-owned /32 rule on the disposable AVD can be removed.
 * Real phones require a durable owned-rule journal and physical validation.
 */
public final class RecoveryActivity extends Activity {
    private static final String TAG="WBD_RECOVERY";
    private static final String BIN="/data/local/tmp/wbd-app-native";
    private Button button;
    private TextView label;
    private JSONObject performRecovery() throws Exception {
        JSONObject j=new JSONObject();
        int uid=Process.myUid();
        j.put("schema","wbd-explicit-restore/v1");
        j.put("app_uid",uid);
        j.put("target_sdk",getApplicationInfo().targetSdkVersion);
        j.put("trigger","explicit_user_button");
        j.put("scope","only WBD priority8200 UID /32 table235 on disposable AVD");
        long start=SystemClock.elapsedRealtime();
        java.lang.Process root=null;
        try {
            root=new ProcessBuilder("su","-c",BIN+" recover "+uid)
                .redirectErrorStream(true).start();
            java.lang.Process child=root;
            final StringBuilder raw=new StringBuilder();
            Thread reader=new Thread(()->{
                try(InputStream in=child.getInputStream()){
                    byte[] buf=new byte[1024];int n;
                    while((n=in.read(buf))!=-1){
                        synchronized(raw){
                            if(raw.length()<24000)
                                raw.append(new String(buf,0,Math.min(n,24000-raw.length()),StandardCharsets.UTF_8));
                        }
                    }
                }catch(Exception e){synchronized(raw){raw.append(" READ_ERROR:"+e);}}
            },"wbd-recover-reader");
            reader.setDaemon(true);
            reader.start();
            boolean finished=root.waitFor(18,TimeUnit.SECONDS);
            if(!finished){
                root.destroy();
                if(!root.waitFor(2,TimeUnit.SECONDS))root.destroyForcibly();
            }
            reader.join(1200);
            String output;
            synchronized(raw){output=raw.toString();}
            j.put("su_exit",finished?root.exitValue():-1);
            int index=output.indexOf("WBD_RECOVERY_RESULT ");
            if(!finished)j.put("status","ROOT_TIMEOUT");
            else if(index<0){
                j.put("status","NO_NATIVE_RESULT");
                j.put("log_excerpt",output.substring(0,Math.min(1600,output.length())));
            }else{
                int from=index+"WBD_RECOVERY_RESULT ".length();
                int stop=output.indexOf('\n',from);
                JSONObject nativeReport=new JSONObject(output.substring(from,stop<0?output.length():stop).trim());
                j.put("native",nativeReport);
                boolean verified=root.exitValue()==0 &&
                    nativeReport.optInt("uid",-1)==uid &&
                    nativeReport.optInt("root_uid",-1)==0 &&
                    ("RESTORED".equals(nativeReport.optString("status")) ||
                     "ALREADY_CLEAN".equals(nativeReport.optString("status")));
                j.put("status",verified?nativeReport.optString("status"):"RECOVERY_UNVERIFIED");
            }
        }catch(IOException e){
            j.put("status","SU_UNAVAILABLE");
            j.put("su_error",e.toString());
        }finally{if(root!=null)root.destroy();}
        j.put("elapsed_ms",SystemClock.elapsedRealtime()-start);
        return j;
    }
    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        LinearLayout layout=new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        // This app uses the stock ActionBar theme. A content View at y=24
        // is visually present but the ActionBar intercepts its tap.
        // Keep the physical Button entirely below the ActionBar's y=80.
        layout.setPadding(24,112,24,24);
        label=new TextView(this);
        label.setText("仅清理 WBD 自有规则，不会清空默认路由或修改系统共享。");
        label.setTextSize(16);
        button=new Button(this);
        button.setText("一键恢复正常网络");
        layout.addView(button);
        layout.addView(label);
        setContentView(layout);
        button.setOnClickListener(v->{
            button.setEnabled(false);
            label.setText("检查和清理 owned 网络规则…");
            new Thread(()->{
                JSONObject j;
                try{j=performRecovery();}
                catch(Exception e){
                    j=new JSONObject();
                    try{j.put("status","FAIL");j.put("error",e.toString());}
                    catch(Exception ignored){}
                }
                try(FileOutputStream f=openFileOutput("recovery-result.json",MODE_PRIVATE)){
                    f.write(j.toString(2).getBytes(StandardCharsets.UTF_8));
                }catch(Exception e){Log.e(TAG,"private recovery result write failed",e);}
                String status=j.optString("status","FAIL");
                Log.i(TAG,"explicit recovery status="+status);
                runOnUiThread(()->{label.setText(status);button.setEnabled(true);});
            },"owned-network-recovery").start();
        });
    }
}
