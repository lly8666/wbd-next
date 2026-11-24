package org.wbdnext.rootclient;

import java.net.Inet4Address;
import java.net.InetAddress;

/** B28: select a usable literal IPv4 from the selected Android Network's
 * cold hostname answers; never open an original WBD data-plane socket. */
final class PhysicalPeerIPv4Choice {
    private PhysicalPeerIPv4Choice(){}
    static String select(InetAddress[] answers){
        if(answers==null)return null;
        for(InetAddress a:answers){
            if(a instanceof Inet4Address&&!a.isAnyLocalAddress()&&
               !a.isLoopbackAddress()){
                return a.getHostAddress();
            }
        }
        return null;
    }
}
