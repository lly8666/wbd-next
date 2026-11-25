package org.wbdnext.testtraffic;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import android.os.Process;

public final class TrafficInstrumentation extends Instrumentation {
    private Bundle args;
    private Activity foreground;
    public static final class Foreground extends Activity {
        @Override protected void onCreate(Bundle state){
            super.onCreate(state);
            android.widget.TextView v=new android.widget.TextView(this);
            v.setText("Ordinary UID traffic test");setContentView(v);
        }
    }
    private void enterForeground()throws Exception{
        android.content.Intent i=new android.content.Intent(getTargetContext(),Foreground.class);
        i.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
        foreground=startActivitySync(i);waitForIdleSync();
        android.app.ActivityManager.RunningAppProcessInfo info=new android.app.ActivityManager.RunningAppProcessInfo();
        for(int n=0;n<30;n++){
            android.app.ActivityManager.getMyMemoryState(info);
            // Read the real window state on its UI thread, not the instrumentation worker.
            final boolean[] focused={false};
            runOnMainSync(()->focused[0]=foreground.hasWindowFocus());
            if(info.importance==android.app.ActivityManager.RunningAppProcessInfo.IMPORTANCE_FOREGROUND
                    &&focused[0]){
                android.util.Log.i("WBD_UID_TEST","B95_FOREGROUND_UID "+Process.myUid()+" importance="+info.importance);
                return;
            }
            android.os.SystemClock.sleep(100);
        }
        throw new IllegalStateException("ordinary foreground admission not proven importance="+info.importance);
    }
    private void finishProbe(int code,Bundle result){
        if(foreground!=null){runOnMainSync(()->foreground.finish());foreground=null;}
        finish(code,result);
    }
    @Override public void onCreate(Bundle arguments){
        super.onCreate(arguments);args=arguments;start();
    }
    // A second real AF_INET UDP socket, independent of Java dual-stack
    // DatagramSocket. Never alter App permissions, fwmark or netd policy.
    private void udp4(String dest,byte[] payload,boolean echo,int count)throws Exception{
        java.io.FileDescriptor fd=android.system.Os.socket(android.system.OsConstants.AF_INET,
            android.system.OsConstants.SOCK_DGRAM,android.system.OsConstants.IPPROTO_UDP);
        try{
            android.system.Os.connect(fd,java.net.InetAddress.getByName(dest),43999);
            for(int n=0;n<count;n++){
                if(android.system.Os.write(fd,payload,0,payload.length)!=payload.length)
                    throw new java.io.IOException("short AF_INET write");
                if(count>1)android.os.SystemClock.sleep(5);
            }
            if(echo){
                android.system.StructPollfd poll=new android.system.StructPollfd();
                poll.fd=fd;poll.events=(short)android.system.OsConstants.POLLIN;
                if(android.system.Os.poll(new android.system.StructPollfd[]{poll},4000)!=1)
                    throw new java.io.IOException("AF_INET UDP echo deadline");
                byte[] reply=new byte[64];int n=android.system.Os.read(fd,reply,0,reply.length);
                if(n!=payload.length||!java.util.Arrays.equals(payload,java.util.Arrays.copyOf(reply,n)))
                    throw new java.io.IOException("AF_INET UDP echo differs");
            }
        }finally{android.system.Os.close(fd);}
    }
    @Override public void onStart(){
        Bundle result=new Bundle();
        try{
            String probe=args.getString("uid_probe","");
            if(!probe.isEmpty()||!args.getString("dns_probe","").isEmpty())enterForeground();
            if("tcp-connect".equals(probe)){
                // Ordinary TCP SYN into selected TUN. No remote peer is
                // available in this fixture; timeout is expected, not E2E.
                try(java.net.Socket socket=new java.net.Socket()){
                    try{socket.connect(new java.net.InetSocketAddress("192.0.2.1",18081),1600);
                        throw new IllegalStateException("unexpected remote TCP connection");
                    }catch(java.net.SocketTimeoutException expected){}
                }
                result.putString("report","uid_probe_sent="+Process.myUid()+" foreground=1 tcp_connect_attempt=1 remote_reply=NOT_PROVEN");
                finishProbe(Activity.RESULT_OK,result);return;
            }
            if("daily-direct".equals(probe)||"daily-tunnel".equals(probe)){
                String report=TrafficProbe.run(args.getString("host"),18080,8,1);
                if(!report.contains("tcp_ok=8 udp_ok=8 samples=8")||!report.contains("echo_bytes_each_direction=1048576"))
                    throw new IllegalStateException("ordinary direct traffic mismatch: "+report);
                result.putString("report","uid_probe_sent="+Process.myUid()+" foreground=1 "+report);
                finishProbe(Activity.RESULT_OK,result);return;
            }
            if("daily4".equals(args.getString("dns_probe"))){
                String transport=args.getString("dns_transport");
                java.io.ByteArrayOutputStream raw=new java.io.ByteArrayOutputStream();
                java.io.DataOutputStream query=new java.io.DataOutputStream(raw);
                query.writeShort(0x6972);query.writeShort(0x0100);query.writeShort(1);
                query.writeShort(0);query.writeShort(0);query.writeShort(0);
                for(String label:args.getString("dns_name").split("\\.")){
                    byte[] b=label.getBytes(java.nio.charset.StandardCharsets.US_ASCII);
                    query.writeByte(b.length);query.write(b);
                }
                query.writeByte(0);query.writeShort(1);query.writeShort(1);
                byte[] q=raw.toByteArray(),answer=null;
                java.net.InetSocketAddress dest=new java.net.InetSocketAddress(args.getString("dns_host","192.0.2.53"),53);
                if("steady".equals(transport)){
                    // Same ordinary UDP socket throughout. Move the actual
                    // Activity to the background midway (not a synthetic
                    // process-state flag); instrumentation may retain its
                    // own OS importance, which is recorded rather than assumed.
                    int backgroundImportance=-1;
                    try(java.net.DatagramSocket s=new java.net.DatagramSocket()){
                        s.connect(dest);s.setSoTimeout(4000);
                        for(int j=0;j<5;j++){
                            if(j==2){
                                final boolean[] moved={false},focused={true};
                                runOnMainSync(()->moved[0]=foreground.moveTaskToBack(true));
                                for(int k=0;k<30;k++){
                                    runOnMainSync(()->focused[0]=foreground.hasWindowFocus());
                                    if(!focused[0])break;
                                    android.os.SystemClock.sleep(100);
                                }
                                if(!moved[0]||focused[0])throw new IllegalStateException("Activity did not move to background");
                                android.app.ActivityManager.RunningAppProcessInfo info=new android.app.ActivityManager.RunningAppProcessInfo();
                                android.app.ActivityManager.getMyMemoryState(info);backgroundImportance=info.importance;
                            }
                            q[1]=(byte)(0x72+j);
                            s.send(new java.net.DatagramPacket(q,q.length,dest));
                            java.net.DatagramPacket packet=new java.net.DatagramPacket(new byte[512],512);
                            s.receive(packet);
                            byte[] a=java.util.Arrays.copyOf(packet.getData(),packet.getLength());
                            if(a.length<16||a[0]!=q[0]||a[1]!=q[1]||(a[2]&128)==0||a[7]!=1||
                               !java.util.Arrays.equals(java.util.Arrays.copyOfRange(a,a.length-4,a.length),new byte[]{(byte)192,0,2,55}))
                                throw new IllegalStateException("steady DNS answer mismatch at "+j);
                            if(j<4)android.os.SystemClock.sleep(4000);
                        }
                    }
                    result.putString("report","dns_probe_uid="+Process.myUid()+" foreground=1 steady_answers=5 background_focus_lost=1 background_importance="+backgroundImportance);
                    android.util.Log.i("WBD_UID_TEST","B103_ACTIVITY_BACKGROUND_IMPORTANCE "+backgroundImportance);
                    finishProbe(Activity.RESULT_OK,result);return;
                }
                if("tcp".equals(transport)){
                    try(java.net.Socket s=new java.net.Socket()){
                        s.connect(dest,4000);s.setSoTimeout(4000);
                        java.io.DataOutputStream out=new java.io.DataOutputStream(s.getOutputStream());
                        out.writeShort(q.length);out.write(q);out.flush();
                        java.io.DataInputStream in=new java.io.DataInputStream(s.getInputStream());
                        answer=new byte[in.readUnsignedShort()];in.readFully(answer);
                    }
                }else{
                    try(java.net.DatagramSocket s=new java.net.DatagramSocket()){
                        s.connect(dest);s.setSoTimeout(4000);
                        s.send(new java.net.DatagramPacket(q,q.length,dest));
                        if(!"send".equals(transport)){
                            java.net.DatagramPacket a=new java.net.DatagramPacket(new byte[512],512);
                            s.receive(a);
                            answer=java.util.Arrays.copyOf(a.getData(),a.getLength());
                        }
                    }
                }
                if(!"send".equals(transport)&&(answer==null||answer.length<16||answer[0]!=q[0]||answer[1]!=q[1]||
                   (answer[2]&128)==0||answer[7]!=1||
                   !java.util.Arrays.equals(java.util.Arrays.copyOfRange(answer,answer.length-4,answer.length),new byte[]{(byte)192,0,2,55})))
                    throw new IllegalStateException("actual DNS answer mismatch");
                result.putString("report","dns_probe_uid="+Process.myUid()+" foreground=1 daily_dns="+transport);
                finishProbe(Activity.RESULT_OK,result);return;
            }
            if("explicit6".equals(args.getString("dns_probe"))){
                String localPort=args.getString("dns_loopback_port","");
                boolean loopback=!localPort.isEmpty();
                int port=loopback?Integer.parseInt(localPort):53;
                android.net.Network network=loopback?null:android.net.Network.fromNetworkHandle(Long.parseUnsignedLong(args.getString("network_handle")));
                java.net.InetAddress dest=java.net.InetAddress.getByName(loopback?"::1":"fd00::53");
                byte[] q=java.util.Base64.getDecoder().decode("mZkBAAABAAAAAAAABnN5c3RlbQd3YmQtYjkxBHRlc3QAAAEAAQ==");
                byte[] answer;
                if("tcp".equals(args.getString("dns_transport"))){
                    try(java.net.Socket s=new java.net.Socket()){
                        if(network!=null)network.bindSocket(s);s.connect(new java.net.InetSocketAddress(dest,port),4000);s.setSoTimeout(4000);
                        java.io.DataOutputStream o=new java.io.DataOutputStream(s.getOutputStream());
                        o.writeShort(q.length);o.write(q);o.flush();
                        java.io.DataInputStream in=new java.io.DataInputStream(s.getInputStream());
                        answer=new byte[in.readUnsignedShort()];in.readFully(answer);
                    }
                }else{
                    try(java.net.DatagramSocket s=new java.net.DatagramSocket(null)){
                        if(network!=null)network.bindSocket(s);s.bind(new java.net.InetSocketAddress(java.net.InetAddress.getByName("::"),0));
                        s.setSoTimeout(4000);s.send(new java.net.DatagramPacket(q,q.length,dest,port));
                        java.net.DatagramPacket a=new java.net.DatagramPacket(new byte[512],512);s.receive(a);
                        answer=java.util.Arrays.copyOf(a.getData(),a.getLength());
                    }
                }
                if(answer.length<16||answer[0]!=q[0]||answer[1]!=q[1]||(answer[2]&128)==0||
                   answer[7]!=1||!java.util.Arrays.equals(java.util.Arrays.copyOfRange(answer,answer.length-4,answer.length),new byte[]{(byte)192,0,2,55}))
                    throw new IllegalStateException("IPv6 DNS exact A answer missing");
                result.putString("report","dns_probe_uid="+Process.myUid()+" foreground=1 dns6_answer=192.0.2.55");
                finishProbe(Activity.RESULT_OK,result);return;
            }
            if("physical-excluded".equals(probe)||"physical-cn".equals(probe)){
                String dest="physical-cn".equals(probe)?args.getString("dest"):"192.0.2.1";
                // Different response bytes from the isolated TUN fixture.
                byte[] question=("WBD_B99_"+Process.myUid()).getBytes(java.nio.charset.StandardCharsets.US_ASCII);
                byte[] expected=("HOST_"+new String(question,java.nio.charset.StandardCharsets.US_ASCII)).getBytes(java.nio.charset.StandardCharsets.US_ASCII);
                try(java.net.DatagramSocket socket=new java.net.DatagramSocket()){
                    socket.setSoTimeout(4000);
                    socket.send(new java.net.DatagramPacket(question,question.length,java.net.InetAddress.getByName(dest),43999));
                    byte[] buf=new byte[128];java.net.DatagramPacket reply=new java.net.DatagramPacket(buf,buf.length);
                    socket.receive(reply);
                    if(!reply.getAddress().getHostAddress().equals(dest)||reply.getPort()!=43999||
                       !java.util.Arrays.equals(expected,java.util.Arrays.copyOf(buf,reply.getLength())))
                        throw new IllegalStateException("physical-only host witness mismatch");
                }
                result.putString("report","uid_probe_sent="+Process.myUid()+" foreground=1 host_witness=1");
                finishProbe(Activity.RESULT_OK,result);return;
            }
            if("mtu-minus".equals(probe)||"mtu-edge".equals(probe)||"mtu-over".equals(probe)){
                int size=Integer.parseInt(args.getString("ip_size"));
                if(size<576||size>1501)throw new IllegalArgumentException("invalid fixture IP size");
                byte[] payload=new byte[size-28];
                java.io.FileDescriptor fd=android.system.Os.socket(android.system.OsConstants.AF_INET,
                    android.system.OsConstants.SOCK_DGRAM,android.system.OsConstants.IPPROTO_UDP);
                try{
                    // Linux IP_MTU_DISCOVER=10, IP_PMTUDISC_DO=2; ordinary socket DF.
                    android.system.Os.setsockoptInt(fd,android.system.OsConstants.IPPROTO_IP,10,2);
                    android.system.Os.connect(fd,java.net.InetAddress.getByName("192.0.2.1"),43999);
                    boolean reject="mtu-over".equals(probe);
                    for(int j=0;j<(reject?1:4);j++){
                        payload[0]=(byte)j;
                        try{
                            if(android.system.Os.write(fd,payload,0,payload.length)!=payload.length)
                                throw new java.io.IOException("short MTU UDP write");
                            if(reject)throw new IllegalStateException("oversize DF datagram unexpectedly accepted");
                        }catch(android.system.ErrnoException error){
                            if(!reject||error.errno!=android.system.OsConstants.EMSGSIZE)throw error;
                            result.putString("report","uid_probe_rejected="+Process.myUid()+" errno=EMSGSIZE foreground=1 ip_size="+size);
                            finishProbe(Activity.RESULT_OK,result);return;
                        }
                    }
                    result.putString("report","uid_probe_sent="+Process.myUid()+" foreground=1 ip_size="+size+" datagrams=4");
                    finishProbe(Activity.RESULT_OK,result);return;
                }finally{android.system.Os.close(fd);}
            }
            if("echo4".equals(probe)||"send4".equals(probe)||"baseline4".equals(probe)||"burst4".equals(probe)){
                String dest="baseline4".equals(probe)?"10.0.2.2":"192.0.2.1";
                udp4(dest,"WBD_B94_UID4".getBytes(java.nio.charset.StandardCharsets.US_ASCII),!"send4".equals(probe)&&!"burst4".equals(probe),"burst4".equals(probe)?32:1);
                result.putString("report","uid_probe_sent="+Process.myUid()+" socket=AF_INET probe="+probe+" foreground=1");
                finishProbe(Activity.RESULT_OK,result);return;
            }
            if("1".equals(probe)||"echo".equals(probe)||"baseline".equals(probe)){
                String dest="baseline".equals(probe)?"10.0.2.2":"192.0.2.1";
                byte[] payload="WBD_B90_UID".getBytes(java.nio.charset.StandardCharsets.US_ASCII);
                try(java.net.DatagramSocket socket=new java.net.DatagramSocket()){
                    socket.send(new java.net.DatagramPacket(payload,payload.length,
                        java.net.InetAddress.getByName(dest),43999));
                    if(!"1".equals(probe)){
                        socket.setSoTimeout(4000);
                        byte[] reply=new byte[64];
                        java.net.DatagramPacket packet=new java.net.DatagramPacket(reply,reply.length);
                        socket.receive(packet);
                        if(packet.getLength()!=payload.length||packet.getPort()!=43999||
                           !packet.getAddress().getHostAddress().equals(dest)||
                           !java.util.Arrays.equals(payload,java.util.Arrays.copyOf(reply,packet.getLength())))
                            throw new IllegalStateException("UID TUN echo mismatch");
                    }
                }
                result.putString("report","uid_probe_sent="+Process.myUid()+" foreground=1");
                finishProbe(Activity.RESULT_OK,result);
                return;
            }
            if("default".equals(args.getString("dns_probe"))){
                // Everyday application API, no explicit Network or socket
                // binding. Unique names make the two UID queries observable.
                String expected=args.getString("expected_ip");
                boolean found=false;
                for(java.net.InetAddress ip:java.net.InetAddress.getAllByName(args.getString("dns_name")))
                    if(expected.equals(ip.getHostAddress()))found=true;
                if(!found)throw new IllegalStateException("default Android Resolver A answer mismatch");
                result.putString("report","dns_probe_uid="+Process.myUid()+" default_dns_answer="+expected+" foreground=1");
                finishProbe(Activity.RESULT_OK,result);return;
            }
            if("system".equals(args.getString("dns_probe"))){
                android.net.Network network=android.net.Network.fromNetworkHandle(
                    Long.parseUnsignedLong(args.getString("network_handle")));
                String expected=args.getString("expected_ip");
                boolean found=false;
                for(java.net.InetAddress ip:network.getAllByName(args.getString("dns_name")))
                    if(expected.equals(ip.getHostAddress()))found=true;
                if(!found)throw new IllegalStateException("Android Resolver A answer mismatch");
                result.putString("report","dns_probe_uid="+Process.myUid()+" dns_answer="+expected+" foreground=1");
                finishProbe(Activity.RESULT_OK,result);
                return;
            }
            String report=TrafficProbe.run(args.getString("host"),
                Integer.parseInt(args.getString("port","18080")),
                Integer.parseInt(args.getString("samples","32")),
                Integer.parseInt(args.getString("mib","4")));
            result.putString("report","uid="+Process.myUid()+" "+report+TrafficProbe.resolve(args.getString("dns","")));
            finishProbe(Activity.RESULT_OK,result);
        }catch(Exception e){
            result.putString("error","uid="+Process.myUid()+" probe="+args.getString("uid_probe","")+" "+e);finishProbe(Activity.RESULT_CANCELED,result);
        }
    }
}
