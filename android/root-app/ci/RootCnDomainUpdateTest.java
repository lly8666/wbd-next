package org.wbdnext.rootclient;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.charset.StandardCharsets;
import java.util.TreeSet;

/** Compare actual upstream binary with main's signed typed text; no network. */
public final class RootCnDomainUpdateTest{
    public static void main(String[] args)throws Exception{
        byte[] raw=Files.readAllBytes(Paths.get(args[0]));
        String extracted=new String(RootCnDomainUpdate.extract(raw),StandardCharsets.UTF_8);
        TreeSet<String> expected=new TreeSet<>();
        for(String row:Files.readAllLines(Paths.get(args[1]),StandardCharsets.UTF_8)){
            if(row.startsWith("domain:"))row=row.substring(7);
            else if(row.startsWith("full:"))row="="+row.substring(5);
            if(!row.isEmpty())expected.add(row);
        }
        TreeSet<String> actual=new TreeSet<>();
        for(String row:extracted.split("\n"))if(!row.isEmpty())actual.add(row);
        if(actual.size()<1000||!actual.equals(expected))
            throw new AssertionError("Android manual release extraction differs: "+actual.size()+" vs "+expected.size());
        System.out.println("ANDROID_CN_MANUAL_UPDATE_OFFICIAL_GROUP_PASS rules="+actual.size());
    }
}
