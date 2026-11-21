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
}
