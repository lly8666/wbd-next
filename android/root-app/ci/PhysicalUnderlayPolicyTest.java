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
        check(PhysicalUnderlayPolicy.useClat(false,true,96,"rmnet0","v4-rmnet0","192.0.0.4",32),
            "actual RFC7335 CLAT on IPv6-only selected Network");
        check(!PhysicalUnderlayPolicy.useClat(true,true,96,"rmnet0","v4-rmnet0","192.0.0.4",32),
            "native IPv4 preferred on dual stack");
        check(!PhysicalUnderlayPolicy.useClat(false,true,96,"rmnet0","v4-rmnet1","192.0.0.4",32),
            "different physical parent rejected");
        check(!PhysicalUnderlayPolicy.useClat(false,true,0,"rmnet0","v4-rmnet0","192.0.0.4",32),
            "no NAT64 prefix means no CLAT");
        check(!PhysicalUnderlayPolicy.useClat(false,true,96,"rmnet0","v4-rmnet0","10.0.0.1",32),
            "foreign virtual IPv4 rejected");
        check(!PhysicalUnderlayPolicy.useClat(false,true,96,"rmnet0","v4-rmnet0","192.0.0.4",24),
            "CLAT must be real kernel /32");
        check(!PhysicalUnderlayPolicy.useClat(false,false,96,"rmnet0","v4-rmnet0","192.0.0.4",32),
            "parent must own usable IPv6");
        System.out.println("ANDROID_B67_EXISTING_CLAT_464XLAT_UNDERLAY_HOST_PASS");
        System.out.println("ANDROID_B27_LOCAL_ONLY_PHYSICAL_WBD_UNDERLAY_HOST_PASS");
    }
}
