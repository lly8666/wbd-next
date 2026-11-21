package org.wbdnext.rootclient;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

// The REAL production RootService delegates original Go CLI argv assembly
// here. Pure Java by design: Actions can test this exact path without AVD,
// fake networks, Root grants or replacing original Go/Rust/TLS.
final class OriginalGoCommandArgs {
    private OriginalGoCommandArgs(){}

    static String shellQuote(String s){
        if(s==null)throw new IllegalArgumentException("null original Go CLI token");
        // POSIX single-quote escape; no untrusted parameter expands in su -c.
        return "'"+s.replace("'","'\\''")+"'";
    }

    private static void pair(List<String> out,String flag,String value){
        out.add(flag);
        out.add(value);
    }
    private static void absolute(String path){
        if(path==null||!path.startsWith("/")||path.length()>4096||
           path.indexOf('\n')>=0||path.indexOf('\r')>=0)
            throw new IllegalArgumentException("original Go private file path invalid");
    }
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile){
        return build(iface,handle,localIPv4,peer,peerPort,localPort,
            sni,user,passwordFile,routeKeyFile,installationFile,cnFile,
            targetUids,allApps,excludedAppIDs,tlsCaFile,false);
    }
    // Default matches main: the flag only opts into strict verification.
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile,boolean verifyTLS){
        return build(iface,handle,localIPv4,peer,peerPort,localPort,
            sni,user,passwordFile,routeKeyFile,installationFile,cnFile,
            targetUids,allApps,excludedAppIDs,tlsCaFile,verifyTLS,true);
    }
    // Explicit tunnel UDP DNS toggle: old Android app callers default ON;
    // disabling it leaves the exact legacy Normal/off TUN DATA behavior.
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile,boolean verifyTLS,boolean tunnelDNS){
        return build(iface,handle,localIPv4,peer,peerPort,localPort,
            sni,user,passwordFile,routeKeyFile,installationFile,cnFile,
            targetUids,allApps,excludedAppIDs,tlsCaFile,verifyTLS,tunnelDNS,false);
    }
    // Only explicit physical-DNS opt-in changes the original tunnel default.
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile,boolean verifyTLS,boolean tunnelDNS,
                              boolean physicalDNS){
        return build(iface,handle,localIPv4,peer,peerPort,localPort,
            sni,user,passwordFile,routeKeyFile,installationFile,cnFile,
            targetUids,allApps,excludedAppIDs,tlsCaFile,verifyTLS,tunnelDNS,physicalDNS,false);
    }
    // B5 full CN8503 QNAME split is explicit; legacy overloads unchanged.
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile,boolean verifyTLS,boolean tunnelDNS,
                              boolean physicalDNS,boolean cnSplitDNS){
        return build(iface,handle,localIPv4,peer,peerPort,localPort,
            sni,user,passwordFile,routeKeyFile,installationFile,cnFile,
            targetUids,allApps,excludedAppIDs,tlsCaFile,verifyTLS,
            tunnelDNS,physicalDNS,cnSplitDNS,1460);
    }
    // Original Go MTU budget; no Java packet processing.
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile,boolean verifyTLS,boolean tunnelDNS,
                              boolean physicalDNS,boolean cnSplitDNS,int requestedOuterMTU){
        return build(iface,handle,localIPv4,peer,peerPort,localPort,
            sni,user,passwordFile,routeKeyFile,installationFile,cnFile,
            targetUids,allApps,excludedAppIDs,tlsCaFile,verifyTLS,
            tunnelDNS,physicalDNS,cnSplitDNS,requestedOuterMTU,"chacha20-poly1305");
    }
    // B9 original Go authenticates this choice in the V4 cold snapshot;
    // Rust's existing RecordSuite handles all three, no separate Android AEAD.
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile,boolean verifyTLS,boolean tunnelDNS,
                              boolean physicalDNS,boolean cnSplitDNS,int requestedOuterMTU,
                              String recordCipher){
        return build(iface,handle,localIPv4,peer,peerPort,localPort,
            sni,user,passwordFile,routeKeyFile,installationFile,cnFile,
            targetUids,allApps,excludedAppIDs,tlsCaFile,verifyTLS,
            tunnelDNS,physicalDNS,cnSplitDNS,requestedOuterMTU,recordCipher,500);
    }
    // B10: Original-Go kernel TUN queue cold knob only; old overloads default 500.
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile,boolean verifyTLS,boolean tunnelDNS,
                              boolean physicalDNS,boolean cnSplitDNS,int requestedOuterMTU,
                              String recordCipher,int requestedTunQueue){
        return build(iface,handle,localIPv4,peer,peerPort,localPort,
            sni,user,passwordFile,routeKeyFile,installationFile,cnFile,
            targetUids,allApps,excludedAppIDs,tlsCaFile,verifyTLS,
            tunnelDNS,physicalDNS,cnSplitDNS,requestedOuterMTU,recordCipher,
            requestedTunQueue,"off");
    }
    // B11b original-Go authenticated cold selection; legacy callers stay off.
    static List<String> build(String iface,long handle,String localIPv4,
                              String peer,int peerPort,int localPort,
                              String sni,String user,String passwordFile,
                              String routeKeyFile,String installationFile,
                              String cnFile,int[] targetUids,
                              boolean allApps,int[] excludedAppIDs,
                              String tlsCaFile,boolean verifyTLS,boolean tunnelDNS,
                              boolean physicalDNS,boolean cnSplitDNS,int requestedOuterMTU,
                              String recordCipher,int requestedTunQueue,String paddingMode){
        if(!"off".equals(paddingMode)&&!"tls".equals(paddingMode)&&
           !"flows".equals(paddingMode))
            throw new IllegalArgumentException("unsupported original startup padding");
        if(requestedTunQueue!=500&&requestedTunQueue!=2048)
            throw new IllegalArgumentException("TUN txqlen must be 500 or 2048");
        if(!"chacha20-poly1305".equals(recordCipher)&&
           !"aes-128-gcm".equals(recordCipher)&&
           !"aes-256-gcm".equals(recordCipher))
            throw new IllegalArgumentException("unsupported original V4 record cipher");
        if(requestedOuterMTU<576||requestedOuterMTU>1500)
            throw new IllegalArgumentException("outer IPv4 IP MTU must be 576..1500");
        if(iface==null||!iface.matches("[A-Za-z0-9_.-]{1,32}")||
           handle==0||!ServerAddress.isIPv4Literal(localIPv4)||
           !ServerAddress.valid(peer)||peerPort<1||peerPort>65535||
           localPort<1||localPort>65535||
           sni==null||sni.isEmpty()||sni.length()>253||
           user==null||user.isEmpty()||user.length()>128)
            throw new IllegalArgumentException("invalid original Go cold connection scope");
        absolute(passwordFile);
        absolute(routeKeyFile);
        absolute(installationFile);
        absolute(cnFile);
        if(tlsCaFile!=null)absolute(tlsCaFile);
        final ArrayList<String> args=new ArrayList<>();
        pair(args,"--mode","normal");
        args.add("--auto-ip");
        pair(args,"--raw-interface",iface);
        pair(args,"--android-network-handle",Long.toUnsignedString(handle));
        pair(args,"--local-ip",localIPv4);
        pair(args,ServerAddress.isIPv4Literal(peer)?"--peer-ip":"--peer-host",peer);
        pair(args,"--peer-port",Integer.toString(peerPort));
        pair(args,"--local-port",Integer.toString(localPort));
        pair(args,"--tun-name","wbdv40");
        pair(args,"--server-name",sni);
        pair(args,"--username",user);
        pair(args,"--password-file",passwordFile);
        pair(args,"--route-key-hex-file",routeKeyFile);
        pair(args,"--installation-id-file",installationFile);
        pair(args,"--outer-mtu",Integer.toString(requestedOuterMTU));
        pair(args,"--record-cipher",recordCipher);
        pair(args,"--startup-padding",paddingMode);
        pair(args,"--tun-fq-maxrate-mbps","0");
        pair(args,"--tun-txqlen-packets",Integer.toString(requestedTunQueue));
        pair(args,"--outer-repair","off");
        pair(args,"--android-cn-geosite-file",cnFile);
        if(cnSplitDNS)args.add("--android-cn-dns-split");
        else if(physicalDNS)args.add("--android-physical-dns");
        else if(tunnelDNS)args.add("--android-tunnel-dns");
        if(allApps){
            if(targetUids!=null)
                throw new IllegalArgumentException("all-app cannot also target selected UIDs");
            args.add("--android-route-all-apps");
            pair(args,"--android-route-exclude-appids",AllAppUIDPolicy.csv(excludedAppIDs));
        }else{
            if(excludedAppIDs!=null||targetUids==null||targetUids.length==0||
               targetUids.length>8)
                throw new IllegalArgumentException("exact selected UIDs required");
            Set<Integer> seen=new HashSet<>();
            for(int uid:targetUids){
                AllAppUIDPolicy.appId(uid);
                if(!seen.add(uid))
                    throw new IllegalArgumentException("duplicate selected UID");
            }
            if(targetUids.length==1){
                pair(args,"--android-route-uid",Integer.toString(targetUids[0]));
            }else{
                StringBuilder group=new StringBuilder();
                for(int uid:targetUids){
                    if(group.length()>0)group.append(',');
                    group.append(uid);
                }
                pair(args,"--android-route-uids",group.toString());
            }
        }
        if(verifyTLS){
            args.add("--tls-verify-server");
            if(tlsCaFile!=null)pair(args,"--tls-ca-pem",tlsCaFile);
        }
        return Collections.unmodifiableList(args);
    }
}
