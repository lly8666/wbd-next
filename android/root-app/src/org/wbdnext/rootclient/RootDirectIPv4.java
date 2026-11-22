package org.wbdnext.rootclient;

import java.util.TreeSet;

/** Cold UI option only: up to four real IPv4 prefixes for Android's existing
 * uidrange private FIB throw routes. There is no Java packet forwarding. */
final class RootDirectIPv4 {
    static final int MAX_PREFIXES=4;
    private RootDirectIPv4(){}

    static String canonicalCSV(String raw){
        if(raw==null||raw.trim().isEmpty())return "";
        String[] tokens=raw.split(",",-1);
        if(tokens.length>MAX_PREFIXES)
            throw new IllegalArgumentException("最多4个IPv4直连网段");
        TreeSet<String> sorted=new TreeSet<>();
        for(String token:tokens){
            String route=token.trim();
            int slash=route.indexOf('/');
            if(slash<=0||slash!=route.lastIndexOf('/')||slash>=route.length()-1)
                throw new IllegalArgumentException("IPv4直连须填写 CIDR 如 192.168.1.0/24");
            int bits=parseDecimal(route.substring(slash+1),32);
            if(bits<1)throw new IllegalArgumentException("不允许0.0.0.0/0绕过全部隧道");
            String[] a=route.substring(0,slash).split("\\.",-1);
            if(a.length!=4)throw new IllegalArgumentException("必须是IPv4而非域名或IPv6");
            int[] octets=new int[4];
            long ip=0;
            for(int i=0;i<4;i++){
                octets[i]=parseDecimal(a[i],255);
                ip=(ip<<8)|octets[i];
            }
            if(octets[0]==0||octets[0]==127||octets[0]>=224)
                throw new IllegalArgumentException("直连前缀必须是普通IPv4单播");
            long mask=(0xffffffffL << (32-bits))&0xffffffffL;
            if((ip&mask)!=ip)
                throw new IllegalArgumentException("直连CIDR必须写网段地址，而不是某台主机/掩码");
            String cidr=octets[0]+"."+octets[1]+"."+octets[2]+"."+octets[3]+"/"+bits;
            if(!sorted.add(cidr))throw new IllegalArgumentException("重复的IPv4直连网段");
        }
        return String.join(",",sorted);
    }
    private static int parseDecimal(String raw,int max){
        if(raw.isEmpty()||raw.length()>3||(raw.length()>1&&raw.charAt(0)=='0'))
            throw new IllegalArgumentException("IPv4数字格式错误");
        int x=0;
        for(int i=0;i<raw.length();i++){
            char c=raw.charAt(i);
            if(c<'0'||c>'9')throw new IllegalArgumentException("非十进制IPv4数字");
            x=x*10+c-'0';
            if(x>max)throw new IllegalArgumentException("IPv4数字超出范围");
        }
        return x;
    }
}
