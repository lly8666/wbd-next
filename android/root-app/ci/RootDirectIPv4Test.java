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
  ok("192.168.1.0/24".equals(RootDirectIPv4.connectedSubnet("192.168.1.95",24)));
  ok("10.4.0.0/16".equals(RootDirectIPv4.connectedSubnet("10.4.9.2",16)));
  ok("100.64.13.6/32".equals(RootDirectIPv4.connectedSubnet("100.64.13.6",32)));
  ok("10.4.0.0/16,192.168.1.0/24".equals(
     RootDirectIPv4.withConnectedSubnet("10.4.0.0/16","192.168.1.0/24")));
  ok("10.4.0.0/16".equals(
     RootDirectIPv4.withConnectedSubnet("10.4.0.0/16","10.4.0.0/16")));
  ok(RootDirectIPv4.includes("10.4.0.0/16,192.168.1.0/24","192.168.1.0/24"));
  boolean bad=false;
  try{RootDirectIPv4.connectedSubnet("192.168.1.95",0);}
  catch(IllegalArgumentException expected){bad=true;}ok(bad);
  bad=false;
  try{RootDirectIPv4.withConnectedSubnet(
      "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10",
      "198.51.100.0/24");}
  catch(IllegalArgumentException expected){bad=true;}ok(bad);
  System.out.println("ANDROID_B38_SELECTED_LAN_AUTO_CIDR_ORIGINAL_FIB_HOST_PASS checks="+checks);
 }
}
