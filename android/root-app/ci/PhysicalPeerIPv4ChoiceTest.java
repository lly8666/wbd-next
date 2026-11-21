package org.wbdnext.rootclient;

import java.net.InetAddress;

public final class PhysicalPeerIPv4ChoiceTest {
    private static void ok(boolean v,String msg){if(!v)throw new AssertionError(msg);}
    public static void main(String[] args)throws Exception{
        InetAddress v6=InetAddress.getByAddress(new byte[16]);
        InetAddress localhost=InetAddress.getByAddress(new byte[]{127,0,0,1});
        InetAddress lan=InetAddress.getByAddress(new byte[]{(byte)192,(byte)168,25,4});
        InetAddress publicIp=InetAddress.getByAddress(new byte[]{(byte)203,0,113,9});
        ok("192.168.25.4".equals(PhysicalPeerIPv4Choice.select(
            new InetAddress[]{v6,localhost,lan,publicIp})),"first selected usable LAN IPv4");
        ok("203.0.113.9".equals(PhysicalPeerIPv4Choice.select(
            new InetAddress[]{v6,publicIp})),"IPv4 after AAAA");
        ok(PhysicalPeerIPv4Choice.select(new InetAddress[]{v6,localhost})==null,
            "no valid IPv4 must not silently use IPv6/loopback");
        ok(PhysicalPeerIPv4Choice.select(null)==null,"missing answer");
        System.out.println("ANDROID_B28_SELECTED_NETWORK_LAN_HOSTNAME_IPV4_HOST_PASS");
    }
}
