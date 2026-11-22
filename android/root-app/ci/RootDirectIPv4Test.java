package org.wbdnext.rootclient;
public final class RootDirectIPv4Test {
 private static int checks;
 private static void ok(boolean b){checks++;if(!b)throw new AssertionError("bad direct CIDR contract "+checks);}
 private static void rejects(String s){
  boolean bad=false;
  try{RootDirectIPv4.canonicalCSV(s);}catch(IllegalArgumentException expected){bad=true;}
  ok(bad);
 }
 public static void main(String[] ignored){
  ok("".equals(RootDirectIPv4.canonicalCSV("")));
  ok("10.9.0.0/16,192.168.7.0/24".equals(
   RootDirectIPv4.canonicalCSV("192.168.7.0/24, 10.9.0.0/16")));
  ok("198.51.100.9/32".equals(RootDirectIPv4.canonicalCSV("198.51.100.9/32")));
  rejects("0.0.0.0/0");rejects("10.3.0.4/16");rejects("192.168.0.0/16,192.168.0.0/16");
  rejects("fe80::/64");rejects("192.168.0.0/16,");rejects("192.168.01.0/24");
  rejects("10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,198.51.100.0/24,203.0.113.0/24");
  System.out.println("ANDROID_B33_DIRECT_IPV4_CIDR_COLD_HOST_PASS checks="+checks);
 }
}
