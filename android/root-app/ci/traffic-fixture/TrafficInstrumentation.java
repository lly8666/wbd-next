package org.wbdnext.testtraffic;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import android.os.Process;

public final class TrafficInstrumentation extends Instrumentation {
    private Bundle args;
    @Override public void onCreate(Bundle arguments){
        super.onCreate(arguments);args=arguments;start();
    }
    @Override public void onStart(){
        Bundle result=new Bundle();
        try{
            if("1".equals(args.getString("uid_probe"))){
                byte[] payload="WBD_B90_UID".getBytes(java.nio.charset.StandardCharsets.US_ASCII);
                try(java.net.DatagramSocket socket=new java.net.DatagramSocket()){
                    socket.send(new java.net.DatagramPacket(payload,payload.length,
                        java.net.InetAddress.getByName("192.0.2.1"),43999));
                }
                result.putString("report","uid_probe_sent="+Process.myUid());
                finish(Activity.RESULT_OK,result);
                return;
            }
            String report=TrafficProbe.run(args.getString("host"),
                Integer.parseInt(args.getString("port","18080")),
                Integer.parseInt(args.getString("samples","32")),
                Integer.parseInt(args.getString("mib","4")));
            result.putString("report","uid="+Process.myUid()+" "+report+TrafficProbe.resolve(args.getString("dns","")));
            finish(Activity.RESULT_OK,result);
        }catch(Exception e){
            result.putString("error",e.toString());finish(Activity.RESULT_CANCELED,result);
        }
    }
}
