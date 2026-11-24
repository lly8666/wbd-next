package org.wbdnext.rootclient;

/** UI-only projection of the actual existing cold routing fields. */
final class RootUiRouting {
    private RootUiRouting(){}
    static boolean isSplit(boolean cnIp,boolean cnDns,boolean physicalDns,boolean lan,String v4,String v6){
        return cnIp||cnDns||physicalDns||lan||!v4.trim().isEmpty()||!v6.trim().isEmpty();
    }
}
