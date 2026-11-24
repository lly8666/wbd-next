package org.wbdnext.testtraffic;

import java.io.DataInputStream;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.util.Arrays;
import java.util.Locale;
import java.util.Random;
import java.util.concurrent.FutureTask;

/** Ordinary Java sockets under the test APK UID. No Root, VPN or WBD engine. */
public final class TrafficProbe {
    private TrafficProbe() {}
    private static double ms(long ns) { return ns / 1_000_000.0; }
    private static double percentile(long[] a, int n, double p) {
        if(n==0)return -1;
        Arrays.sort(a,0,n);
        return ms(a[Math.max(0,(int)Math.ceil(p*n)-1)]);
    }
    public static String run(String host,int port,int samples,int mib) throws Exception {
        if(samples<1||samples>1000||mib<1||mib>256||port<1||port>65535)
            throw new IllegalArgumentException("invalid test arguments");
        InetAddress addr=InetAddress.getByName(host);
        InetSocketAddress peer=new InetSocketAddress(addr,port);
        Random random=new Random(20261124L);
        byte[] tx=new byte[64],rx=new byte[64];
        long[] tcp=new long[samples],udp=new long[samples];
        long connect,first,bulkNs;
        int udpOk=0;
        long bulkBytes=(long)mib*1024*1024;
        try(Socket s=new Socket()){
            s.setTcpNoDelay(true);s.setSoTimeout(5000);
            long start=System.nanoTime();
            s.connect(peer,5000);
            connect=System.nanoTime()-start;
            DataInputStream in=new DataInputStream(s.getInputStream());
            OutputStream out=s.getOutputStream();
            for(int i=0;i<samples;i++){
                random.nextBytes(tx);start=System.nanoTime();
                out.write(tx);in.readFully(rx);
                tcp[i]=System.nanoTime()-start;
                if(!Arrays.equals(tx,rx))throw new IllegalStateException("TCP echo mismatch");
            }
            first=tcp[0];
            // Stream both directions concurrently. Do not impose an
            // artificial 64KiB-per-RTT application stop-and-wait ceiling.
            byte[] block=new byte[65536],echo=new byte[65536];
            Random expected=new Random(123456L);
            FutureTask<Void> send=new FutureTask<>(()->{
                Random source=new Random(123456L);
                byte[] buffer=new byte[65536];
                try{
                    for(long sent=0;sent<bulkBytes;sent+=buffer.length){
                        source.nextBytes(buffer);out.write(buffer);
                    }
                    return null;
                }catch(Exception failure){s.close();throw failure;}
            });
            Thread writer=new Thread(send,"traffic-fixture-writer");
            start=System.nanoTime();writer.start();
            try{
                for(long received=0;received<bulkBytes;received+=block.length){
                    expected.nextBytes(block);in.readFully(echo);
                    if(!Arrays.equals(block,echo))throw new IllegalStateException("TCP bulk echo mismatch");
                }
                send.get();
            }finally{
                if(!send.isDone())s.close();
                writer.join();
            }
            bulkNs=System.nanoTime()-start;
        }
        try(DatagramSocket s=new DatagramSocket()){
            s.connect(peer);s.setSoTimeout(1500);
            DatagramPacket request=new DatagramPacket(tx,tx.length);
            DatagramPacket answer=new DatagramPacket(rx,rx.length);
            for(int i=0;i<samples;i++){
                random.nextBytes(tx);long start=System.nanoTime();
                s.send(request);answer.setLength(rx.length);
                try{s.receive(answer);}
                catch(SocketTimeoutException timeout){continue;}
                if(answer.getLength()!=tx.length||!Arrays.equals(tx,rx))continue;
                udp[udpOk++]=System.nanoTime()-start;
            }
        }
        // Concurrent byte-verified duplex echo rate, not line capacity or
        // a causal CPU measurement of the product itself.
        double echoMbps=bulkBytes*2*8/(bulkNs/1e9)/1e6;
        return String.format(Locale.ROOT,
          "tcp_ok=%d udp_ok=%d samples=%d connect_ms=%.3f first_echo_ms=%.3f tcp_p50_ms=%.3f tcp_p95_ms=%.3f tcp_p99_ms=%.3f udp_p50_ms=%.3f udp_p95_ms=%.3f udp_p99_ms=%.3f echo_bytes_each_direction=%d echo_mbps_both_directions=%.3f",
          samples,udpOk,samples,ms(connect),ms(first),
          percentile(tcp,samples,.50),percentile(tcp,samples,.95),percentile(tcp,samples,.99),
          percentile(udp,udpOk,.50),percentile(udp,udpOk,.95),percentile(udp,udpOk,.99),
          bulkBytes,echoMbps);
    }
    public static String resolve(String names) {
        if(names==null||names.isEmpty())return "";
        int total=0,ok=0;long start=System.nanoTime();
        for(String name:names.split(",")){
            if(name.isEmpty())continue;
            total++;
            try{if(InetAddress.getAllByName(name).length>0)ok++;}
            catch(Exception unresolved){/* count the ordinary resolver result */}
        }
        return String.format(Locale.ROOT," dns_ok=%d dns_count=%d dns_ms=%.3f",
            ok,total,ms(System.nanoTime()-start));
    }
    public static void main(String[] args)throws Exception{
        System.out.println(run(args[0],Integer.parseInt(args[1]),Integer.parseInt(args[2]),Integer.parseInt(args[3])));
    }
}
