package org.wbdnext.rootclient;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import java.net.Inet4Address;
import java.net.NetworkInterface;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

// Only real ConnectivityManager Network instances: NEVER infer a netId
// from an interface name, use VpnService, or select the default after loss.
// Stateless and cold-only; native Bionic independently binds its RAW FD.
final class PhysicalNetwork {
    final long handle;
    final String interfaceName;
    final int ifindex;
    final int mtu;
    final String address;
    private PhysicalNetwork(long handle,String name,int index,int mtu,String addr){
        this.handle=handle;this.interfaceName=name;
        this.ifindex=index;this.mtu=mtu;this.address=addr;
    }
    String title(){
        return interfaceName+"  "+address+"  MTU "+mtu+
            "  Network "+Long.toUnsignedString(handle);
    }
    boolean same(PhysicalNetwork other){
        return other!=null&&handle==other.handle&&
            interfaceName.equals(other.interfaceName)&&
            ifindex==other.ifindex&&mtu==other.mtu&&
            address.equals(other.address);
    }
    static List<PhysicalNetwork> available(Context context){
        ConnectivityManager cm=(ConnectivityManager)context.getSystemService(
            Context.CONNECTIVITY_SERVICE);
        if(cm==null)return Collections.emptyList();
        ArrayList<PhysicalNetwork> out=new ArrayList<>();
        for(Network network:cm.getAllNetworks()){
            try{
                NetworkCapabilities caps=cm.getNetworkCapabilities(network);
                if(caps==null||!caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)||
                    caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)||
                    !(caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)||
                      caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR))){
                    continue;
                }
                LinkProperties link=cm.getLinkProperties(network);
                if(link==null||link.getInterfaceName()==null)continue;
                String name=link.getInterfaceName();
                NetworkInterface iface=NetworkInterface.getByName(name);
                if(iface==null||iface.getIndex()<=0||!iface.isUp())continue;
                int mtu=iface.getMTU();
                if(mtu<576||mtu>65535)continue;
                String addr=null;
                for(LinkAddress a:link.getLinkAddresses()){
                    if(a.getAddress() instanceof Inet4Address){
                        String ip=a.getAddress().getHostAddress();
                        if(!a.getAddress().isAnyLocalAddress()&&
                           !a.getAddress().isLoopbackAddress()&&
                           !a.getAddress().isLinkLocalAddress()){
                            // The Network handle and actual kernel interface
                            // MUST agree on this source IP before FakeTCP SYN.
                            java.util.Enumeration<java.net.InetAddress> owned=
                                iface.getInetAddresses();
                            while(owned.hasMoreElements()){
                                if(ip.equals(owned.nextElement().getHostAddress())){
                                    addr=ip;break;
                                }
                            }
                            if(addr!=null)break;
                        }
                    }
                }
                if(addr==null)continue;
                long handle=network.getNetworkHandle();
                if(handle==0)continue;
                out.add(new PhysicalNetwork(handle,name,iface.getIndex(),mtu,addr));
            }catch(Exception ignored){
                // A disappearing Network is never a candidate.
            }
        }
        return out;
    }
    static PhysicalNetwork exact(Context ctx,long handle,String iface,
                                 int ifindex,int mtu,String address){
        for(PhysicalNetwork n:available(ctx)){
            if(n.handle==handle&&n.interfaceName.equals(iface)&&
               n.ifindex==ifindex&&n.mtu==mtu&&n.address.equals(address)){
                return n;
            }
        }
        return null;
    }
}
