package org.wbdnext.rootprobe;

import android.app.Activity;
import android.os.Bundle;
import android.os.Process;
import android.os.SystemClock;
import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.util.Log;
import android.widget.TextView;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLParameters;
import javax.net.ssl.TrustManagerFactory;
import java.util.UUID;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

/** Ordinary App's UDP, UDP53, TCP HTTP and real default-Network socket. */
public final class MainstreamActivity extends Activity {
    private static final String TAG="WBD_MAINSTREAM";
    private static final String BIN="/data/local/tmp/wbd-app-native";
    private static final byte[] IP={(byte)198,18,(byte)254,2};
    private TextView label;
    private static String ctx() {
        try(FileInputStream f=new FileInputStream("/proc/self/attr/current")){
            byte[] b=new byte[200];int n=f.read(b);
            return new String(b,0,n,StandardCharsets.UTF_8).trim();
        }catch(Exception e){return "UNAVAILABLE:"+e;}
    }
    private static String token() {
        return UUID.randomUUID().toString().replace("-","");
    }
    private static InetAddress peer() throws Exception {
        return InetAddress.getByAddress(IP);
    }
    private static JSONObject udpEcho(String t) throws Exception {
        byte[] msg=("wbd-app-"+t).getBytes(StandardCharsets.US_ASCII);
        try(DatagramSocket s=new DatagramSocket()) {
            s.setSoTimeout(4500);
            s.send(new DatagramPacket(msg,msg.length,peer(),49492));
            byte[] bytes=new byte[256];
            DatagramPacket r=new DatagramPacket(bytes,bytes.length);
            s.receive(r);
            String got=new String(r.getData(),r.getOffset(),r.getLength(),StandardCharsets.US_ASCII);
            if(!got.equals("wbd-reply-"+t)||!r.getAddress().equals(InetAddress.getByAddress(new byte[]{(byte)198,18,(byte)253,2}))||
               r.getPort()!=49492)throw new IOException("UDP response mismatch: "+got);
            return new JSONObject().put("status","PASS").put("send_bytes",msg.length)
                .put("receive_bytes",r.getLength()).put("payload",got)
                .put("from",r.getAddress().getHostAddress()+":"+r.getPort());
        }
    }
    private static byte[] dnsQuery(String t) throws Exception {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        int id=Integer.parseInt(t.substring(0,4),16);
        out.write((id>>8)&255);out.write(id&255);
        out.write(new byte[]{1,0,0,1,0,0,0,0,0,0});
        for(String part:new String[]{"probe","wbd","test"}){
            byte[] b=part.getBytes(StandardCharsets.US_ASCII);
            out.write(b.length);out.write(b);
        }
        out.write(new byte[]{0,0,1,0,1});
        return out.toByteArray();
    }
    private static JSONObject dns(String t) throws Exception {
        byte[] q=dnsQuery(t);
        try(DatagramSocket s=new DatagramSocket()){
            s.setSoTimeout(4500);
            s.send(new DatagramPacket(q,q.length,peer(),53));
            byte[] b=new byte[512];
            DatagramPacket r=new DatagramPacket(b,b.length);
            s.receive(r);
            int n=r.getLength(),p=r.getOffset();
            boolean ok=n>=q.length+16 && b[p]==q[0] && b[p+1]==q[1] &&
                (b[p+2]&255)==0x81 && (b[p+3]&255)==0x80 &&
                (b[p+6]&255)==0 && (b[p+7]&255)==1 &&
                b[p+n-4]==(byte)198 && b[p+n-3]==18 &&
                b[p+n-2]==(byte)254 && b[p+n-1]==2 &&
                r.getPort()==53 && r.getAddress().equals(peer());
            if(!ok)throw new IOException("invalid real UDP53 DNS answer, bytes="+n);
            return new JSONObject().put("status","PASS").put("query_bytes",q.length)
                .put("response_bytes",n).put("name","probe.wbd.test.")
                .put("answer","198.18.254.2").put("from",r.getAddress().getHostAddress()+":"+r.getPort());
        }
    }
    private static JSONObject tcpHttp(String t) throws Exception {
        try(Socket s=new Socket()){
            s.connect(new InetSocketAddress(peer(),49493),4500);
            s.setSoTimeout(4500);
            byte[] req=("GET /wbd/"+t+" HTTP/1.0\r\nHost: probe.wbd.test\r\n\r\n")
                .getBytes(StandardCharsets.US_ASCII);
            s.getOutputStream().write(req);
            s.getOutputStream().flush();
            byte[] response=new byte[2048];
            int used=0;
            String expect="wbd-ok-"+t;
            while(used<response.length){
                int n=s.getInputStream().read(response,used,response.length-used);
                if(n<0)break;
                used+=n;
                String got=new String(response,0,used,StandardCharsets.US_ASCII);
                if(got.startsWith("HTTP/1.0 200 OK\r\n")&&got.contains("\r\n\r\n"+expect))break;
            }
            String got=new String(response,0,used,StandardCharsets.US_ASCII);
            if(!got.startsWith("HTTP/1.0 200 OK\r\n")||
               !got.contains("\r\n\r\n"+expect)){
                throw new IOException("TCP HTTP reply mismatch: "+got.substring(0,Math.min(got.length(),150)));
            }
            return new JSONObject().put("status","PASS").put("request_bytes",req.length)
                .put("response_bytes",used).put("http_status",200).put("body",expect)
                .put("connected_to","198.18.254.2:49493");
        }
    }
    private JSONObject underlay(String t) throws Exception {
        ConnectivityManager cm=(ConnectivityManager)getSystemService(Context.CONNECTIVITY_SERVICE);
        if(cm==null)throw new IOException("ConnectivityManager absent");
        Network net=cm.getActiveNetwork();
        if(net==null)throw new IOException("Android netd has no default active Network");
        NetworkCapabilities caps=cm.getNetworkCapabilities(net);
        LinkProperties lp=cm.getLinkProperties(net);
        if(caps==null||lp==null||lp.getInterfaceName()==null)
            throw new IOException("active Network has no LinkProperties/capabilities");
        if(!caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET))
            throw new IOException("active Network lacks INTERNET capability");
        String probe="wbd-host-"+t;
        try(Socket s=new Socket()){
            // Actual Android API uses netd fwmark/network selection, not root SO_BINDTODEVICE.
            net.bindSocket(s);
            s.connect(new InetSocketAddress(InetAddress.getByAddress(new byte[]{10,0,2,2}),18317),4500);
            s.setSoTimeout(4500);
            s.getOutputStream().write((probe+"\n").getBytes(StandardCharsets.US_ASCII));
            s.getOutputStream().flush();
            BufferedReader br=new BufferedReader(new InputStreamReader(
                s.getInputStream(),StandardCharsets.US_ASCII));
            String answer=br.readLine();
            if(!("wbd-underlay-ok-"+t).equals(answer))
                throw new IOException("emulator host underlay echo mismatch: "+answer);
            return new JSONObject().put("status","PASS").put("network",net.toString())
                .put("interface",lp.getInterfaceName()).put("routes",lp.getRoutes().size())
                .put("internet_capability",true).put("transport_wifi",
                    caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI))
                .put("transport_ethernet",caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET))
                .put("socket_bound_to_active_network",true)
                .put("destination","10.0.2.2:18317").put("reply",answer);
        }
    }

    /** Real Android netd resolver, not the App's synthetic direct UDP53 server. */
    private JSONObject systemDns() throws Exception {
        ConnectivityManager cm=(ConnectivityManager)getSystemService(Context.CONNECTIVITY_SERVICE);
        Network net=cm==null?null:cm.getActiveNetwork();
        if(net==null)throw new IOException("no active Network for system DNS");
        long start=SystemClock.elapsedRealtime();
        InetAddress[] addrs=net.getAllByName("example.com");
        boolean ipv4=false;
        StringBuilder ips=new StringBuilder();
        for(InetAddress a:addrs){
            if(a instanceof Inet4Address && !a.isAnyLocalAddress() && !a.isLoopbackAddress()){
                ipv4=true;
            }
            if(ips.length()>0)ips.append(',');
            ips.append(a.getHostAddress());
        }
        if(!ipv4)throw new IOException("system network DNS returned no usable IPv4 for example.com: "+ips);
        return new JSONObject().put("status","PASS").put("using_android_network_resolver",true)
            .put("network",net.toString()).put("hostname","example.com")
            .put("has_ipv4",ipv4).put("answer_count",addrs.length)
            .put("addresses",ips.toString())
            .put("elapsed_ms",SystemClock.elapsedRealtime()-start);
    }
    private JSONObject tlsUnderlay(String t) throws Exception {
        ConnectivityManager cm=(ConnectivityManager)getSystemService(Context.CONNECTIVITY_SERVICE);
        Network net=cm==null?null:cm.getActiveNetwork();
        if(net==null)throw new IOException("no active Network for TLS");
        CertificateFactory cf=CertificateFactory.getInstance("X.509");
        Certificate cert;
        try(InputStream in=getAssets().open("wbd-host-tls.der")){
            cert=cf.generateCertificate(in);
        }
        MessageDigest hash=MessageDigest.getInstance("SHA-256");
        byte[] digest=hash.digest(cert.getEncoded());
        StringBuilder hex=new StringBuilder();
        for(byte b:digest)hex.append(String.format(java.util.Locale.ROOT,"%02x",b&0xff));
        KeyStore store=KeyStore.getInstance(KeyStore.getDefaultType());
        store.load(null,null);
        store.setCertificateEntry("ephemeral-ci-host",cert);
        TrustManagerFactory trust=TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        trust.init(store);
        SSLContext ssl=SSLContext.getInstance("TLS");
        ssl.init(null,trust.getTrustManagers(),null);
        try(Socket transport=new Socket()){
            net.bindSocket(transport);
            transport.connect(new InetSocketAddress(InetAddress.getByAddress(new byte[]{10,0,2,2}),18318),4500);
            transport.setSoTimeout(5000);
            try(SSLSocket socket=(SSLSocket)ssl.getSocketFactory().createSocket(
                  transport,"wbd-ci-host.test",18318,true)){
                socket.setSoTimeout(5000);
                SSLParameters params=socket.getSSLParameters();
                params.setEndpointIdentificationAlgorithm("HTTPS");
                socket.setSSLParameters(params);
                socket.startHandshake();
                String version=socket.getSession().getProtocol();
                if(!("TLSv1.3".equals(version)||"TLSv1.2".equals(version)))
                    throw new IOException("TLS version unacceptable: "+version);
                String body="wbd-tls-"+t;
                socket.getOutputStream().write((body+"\n").getBytes(StandardCharsets.US_ASCII));
                socket.getOutputStream().flush();
                BufferedReader in=new BufferedReader(new InputStreamReader(
                    socket.getInputStream(),StandardCharsets.US_ASCII));
                String actual=in.readLine();
                if(!("wbd-tls-ok-"+t).equals(actual))
                    throw new IOException("TLS host nonce mismatch: "+actual);
                return new JSONObject().put("status","PASS").put("protocol",version)
                    .put("cipher_suite",socket.getSession().getCipherSuite())
                    .put("network",net.toString())
                    .put("server_identity_verified",true).put("hostname_verified",true)
                    .put("network_bound_socket",true)
                    .put("certificate_sha256",hex.toString())
                    .put("host","wbd-ci-host.test").put("underlay_ip","10.0.2.2")
                    .put("reply",actual);
            }
        }
    }
    private JSONObject run() throws Exception {
        JSONObject j=new JSONObject();
        int uid=Process.myUid();
        String t=token();
        j.put("schema","android-mainstream-app-kernelsu/v1");
        j.put("app_uid",uid).put("app_context",ctx()).put("target_sdk",getApplicationInfo().targetSdkVersion);
        j.put("token",t);
        j.put("scope","real App UDP+UDP53+TCP into KSU TUN; Android netd active Network to emulator host only");
        java.lang.Process root=null;
        long begin=SystemClock.elapsedRealtime();
        try{
            root=new ProcessBuilder("su","-c",BIN+" appflow-mainstream "+uid+" "+t)
                .redirectErrorStream(true).start();
            java.lang.Process p=root;
            LinkedBlockingQueue<String> q=new LinkedBlockingQueue<>(256);
            StringBuilder log=new StringBuilder();
            Thread reader=new Thread(()->{
                try(BufferedReader in=new BufferedReader(new InputStreamReader(p.getInputStream(),StandardCharsets.UTF_8))){
                    String line;
                    while((line=in.readLine())!=null){
                        synchronized(log){if(log.length()<18000)log.append(line).append('\n');}
                        q.offer(line);
                    }
                }catch(Exception e){q.offer("READER_ERROR:"+e);}
            },"ksu-mainstream-root-output");
            reader.setDaemon(true);reader.start();
            boolean ready=false;
            long deadline=SystemClock.elapsedRealtime()+14000;
            while(SystemClock.elapsedRealtime()<deadline){
                String line=q.poll(400,TimeUnit.MILLISECONDS);
                if(line==null)continue;
                if(line.equals("WBD_APPFLOW_READY "+t)){ready=true;break;}
                if(line.startsWith("WBD_APPFLOW_RESULT "))break;
            }
            j.put("root_ready",ready);
            if(ready){
                try{
                    j.put("udp",udpEcho(t));
                    j.put("dns",dns(t));
                    j.put("tcp",tcpHttp(t));
                    j.put("netd_underlay",underlay(t));
                    j.put("system_dns",systemDns());
                    j.put("tls_underlay",tlsUnderlay(t));
                    // A real App marker confirms the default-network echo was
                    // completed WHILE the independent root TUN UID rule was active.
                    byte[] completed=("wbd-underlay-"+t).getBytes(StandardCharsets.US_ASCII);
                    try(DatagramSocket signal=new DatagramSocket()){
                        signal.send(new DatagramPacket(completed,completed.length,peer(),49494));
                    }
                    j.put("underlay_completion_marker_bytes",completed.length);
                }catch(Exception e){
                    j.put("network_error",e.toString());
                }
            }
            boolean finished=root.waitFor(40,TimeUnit.SECONDS);
            if(!finished){
                root.destroy();
                if(!root.waitFor(2,TimeUnit.SECONDS))root.destroyForcibly();
            }
            reader.join(1100);
            j.put("su_exit",finished?root.exitValue():-1);
            j.put("elapsed_ms",SystemClock.elapsedRealtime()-begin);
            String all;
            synchronized(log){all=log.toString();}
            j.put("root_output",all);
            int i=all.indexOf("WBD_APPFLOW_RESULT ");
            if(i>=0){
                int from=i+"WBD_APPFLOW_RESULT ".length();
                int e=all.indexOf('\n',from);
                JSONObject nativeResult=new JSONObject(all.substring(from,e<0?all.length():e));
                j.put("native",nativeResult);
                JSONObject ev=nativeResult.optJSONObject("evidence");
                JSONObject multi=ev==null?null:ev.optJSONObject("mainstream");
                JSONObject cl=nativeResult.optJSONObject("cleanup");
                boolean pass=ready&&finished&&root.exitValue()==0&&uid>=10000&&
                    "SUPPORTED_IN_SCOPE".equals(nativeResult.optString("status"))&&
                    nativeResult.optInt("root_uid",-1)==0&&nativeResult.optInt("app_uid",-1)==uid&&
                    multi!=null&&"SUPPORTED_IN_SCOPE".equals(multi.optString("status"))&&
                    "SUPPORTED_IN_SCOPE".equals(multi.optJSONObject("dns_udp53").optString("status"))&&
                    "SUPPORTED_IN_SCOPE".equals(multi.optJSONObject("tcp_http").optString("status"))&&
                    "PASS".equals(j.optJSONObject("udp").optString("status"))&&
                    "PASS".equals(j.optJSONObject("dns").optString("status"))&&
                    "PASS".equals(j.optJSONObject("tcp").optString("status"))&&
                    "PASS".equals(j.optJSONObject("netd_underlay").optString("status"))&&
                    j.optJSONObject("system_dns")!=null &&
                    "PASS".equals(j.optJSONObject("system_dns").optString("status"))&&
                    j.optJSONObject("tls_underlay")!=null &&
                    "PASS".equals(j.optJSONObject("tls_underlay").optString("status"))&&
                    multi.optJSONObject("underlay_marker")!=null &&
                    multi.optJSONObject("underlay_marker").optBoolean("real_app_underlay_completed_before_rule_release")&&
                    j.optInt("underlay_completion_marker_bytes",0)>0&&
                    cl!=null&&cl.optBoolean("ok")&&cl.optBoolean("rules_equal")&&
                    cl.optBoolean("routes_equal")&&cl.optBoolean("tun_gone");
                j.put("status",pass?"APP_DNS_TLS_MAINSTREAM_PASS":"APP_DNS_TLS_MAINSTREAM_FAIL");
            }else{
                j.put("status","NO_NATIVE_RESULT");
            }
        }catch(IOException e){
            j.put("status","SU_EXEC_UNAVAILABLE").put("su_error",e.toString());
        }finally{
            if(root!=null)root.destroy();
        }
        return j;
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        label=new TextView(this);
        label.setText("Real KSU mainstream App UDP / DNS / TCP / default network");
        label.setTextSize(15);label.setPadding(20,20,20,20);
        setContentView(label);
        new Thread(()->{
            JSONObject result;
            try{result=run();}catch(Exception e){
                result=new JSONObject();
                try{result.put("status","APP_EXCEPTION").put("error",e.toString());}
                catch(Exception ignored){}
            }
            try(FileOutputStream out=openFileOutput("mainstream-result.json",MODE_PRIVATE)){
                out.write(result.toString(2).getBytes(StandardCharsets.UTF_8));
            }catch(Exception e){Log.e(TAG,"result file",e);}
            String display=result.optString("status");
            Log.i(TAG,display);
            runOnUiThread(()->label.setText(display));
        },"mainstream-real-app-network").start();
    }
}
