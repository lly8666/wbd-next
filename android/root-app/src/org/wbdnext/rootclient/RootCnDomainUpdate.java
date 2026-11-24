package org.wbdnext.rootclient;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.IDN;
import java.net.URL;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.TreeSet;

/** Cold official release extraction. Same DLC format/type mapping as main;
 * Go/Rust retain the only production domain matcher. No automatic download. */
final class RootCnDomainUpdate {
    private static final String LATEST="https://api.github.com/repos/v2fly/domain-list-community/releases/latest";
    private static final String BASE="https://github.com/v2fly/domain-list-community/releases/download/";
    private static final int MAX_DOWNLOAD=16<<20, MAX_RULES_BYTES=4<<20;
    private RootCnDomainUpdate(){}
    static final class Result {
        final String tag; final int count;
        Result(String t,int n){tag=t;count=n;}
    }
    private static byte[] get(String url,int max)throws Exception {
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();
        c.setConnectTimeout(15000);c.setReadTimeout(30000);
        c.setRequestProperty("User-Agent","WBD-CN-domain-update");
        try{
            if(c.getResponseCode()!=200)throw new java.io.IOException("HTTP "+c.getResponseCode());
            try(InputStream in=c.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
                byte[] block=new byte[8192];int n;
                while((n=in.read(block))!=-1){
                    if(out.size()+n>max)throw new java.io.IOException("下载过大");
                    out.write(block,0,n);
                }
                return out.toByteArray();
            }
        }finally{c.disconnect();}
    }
    private static String sha(byte[] b)throws Exception{
        StringBuilder s=new StringBuilder(64);
        for(byte v:MessageDigest.getInstance("SHA-256").digest(b))s.append(String.format(Locale.ROOT,"%02x",v&255));
        return s.toString();
    }
    // Minimal official GeoSite protobuf reader (varint / length-delimited),
    // no dependency or permanent runtime state. Slices share the raw asset.
    private static final class Cursor {
        final byte[] b; int pos; final int end;
        Cursor(byte[] b,int start,int end){this.b=b;this.pos=start;this.end=end;}
        boolean more(){return pos<end;}
        long varint()throws Exception{
            long n=0;
            for(int shift=0;shift<64&&pos<end;shift+=7){
                int v=b[pos++]&255;n|=(long)(v&127)<<shift;
                if((v&128)==0)return n;
            }
            throw new java.io.IOException("invalid GeoSite varint");
        }
        Field next()throws Exception{
            long tag=varint();int number=(int)(tag>>>3),kind=(int)(tag&7);
            if(number<=0)throw new java.io.IOException("invalid GeoSite field");
            if(kind==0)return new Field(number,varint(),null);
            if(kind!=2)throw new java.io.IOException("invalid GeoSite wire type");
            long len=varint();
            if(len<0||len>end-pos)throw new java.io.IOException("truncated GeoSite");
            Cursor slice=new Cursor(b,pos,pos+(int)len);pos+=(int)len;
            return new Field(number,0,slice);
        }
        String string()throws Exception{
            return StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(b,pos,end-pos)).toString();
        }
    }
    private static final class Field{
        final int number;final long value;final Cursor data;
        Field(int n,long v,Cursor d){number=n;value=v;data=d;}
    }
    static byte[] extract(byte[] raw)throws Exception{
        if(raw.length>MAX_DOWNLOAD)throw new java.io.IOException("DLC asset too large");
        Cursor root=new Cursor(raw,0,raw.length),selected=null;
        while(root.more()){
            Field f=root.next();if(f.number!=1||f.data==null)continue;
            Cursor site=f.data;Cursor scan=new Cursor(site.b,site.pos,site.end);
            String name="";
            while(scan.more()){
                Field v=scan.next();if(v.number==1&&v.data!=null)name=v.data.string();
            }
            if("geolocation-cn".equalsIgnoreCase(name)){
                if(selected!=null)throw new java.io.IOException("duplicate CN group");
                selected=site;
            }
        }
        if(selected==null)throw new java.io.IOException("missing CN group");
        TreeSet<String> rules=new TreeSet<>();
        while(selected.more()){
            Field f=selected.next();if(f.number!=2||f.data==null)continue;
            long type=0;String value="";
            while(f.data.more()){
                Field v=f.data.next();
                if(v.number==1&&v.data==null)type=v.value;
                if(v.number==2&&v.data!=null)value=v.data.string();
            }
            if(value.isEmpty()||value.indexOf('\n')>=0||value.indexOf('\r')>=0)
                throw new java.io.IOException("invalid CN rule");
            String rule;
            if(type==0)rule="keyword:"+value.toLowerCase(Locale.ROOT);
            else if(type==1)rule="regexp:"+value;
            else if(type==2||type==3){
                if(value.endsWith("."))value=value.substring(0,value.length()-1);
                value=IDN.toASCII(value,IDN.USE_STD3_ASCII_RULES).toLowerCase(Locale.ROOT);
                if(value.isEmpty()||value.length()>253)throw new java.io.IOException("invalid CN domain");
                rule=(type==3?"=":"")+value;
            }else throw new java.io.IOException("unknown CN rule type");
            rules.add(rule);
            if(rules.size()>100000)throw new java.io.IOException("too many CN rules");
        }
        if(rules.size()<1000)throw new java.io.IOException("CN group too small");
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        for(String rule:rules){
            byte[] bytes=(rule+"\n").getBytes(StandardCharsets.UTF_8);
            if(out.size()+bytes.length>MAX_RULES_BYTES)throw new java.io.IOException("CN rules too large");
            out.write(bytes);
        }
        return out.toByteArray();
    }
    static Result refresh(File target)throws Exception{
        // Android JSON parsing stays in the manual caller path. No Go runtime
        // process or external dependency is needed to fetch the official data.
        byte[] meta=get(LATEST,1<<20);
        String tag=new org.json.JSONObject(new String(meta,StandardCharsets.UTF_8)).getString("tag_name");
        if(!tag.matches("[0-9]{14}"))throw new java.io.IOException("invalid release tag");
        String prefix=BASE+tag+"/";
        byte[] dat=get(prefix+"dlc.dat",MAX_DOWNLOAD);
        String sum=new String(get(prefix+"dlc.dat.sha256sum",4096),StandardCharsets.US_ASCII).trim().split("\\s+")[0];
        if(!sha(dat).equalsIgnoreCase(sum))throw new java.io.IOException("官方文件校验值不一致");
        byte[] rules=extract(dat);
        File tmp=File.createTempFile("cn-update-",".txt",target.getParentFile());
        try{
            try(FileOutputStream out=new FileOutputStream(tmp)){out.write(rules);out.getFD().sync();}
            Files.move(tmp.toPath(),target.toPath(),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
        }finally{tmp.delete();}
        int count=0;for(byte b:rules)if(b=='\n')count++;
        return new Result(tag,count);
    }
}
