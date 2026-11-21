package org.wbdnext.rootclient;

// Pure cold input grammar. Never resolve on the Android UI or through
// netd's default resolver: only the root Go physical DNS bootstrap may do so.
final class ServerAddress {
    private ServerAddress(){}
    static boolean isIPv4Literal(String value){
        if(value==null)return false;
        String[] parts=value.split("\\.",-1);
        if(parts.length!=4)return false;
        for(String part:parts){
            if(part.isEmpty()||part.length()>3||
                (part.length()>1&&part.charAt(0)=='0'))return false;
            int num=0;
            for(int i=0;i<part.length();i++){
                char c=part.charAt(i);
                if(c<'0'||c>'9')return false;
                num=num*10+(c-'0');
            }
            if(num>255)return false;
        }
        return true;
    }
    static boolean isDnsName(String value){
        if(value==null||value.length()<3||value.length()>253)return false;
        String[] labels=value.split("\\.",-1);
        if(labels.length<2)return false;
        boolean letters=false;
        for(String label:labels){
            if(label.isEmpty()||label.length()>63||label.charAt(0)=='-'||
                label.charAt(label.length()-1)=='-')return false;
            for(int i=0;i<label.length();i++){
                char c=label.charAt(i);
                boolean alpha=(c>='a'&&c<='z')||(c>='A'&&c<='Z');
                boolean digit=c>='0'&&c<='9';
                if(!alpha&&!digit&&c!='-')return false;
                if(alpha)letters=true;
            }
        }
        return letters;
    }
    static boolean valid(String value){
        return isIPv4Literal(value)||isDnsName(value);
    }
}
