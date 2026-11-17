package org.wbdnext.rootclient;

// The Linux kernel routes by UID, NOT by Java package name.
// A selected package must be a real current-user installed app; shared
// UID packages may share the same route and are explicitly disclosed.
final class InstalledAppTarget {
    final String packageName;
    final String label;
    final int uid;

    InstalledAppTarget(String name,String label,int uid){
        if(!validPackage(name)||uid<10000||uid>1999999)
            throw new IllegalArgumentException("invalid installed app identity");
        this.packageName=name;
        this.label=label==null||label.trim().isEmpty()?name:label.trim();
        this.uid=uid;
    }

    static boolean validPackage(String name){
        if(name==null||name.length()<3||name.length()>255)return false;
        String[] parts=name.split("\\.",-1);
        if(parts.length<2)return false;
        for(String part:parts){
            if(part.isEmpty())return false;
            char first=part.charAt(0);
            if(!((first>='a'&&first<='z')||
                 (first>='A'&&first<='Z')||first=='_'))return false;
            for(int j=1;j<part.length();j++){
                char c=part.charAt(j);
                if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
                     (c>='0'&&c<='9')||c=='_'))return false;
            }
        }
        return true;
    }
    static boolean eligible(String name,int uid,int selfUid,String selfPackage){
        return validPackage(name)&&uid>=10000&&uid<=1999999&&
            uid!=selfUid&&!name.equals(selfPackage);
    }
    boolean matches(String actualPackage,int actualUid,int selfUid,String selfPackage){
        return packageName.equals(actualPackage)&&uid==actualUid&&
            eligible(actualPackage,actualUid,selfUid,selfPackage);
    }
    String title(){
        return label+"  ["+packageName+"]  UID "+uid;
    }
}
