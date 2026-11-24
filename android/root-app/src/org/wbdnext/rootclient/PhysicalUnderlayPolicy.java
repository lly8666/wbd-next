package org.wbdnext.rootclient;

/**
 * B27: a real selected Android link can reach a nearby WBD server
 * without NET_CAPABILITY_INTERNET or VALIDATED. INTERNET is not a
 * property of the kernel interface and must not revoke its owner.
 * Network handle, IPv4, ifindex and MTU are checked by PhysicalNetwork.
 */
final class PhysicalUnderlayPolicy {
    private PhysicalUnderlayPolicy(){}
    static boolean accepts(boolean wifi,boolean cellular,boolean ethernet,
                           boolean vpn){
        return !vpn&&(wifi||cellular||ethernet);
    }
    // Android's RFC7335 CLAT /32 is not an ordinary directly connected LAN.
    static String clatInterface(String parent){
        if(parent==null||!parent.matches("[A-Za-z0-9_.-]{1,12}")||parent.startsWith("v4-"))return null;
        return "v4-"+parent;
    }
    static boolean clatAddress(String addr,int bits){
        return bits==32&&addr!=null&&addr.matches("192\\.0\\.0\\.[1-7]");
    }
    static boolean useClat(boolean nativeIPv4,boolean globalIPv6,int nat64Bits,
                           String parent,String stacked,String addr,int addrBits){
        String expected=clatInterface(parent);
        return !nativeIPv4&&globalIPv6&&nat64Bits==96&&expected!=null&&
            expected.equals(stacked)&&clatAddress(addr,addrBits);
    }
}
