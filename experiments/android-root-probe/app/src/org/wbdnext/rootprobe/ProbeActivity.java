package org.wbdnext.rootprobe;
import android.app.Activity;
import android.os.Bundle;
import android.os.Process;
import android.os.SystemClock;
import android.util.Log;
import android.widget.TextView;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;
public final class ProbeActivity extends Activity {
  private static final String TAG="WBD_APP_SU";
  private static final String SU="/system/xbin/su";
  private static final String NATIVE="/data/local/tmp/wbd-app-native";
  private TextView text;
  private static String read(String path,int length) {
    try(FileInputStream in=new FileInputStream(path)) {
      byte[] b=new byte[length]; int n=in.read(b);
      return n<0?"":new String(b,0,n,StandardCharsets.UTF_8);
    } catch(Exception e) { return "UNAVAILABLE:"+e.toString(); }
  }
  private JSONObject execute() throws Exception {
    JSONObject j=new JSONObject();
    j.put("schema","android-app-su/v1");
    j.put("app_uid",Process.myUid());
    j.put("app_pid",Process.myPid());
    j.put("app_context",read("/proc/self/attr/current",256).trim());
    j.put("app_status",read("/proc/self/status",3000));
    j.put("target_sdk",getApplicationInfo().targetSdkVersion);
    j.put("su_executable",SU);
    j.put("execution_path","ordinary installed APK app UID -> existing su -c");
    String command="id; cat /proc/self/attr/current; grep '^CapEff:' /proc/self/status; "+
      "if [ \"$(id -u)\" != 0 ]; then exit 43; fi; "+
      NATIVE+" inspect; "+NATIVE+" exercise";
    long start=SystemClock.elapsedRealtime();
    java.lang.Process p=null;
    try {
      p=new ProcessBuilder(SU,"-c",command).redirectErrorStream(true).start();
      final InputStream stream=p.getInputStream();
      final StringBuilder output=new StringBuilder();
      Thread reader=new Thread(()->{
        try(InputStream in=stream) {
          byte[] b=new byte[1024];int n;
          while((n=in.read(b))!=-1)
            if(output.length()<24000)
              output.append(new String(b,0,Math.min(n,24000-output.length()),StandardCharsets.UTF_8));
        } catch(Exception e){output.append("\nREAD_ERROR:").append(e.toString());}
      },"su-reader");
      reader.setDaemon(true);reader.start();
      boolean finished=p.waitFor(30,TimeUnit.SECONDS);
      if(!finished) {
        p.destroy();
        if(!p.waitFor(2,TimeUnit.SECONDS))p.destroyForcibly();
      }
      reader.join(1500);
      String stdout=output.toString();
      j.put("su_exit",finished?p.exitValue():-1);
      j.put("su_stdout_stderr",stdout);
      j.put("elapsed_ms",SystemClock.elapsedRealtime()-start);
      if(!finished)j.put("status","AUTH_TIMEOUT");
      else if(p.exitValue()==0 && stdout.contains("uid=0(") &&
        stdout.contains("\"mode\": \"inspect\"") &&
        stdout.contains("\"mode\": \"exercise\"") &&
        stdout.contains("SUPPORTED_IN_SCOPE"))
          j.put("status","APP_SU_NATIVE_EXERCISE_PASS");
      else if(p.exitValue()==0 && stdout.contains("uid=0("))
          j.put("status","APP_SU_UID0_NATIVE_UNVERIFIED");
      else j.put("status","PERMISSION_DENIED_OR_UNAVAILABLE");
    } catch(IOException e) {
      j.put("status","SU_EXEC_UNAVAILABLE");
      j.put("su_error",e.toString());
    } finally { if(p!=null)p.destroy(); }
    return j;
  }
  @Override public void onCreate(Bundle b) {
    super.onCreate(b);
    text=new TextView(this);
    text.setText("App UID "+Process.myUid()+" requesting installed su");
    text.setTextSize(16); text.setPadding(24,24,24,24);setContentView(text);
    new Thread(()->{
      JSONObject j;
      try{j=execute();}
      catch(Exception e) {
        j=new JSONObject();
        try {j.put("status","APP_EXCEPTION");j.put("error",e.toString());}
        catch(Exception ignored){}
      }
      try(FileOutputStream f=openFileOutput("result.json",MODE_PRIVATE)){
        f.write(j.toString(2).getBytes(StandardCharsets.UTF_8));
      }catch(Exception e){Log.e(TAG,"private result write failed",e);}
      String status=j.optString("status")+" app_uid="+Process.myUid();
      Log.i(TAG,status);
      runOnUiThread(()->text.setText(status));
    },"app-su-request").start();
  }
}
