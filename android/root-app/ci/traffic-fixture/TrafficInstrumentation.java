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
    // A second real AF_INET UDP socket, independent of Java dual-stack
    // DatagramSocket. Never alter App permissions, fwmark or netd policy.
    private void udp4(String dest,byte[] payload,boolean echo)throws Exception{
        java.io.FileDescriptor fd=android.system.Os.socket(android.system.OsConstants.AF_INET,
            android.system.OsConstants.SOCK_DGRAM,android.system.OsConstants.IPPROTO_UDP);
        try{
            android.system.Os.connect(fd,java.net.InetAddress.getByName(dest),43999);
            if(android.system.Os.write(fd,payload,0,payload.length)!=payload.length)
                throw new java.io.IOException("short AF_INET write");
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
            if("echo4".equals(probe)||"send4".equals(probe)||"baseline4".equals(probe)){
                String dest="baseline4".equals(probe)?"10.0.2.2":"192.0.2.1";
                udp4(dest,"WBD_B94_UID4".getBytes(java.nio.charset.StandardCharsets.US_ASCII),!"send4".equals(probe));
                result.putString("report","uid_probe_sent="+Process.myUid()+" socket=AF_INET probe="+probe);
                finish(Activity.RESULT_OK,result);return;
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
                result.putString("report","uid_probe_sent="+Process.myUid());
                finish(Activity.RESULT_OK,result);
                return;
            }
            if("system".equals(args.getString("dns_probe"))){
                android.net.Network network=android.net.Network.fromNetworkHandle(
                    Long.parseUnsignedLong(args.getString("network_handle")));
                String expected=args.getString("expected_ip");
                boolean found=false;
                for(java.net.InetAddress ip:network.getAllByName(args.getString("dns_name")))
                    if(expected.equals(ip.getHostAddress()))found=true;
                if(!found)throw new IllegalStateException("Android Resolver A answer mismatch");
                result.putString("report","dns_probe_uid="+Process.myUid()+" dns_answer="+expected);
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
            result.putString("error","uid="+Process.myUid()+" probe="+args.getString("uid_probe","")+" "+e);finish(Activity.RESULT_CANCELED,result);
        }
    }
}
