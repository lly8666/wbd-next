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
    final boolean hasInternetCapability;
    private PhysicalNetwork(long handle,String name,int index,int mtu,String addr,
                            boolean internetCapability){
        this.handle=handle;this.interfaceName=name;
        this.ifindex=index;this.mtu=mtu;this.address=addr;
        this.hasInternetCapability=internetCapability;
    }
    String title(){
        return interfaceName+"  "+address+"  MTU "+mtu+
            "  Network "+Long.toUnsignedString(handle)+
            (hasInternetCapability?"":"  [仅本地链路：Android未声明Internet]");
    }
    boolean same(PhysicalNetwork other){
        return other!=null&&handle==other.handle&&
            interfaceName.equals(other.interfaceName)&&
            ifindex==other.ifindex&&mtu==other.mtu&&
            address.equals(other.address);
    }
    // B27: no INTERNET requirement. Many user-controlled WiFi/Ethernet
    // LAN links reach a nearby WBD server without Internet validation.
    // The SAME cold selection and Service callback policy is used; the
    // original kernel IPv4/interface/MTU check is still mandatory.
    static boolean physicalUnderlay(NetworkCapabilities caps){
        return caps!=null&&PhysicalUnderlayPolicy.accepts(
            caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI),
            caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR),
            caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET),
            caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN));
    }
    static List<PhysicalNetwork> available(Context context){
        ConnectivityManager cm=(ConnectivityManager)context.getSystemService(
            Context.CONNECTIVITY_SERVICE);
        if(cm==null)return Collections.emptyList();
        ArrayList<PhysicalNetwork> out=new ArrayList<>();
        for(Network network:cm.getAllNetworks()){
            try{
                NetworkCapabilities caps=cm.getNetworkCapabilities(network);
                if(!physicalUnderlay(caps)){
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
                out.add(new PhysicalNetwork(handle,name,iface.getIndex(),mtu,addr,
                    caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)));
            }catch(Exception ignored){
                // A disappearing Network is never a candidate.
            }
        }
        return out;
    }
    // Consume the callback's own LinkProperties, never synchronously
    // requery ConnectivityManager inside its asynchronous callback.
    boolean matchesLinkProperties(LinkProperties link){
        if(link==null||!interfaceName.equals(link.getInterfaceName()))return false;
        try{
            NetworkInterface iface=NetworkInterface.getByName(interfaceName);
            if(iface==null||!iface.isUp()||iface.getIndex()!=ifindex||
                iface.getMTU()!=mtu)return false;
            boolean linkAddress=false,kernelAddress=false;
            for(LinkAddress a:link.getLinkAddresses()){
                if(a.getAddress() instanceof Inet4Address &&
                    address.equals(a.getAddress().getHostAddress())){
                    linkAddress=true;break;
                }
            }
            java.util.Enumeration<java.net.InetAddress> addrs=iface.getInetAddresses();
            while(addrs.hasMoreElements()){
                if(address.equals(addrs.nextElement().getHostAddress())){
                    kernelAddress=true;break;
                }
            }
            return linkAddress&&kernelAddress;
        }catch(Exception ignored){return false;}
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
