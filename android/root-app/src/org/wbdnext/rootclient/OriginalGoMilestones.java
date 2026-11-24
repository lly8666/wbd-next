package org.wbdnext.rootclient;

/**
 * Only original-Go markers at a line's beginning, optionally after
 * Go's exact default yyyy/mm/dd hh:mm:ss prefix. No substring matches
 * from an untrusted username, server hostname or native error message.
 * Cold-stage observation is not authenticated app-data evidence.
 */
final class OriginalGoMilestones {
    private OriginalGoMilestones() {}
    private static boolean goTimePrefix(String s) {
        if(s.length()<20 || s.charAt(19)!=' ')return false;
        for(int i=0;i<19;i++){
            char c=s.charAt(i);
            if(i==4||i==7){if(c!='/')return false;}
            else if(i==10){if(c!=' ')return false;}
            else if(i==13||i==16){if(c!=':')return false;}
            else if(c<'0'||c>'9')return false;
        }
        return true;
    }
    static boolean matches(String line,String marker) {
        if(line==null||marker==null||marker.length()==0||
           line.length()>4096||line.indexOf('\n')>=0||
           line.indexOf('\r')>=0)return false;
        String body=line.trim();
        if(goTimePrefix(body))body=body.substring(20);
        return body.equals(marker)||body.startsWith(marker+" ");
    }
}
