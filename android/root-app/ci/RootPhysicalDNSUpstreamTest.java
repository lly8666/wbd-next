package org.wbdnext.rootclient;
public final class RootPhysicalDNSUpstreamTest {
 private static int checks;
 private static void yes(boolean v){checks++;if(!v)throw new AssertionError("DNS upstream "+checks);}
 private static void rejects(String s){
  boolean rejected=false;
  try{RootPhysicalDNSUpstream.canonical(s);}catch(IllegalArgumentException expected){rejected=true;}
  yes(rejected);
 }
 public static void main(String[] a){
  yes("223.5.5.5".equals(RootPhysicalDNSUpstream.canonical("")));
  yes("192.168.1.1".equals(RootPhysicalDNSUpstream.canonical(" 192.168.1.1 ")));
  yes("1.1.1.1".equals(RootPhysicalDNSUpstream.canonical("1.1.1.1")));
  rejects("127.0.0.1");rejects("0.0.0.0");rejects("255.255.255.255");
  rejects("169.254.2.1");rejects("192.168.001.1");rejects("fe80::1");
  rejects("dns.example.net");rejects("1.1.1.256");
  System.out.println("ANDROID_B34_REAL_PHYSICAL_DNS_UPSTREAM_IPV4_HOST_PASS checks="+checks);
 }
}
