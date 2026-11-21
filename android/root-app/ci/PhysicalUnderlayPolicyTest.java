package org.wbdnext.rootclient;

/** Same production policy used by both selection and owner callbacks. */
public final class PhysicalUnderlayPolicyTest {
    private static void check(boolean condition,String why){
        if(!condition)throw new AssertionError(why);
    }
    public static void main(String[] args){
        check(PhysicalUnderlayPolicy.accepts(true,false,false,false),
            "WiFi link with NO INTERNET capability still usable as underlay");
        check(PhysicalUnderlayPolicy.accepts(false,true,false,false),
            "mobile data supported");
        check(PhysicalUnderlayPolicy.accepts(false,false,true,false),
            "Ethernet LAN-only supported");
        check(!PhysicalUnderlayPolicy.accepts(false,false,true,true),
            "VPN underlay must not be confused with physical Ethernet");
        check(!PhysicalUnderlayPolicy.accepts(false,false,false,false),
            "unclassified Network is not an underlay");
        check(!PhysicalUnderlayPolicy.accepts(true,true,true,true),
            "VPN excluded even with physical transport claims");
        System.out.println("ANDROID_B27_LOCAL_ONLY_PHYSICAL_WBD_UNDERLAY_HOST_PASS");
    }
}
